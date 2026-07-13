import streamlit as st
import csv
import os
import math
import pandas as pd
import io

# Set page config
st.set_page_config(
    page_title="트럭 배차 시뮬레이터 (Truck Dispatch Simulator)",
    page_icon="🚛",
    layout="wide"
)

# Helper function to clean numeric values
def clean_num(val):
    if not val:
        return 0.0
    val_clean = "".join(c for c in str(val) if c.isdigit() or c == '.' or c == '-')
    if not val_clean:
        return 0.0
    try:
        return float(val_clean)
    except ValueError:
        return 0.0

# Helper function to extract truck number
def extract_truck_number(name):
    # Extract numeric part from truck name, e.g. '2.5톤 카고' -> '2.5', '5톤  카고' -> '5'
    num_str = "".join(c for c in name if c.isdigit() or c == '.')
    if not num_str:
        return name
    num_str = num_str.strip('.')
    if not num_str:
        return name
    try:
        val = float(num_str)
        return int(val) if val.is_integer() else val
    except ValueError:
        return name

# Load truck database
@st.cache_data
def load_truck_database():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    truck_size_path = os.path.join(BASE_DIR, "truck size.csv")
    if not os.path.exists(truck_size_path):
        st.error(f"차량 규격 데이터베이스 파일이 존재하지 않습니다: {truck_size_path}")
        return []
        
    trucks = []
    with open(truck_size_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    header_idx = -1
    for idx, r in enumerate(rows):
        row_stripped = [cell.strip() for cell in r]
        if '명칭' in row_stripped:
            header_idx = idx
            break
            
    if header_idx == -1:
        header_idx = 1
        
    header = rows[header_idx]
    header_stripped = [cell.strip() for cell in header]
    
    try:
        name_idx = header_stripped.index('명칭')
        width_idx = header_stripped.index('가로(넓이)')
        length_idx = header_stripped.index('세로(길이)')
        limit_weight_idx = header_stripped.index('적재중량')
        safe_weight_idx = header_stripped.index('적정 적재\n중량')
    except ValueError:
        name_idx = 0
        width_idx = 1
        length_idx = 2
        limit_weight_idx = 4
        safe_weight_idx = 5
        
    for i in range(header_idx + 1, len(rows)):
        row = rows[i]
        if not row or len(row) <= max(name_idx, width_idx, length_idx, limit_weight_idx, safe_weight_idx):
            continue
        name = row[name_idx].strip()
        if not name:
            continue
            
        width = clean_num(row[width_idx])
        length = clean_num(row[length_idx])
        limit_weight = clean_num(row[limit_weight_idx])
        
        safe_weight_val = row[safe_weight_idx] if safe_weight_idx < len(row) else ''
        if not safe_weight_val and safe_weight_idx + 1 < len(row):
            safe_weight_val = row[safe_weight_idx + 1]
        safe_weight = clean_num(safe_weight_val)
        
        if safe_weight == 0.0:
            safe_weight = limit_weight
            
        trucks.append({
            'name': name,
            'width': width,
            'length': length,
            'limit_weight': limit_weight,
            'safe_weight': safe_weight
        })
    return trucks

# Load parts database
@st.cache_data
def load_parts_database():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    parts_path = os.path.join(BASE_DIR, "Truck batch.csv")
    if not os.path.exists(parts_path):
        st.error(f"품번 데이터베이스 파일이 존재하지 않습니다: {parts_path}")
        return {}
        
    parts = {}
    with open(parts_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
    header_idx = -1
    for idx, r in enumerate(rows):
        row_stripped = [cell.strip() for cell in r]
        if '품번' in row_stripped:
            header_idx = idx
            break
            
    if header_idx == -1:
        header_idx = 0
        
    header = rows[header_idx]
    header_stripped = [cell.strip() for cell in header]
    
    try:
        part_no_idx = header_stripped.index('품번')
        name_idx = header_stripped.index('품명')
        weight_idx = header_stripped.index('개당 중량')
        company_idx = header_stripped.index('업체명')
        address_idx = header_stripped.index('주소')
        manager_idx = header_stripped.index('담당자')
        contact_idx = header_stripped.index('연락처')
        width_idx = header_stripped.index('가로')
        length_idx = header_stripped.index('세로')
    except ValueError:
        part_no_idx = 1
        name_idx = 2
        weight_idx = 4
        company_idx = 5
        address_idx = 6
        manager_idx = 7
        contact_idx = 8
        width_idx = 9
        length_idx = 10
        
    for i in range(header_idx + 1, len(rows)):
        row = rows[i]
        if not row or len(row) <= max(part_no_idx, name_idx, weight_idx, company_idx, address_idx, manager_idx, contact_idx, width_idx, length_idx):
            continue
        part_no = row[part_no_idx].strip()
        if not part_no:
            continue
            
        part_name = row[name_idx].strip()
        weight = clean_num(row[weight_idx])
        
        company = row[company_idx].strip()
        if not company:
            company = "도착지 정보가 없습니다"
            
        address = row[address_idx].strip()
        manager = row[manager_idx].strip()
        contact = row[contact_idx].strip()
        width = clean_num(row[width_idx])
        length = clean_num(row[length_idx])
        
        parts[part_no.upper()] = {
            'part_no': part_no,
            'name': part_name,
            'weight': weight,
            'company': company,
            'address': address,
            'manager': manager,
            'contact': contact,
            'width': width,
            'length': length
        }
    return parts

# Helper function to find a part in the database by exact or 9-character match
def find_part(selected_part, parts):
    selected_part = selected_part.strip().upper()
    if not selected_part:
        return None
    # 1. Exact match
    if selected_part in parts:
        return parts[selected_part]
    # 2. 9-character prefix match
    if len(selected_part) >= 9:
        prefix = selected_part[:9]
        for k, v in parts.items():
            if k.startswith(prefix):
                return v
    return None

# Parse copy-pasted table data from Excel
def parse_pasted_data(text, parts_db):
    lines = text.strip().split('\n')
    parsed_items = []
    errors = []
    
    # Check if first line is a header
    start_idx = 0
    if lines:
        first_line = lines[0].strip()
        first_line_cells = []
        if '\t' in first_line:
            first_line_cells = [c.strip() for c in first_line.split('\t')]
        elif ',' in first_line:
            first_line_cells = [c.strip() for c in first_line.split(',')]
        else:
            first_line_cells = [c.strip() for c in first_line.split()]
            
        header_keywords = ['품번', '수량', '도착지', '단수', 'PART', 'QTY', 'DESTINATION', 'STACK']
        is_header = any(any(kw in cell.upper() for kw in header_keywords) for cell in first_line_cells)
        if is_header:
            start_idx = 1
            
    for idx, line in enumerate(lines[start_idx:]):
        line = line.strip()
        if not line:
            continue
            
        cells = []
        if '\t' in line:
            cells = [c.strip() for c in line.split('\t')]
        elif ',' in line:
            cells = [c.strip() for c in line.split(',')]
        else:
            cells = [c.strip() for c in line.split() if c.strip()]
            
        if not cells or not cells[0]:
            continue
            
        part_no = cells[0].upper()
        part_info = find_part(part_no, parts_db)
        
        if not part_info:
            errors.append(f"행 {idx + start_idx + 1}: 입력된 품번 '{part_no}'을(를) DB에서 찾을 수 없습니다. (앞자리 9자리 불일치)")
            continue
            
        qty = 1
        if len(cells) > 1 and cells[1]:
            try:
                qty = int(clean_num(cells[1]))
                if qty <= 0:
                    qty = 1
            except ValueError:
                qty = 1
                
        company = part_info['company']
        if len(cells) > 2 and cells[2]:
            company = cells[2].strip()
        if not company:
            company = "도착지 정보가 없습니다"
            
        stack = 1
        if len(cells) > 3 and cells[3]:
            try:
                stack = int(clean_num(cells[3]))
                if stack <= 0:
                    stack = 1
            except ValueError:
                stack = 1
                
        parsed_items.append({
            'part_no': part_no,
            'qty': qty,
            'company': company,
            'stack': stack,
            'name': part_info['name'],
            'weight': part_info['weight'],
            'width': part_info['width'],
            'length': part_info['length'],
            'address': part_info['address'],
            'manager': part_info['manager'],
            'contact': part_info['contact']
        })
        
    return parsed_items, errors

# 2D Shelf packing algorithm
def can_fit_shelf(items, W, L):
    strategies = [
        lambda w, l: (min(w, l), max(w, l)),
        lambda w, l: (max(w, l), min(w, l)),
        lambda w, l: (w, l)
    ]
    
    for strategy in strategies:
        oriented_items = []
        possible = True
        for w, l in items:
            ow, ol = strategy(w, l)
            if ow > W or ol > L:
                ow, ol = ol, ow
                if ow > W or ol > L:
                    possible = False
                    break
            oriented_items.append((ow, ol))
        
        if not possible:
            continue
            
        oriented_items.sort(key=lambda x: x[1], reverse=True)
        
        shelves = []
        for iw, il in oriented_items:
            placed = False
            for shelf in shelves:
                if shelf['used_width'] + iw <= W:
                    shelf['used_width'] += iw
                    placed = True
                    break
            if not placed:
                shelves.append({'height': il, 'used_width': iw})
                
        total_height = sum(shelf['height'] for shelf in shelves)
        if total_height <= L:
            return True, oriented_items, shelves
            
    return False, None, None

# Evaluate dispatch for a single company's items
def evaluate_dispatch(items_to_pack, trucks):
    physical_slots = []
    total_weight_kg = 0.0
    
    for it in items_to_pack:
        qty = it['qty']
        stack = it['stack']
        weight = it['weight']
        width = it['width']
        length = it['length']
        
        total_weight_kg += qty * weight
        slots_needed = math.ceil(qty / stack)
        
        for s in range(slots_needed):
            parts_in_slot = min(stack, qty - s * stack)
            slot_weight = parts_in_slot * weight
            physical_slots.append({
                'width': width,
                'length': length,
                'weight': slot_weight,
                'part_no': it['part_no'],
                'qty': parts_in_slot,
                'orig_width': it['orig_width'],
                'orig_length': it['orig_length']
            })
            
    total_weight_tons = total_weight_kg / 1000.0
    
    results = []
    for truck in trucks:
        t_w = truck['width']
        t_l = truck['length']
        t_limit = truck['safe_weight']
        
        weight_ok = total_weight_tons <= t_limit
        
        slot_dimensions = [(s['width'], s['length']) for s in physical_slots]
        size_ok, oriented_items, shelves = can_fit_shelf(slot_dimensions, t_w, t_l)
        
        results.append({
            'truck': truck,
            'weight_ok': weight_ok,
            'size_ok': size_ok,
            'total_weight_tons': total_weight_tons,
            'shelves': shelves
        })
        
    return results, physical_slots

# Recommend truck based on single truck evaluation (적정 적재 중량 기준 검토)
def recommend_trucks(results):
    valid_trucks = []
    for r in results:
        if r['size_ok'] and r['weight_ok']:
            valid_trucks.append(r)
            
    # Sort candidates by truck limit weight (smallest capacity first)
    valid_trucks.sort(key=lambda x: x['truck']['safe_weight'])
    return valid_trucks

# Multiple truck packing (적정 적재 중량 기준 검토)
def pack_multiple_trucks(physical_slots, trucks):
    remaining_slots = list(physical_slots)
    remaining_slots.sort(key=lambda x: (x['weight'], x['width'] * x['length']), reverse=True)
    
    dispatched_trucks = []
    sorted_trucks_desc = sorted(trucks, key=lambda x: x['safe_weight'], reverse=True)
    
    while remaining_slots:
        fit_all_truck = None
        for truck in sorted(trucks, key=lambda x: x['safe_weight']):
            t_w = truck['width']
            t_l = truck['length']
            t_limit = truck['safe_weight']
            
            total_rem_weight = sum(s['weight'] for s in remaining_slots) / 1000.0
            if total_rem_weight <= t_limit:
                dims = [(s['width'], s['length']) for s in remaining_slots]
                fit, _, _ = can_fit_shelf(dims, t_w, t_l)
                if fit:
                    fit_all_truck = truck
                    break
                    
        if fit_all_truck:
            dispatched_trucks.append({
                'truck': fit_all_truck,
                'slots': list(remaining_slots),
                'weight_tons': sum(s['weight'] for s in remaining_slots) / 1000.0
            })
            break
            
        packed_any = False
        for truck in sorted_trucks_desc:
            t_w = truck['width']
            t_l = truck['length']
            t_limit = truck['safe_weight']
            
            truck_slots = []
            truck_weight_kg = 0.0
            
            i = 0
            while i < len(remaining_slots):
                slot = remaining_slots[i]
                slot_weight_tons = slot['weight'] / 1000.0
                
                if (truck_weight_kg / 1000.0) + slot_weight_tons <= t_limit:
                    test_slots = truck_slots + [slot]
                    dims = [(s['width'], s['length']) for s in test_slots]
                    fit, _, _ = can_fit_shelf(dims, t_w, t_l)
                    
                    if fit:
                        truck_slots.append(slot)
                        truck_weight_kg += slot['weight']
                        remaining_slots.pop(i)
                        packed_any = True
                        continue
                i += 1
                
            if truck_slots:
                dispatched_trucks.append({
                    'truck': truck,
                    'slots': truck_slots,
                    'weight_tons': truck_weight_kg / 1000.0
                })
                break
                
        if not packed_any:
            unfit_slot = remaining_slots.pop(0)
            dispatched_trucks.append({
                'truck': {'name': '배차 불가 (규격 초과)', 'width': 0, 'length': 0, 'limit_weight': 0, 'safe_weight': 0},
                'slots': [unfit_slot],
                'weight_tons': unfit_slot['weight'] / 1000.0
            })
            
    return dispatched_trucks

# Application startup and load DB
trucks = load_truck_database()
parts = load_parts_database()

# Title UI
st.title("🚛 트럭 배차 시뮬레이터 (Excel 복사/붙여넣기 전용)")
st.markdown("""
엑셀(Excel)이나 표 데이터를 **드래그하여 통째로 복사한 뒤 아래 입력 칸에 붙여넣기(Ctrl+V)** 하시면 자동으로 계산이 이루어집니다.
* **마진 적용**: 안전 간격을 위해 가로/세로 각각 양쪽 100mm(총 +200mm) 여유 치수가 적용됩니다.
* **적재 기준 검토**: 중량 심사는 **최대 '적재중량'이 아닌 '적정 적재 중량'**을 기준으로 배차합니다.
* **도착지(업체명) 기준 그룹화**: 동일한 도착지(업체명)의 품목은 한 차량으로 묶어 최적의 트럭을 산출합니다.
* **유연한 9자리 매칭**: 품번이 DB에 없더라도 **앞자리 9글자**가 일치하는 품번 정보로 대체 연동합니다.
""")

# Setup Sidebar database info
with st.sidebar:
    st.header("⚙️ 데이터베이스 정보")
    st.metric("차량 종류 수", f"{len(trucks)}대")
    st.metric("등록된 품번 수", f"{len(parts)}개")
    st.markdown("---")
    st.subheader("💡 차량 목록 및 규격")
    for t in trucks:
        st.text(f"• {t['name']}\n  ({int(t['width'])}x{int(t['length'])} mm, 적량: {t['safe_weight']}t / 최대한도: {t['limit_weight']}t)")

# Main Layout
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("📋 엑셀 데이터 붙여넣기")
    
    # Text area for user to copy-paste
    pasted_text = st.text_area(
        "엑셀 표의 행들을 복사해서 아래에 붙여넣으세요:",
        height=250,
        placeholder="[예시 포맷 - 헤더 포함 여부 무관]\n품번\t수량\t도착지\t단수\n281401101CCN00\t8\t혜성기계(아메코)\t2\n281410101CCN00\t7\t혜성기계(아메코)\t1\n281415101CCN00\t7\t신화엔텍(아메코)\t1"
    )
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        calculate = st.button("🚚 배차 최적화 시작", type="primary", use_container_width=True)
    with col_btn2:
        clear = st.button("초기화", type="secondary", use_container_width=True)
        if clear:
            st.rerun()

with col_right:
    st.subheader("📊 시뮬레이션 결과")
    
    if calculate and pasted_text.strip():
        # Parse inputs
        parsed_items, parse_errors = parse_pasted_data(pasted_text, parts)
        
        # Display parsing warnings/errors if any
        if parse_errors:
            with st.error_tracker if hasattr(st, "error_tracker") else st.expander("⚠️ 일부 품번 매칭 오류 목록", expanded=True):
                for err in parse_errors:
                    st.write(err)
                    
        if not parsed_items:
            st.error("해석된 배차 항목이 없습니다. 올바른 포맷으로 붙여넣었는지 확인해주세요.")
        else:
            st.success(f"총 {len(parsed_items)}개의 배차 물품이 정상 매칭되었습니다.")
            
            # Show input preview
            st.markdown("##### 📥 파싱된 데이터 확인")
            df_preview = pd.DataFrame([{
                "품번": it['part_no'],
                "품명": it['name'],
                "수량": f"{it['qty']}개",
                "도착지": it['company'],
                "단수": f"{it['stack']}단",
                "제품 치수": f"{int(it['width'])}x{int(it['length'])} mm",
                "중량": f"{(it['weight'] * it['qty'])/1000.0:.3f} 톤"
            } for it in parsed_items])
            st.dataframe(df_preview, use_container_width=True)
            
            # Group items by company/destination
            grouped_items = {}
            for item in parsed_items:
                comp = item['company']
                if not comp:
                    comp = "도착지 정보가 없습니다"
                if comp not in grouped_items:
                    grouped_items[comp] = []
                grouped_items[comp].append(item)
                
            final_summary_rows = []
            
            st.markdown("##### 🚛 상세 배차 추천 내역 (적정 적재 중량 기준)")
            # Loop and evaluate
            for comp, items in grouped_items.items():
                with st.expander(f"🏢 도착지: {comp} ({len(items)}종류)", expanded=True):
                    # Add +200mm margin
                    items_to_pack = []
                    for it in items:
                        items_to_pack.append({
                            'part_no': it['part_no'],
                            'name': it['name'],
                            'width': it['width'] + 200,   # Margin
                            'length': it['length'] + 200, # Margin
                            'orig_width': it['width'],
                            'orig_length': it['length'],
                            'weight': it['weight'],
                            'qty': it['qty'],
                            'stack': it['stack'],
                            'address': it['address'],
                            'manager': it['manager'],
                            'contact': it['contact']
                        })
                        
                    total_weight_kg = sum(it['weight'] * it['qty'] for it in items_to_pack)
                    total_weight_tons = total_weight_kg / 1000.0
                    
                    # Run evaluations
                    results, physical_slots = evaluate_dispatch(items_to_pack, trucks)
                    valid_trucks = recommend_trucks(results)
                    
                    if valid_trucks:
                        best_r = valid_trucks[0]
                        t_name = best_r['truck']['name']
                        t_number = extract_truck_number(t_name)
                        st.markdown(f"🏆 **배차 추천:** :green[{t_name}] (실제 중량: {best_r['total_weight_tons']:.3f}톤 / 적정 한도: {best_r['truck']['safe_weight']}톤)")
                        
                        for it in items_to_pack:
                            final_summary_rows.append({
                                "품번": it['part_no'],
                                "품명": it['name'],
                                "수량": it['qty'],
                                "중량": round((it['weight'] * it['qty']) / 1000.0, 3),
                                "차량 명칭": t_number,
                                "도착지": comp,
                                "주소": it['address'] if it['address'] else "도착지 정보가 없습니다",
                                "담당자": it['manager'],
                                "연락처": it['contact']
                            })
                            
                    else:
                        st.markdown("❌ **단일 차량 배차 불가 (다중 분할 배차안 적용)**")
                        dispatched = pack_multiple_trucks(physical_slots, trucks)
                        
                        for idx, d in enumerate(dispatched):
                            t_name = d['truck']['name']
                            t_number = extract_truck_number(t_name)
                            st.write(f"🚛 **차량 {idx+1}:** {t_name} (적재량: {d['weight_tons']:.3f} 톤 / 적정 한도: {d['truck']['safe_weight']}톤)")
                            
                            # Summarize items in this truck
                            slot_counts = {}
                            for slot in d['slots']:
                                p = slot['part_no']
                                slot_counts[p] = slot_counts.get(p, 0) + slot['qty']
                                
                            for part, count in slot_counts.items():
                                p_info = next(it for it in items_to_pack if it['part_no'] == part)
                                st.write(f"  - `{part}` ({count}개 적재) | 중량: {(p_info['weight'] * count)/1000.0:.3f} 톤")
                                
                                final_summary_rows.append({
                                    "품번": part,
                                    "품명": p_info['name'],
                                    "수량": int(count),
                                    "중량": round((p_info['weight'] * count) / 1000.0, 3),
                                    "차량 명칭": t_number,
                                    "도착지": comp,
                                    "주소": p_info['address'] if p_info['address'] else "도착지 정보가 없습니다",
                                    "담당자": p_info['manager'],
                                    "연락처": p_info['contact']
                                })
                                
            # Output final table
            st.markdown("---")
            st.subheader("📋 최종 배차 요약 표")
            
            df_summary = pd.DataFrame(final_summary_rows)
            cols = ["품번", "품명", "수량", "중량", "차량 명칭", "도착지", "주소", "담당자", "연락처"]
            df_summary = df_summary[cols]
            
            st.dataframe(df_summary, use_container_width=True)
            
            csv_data = df_summary.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 배차 요약 파일 다운로드 (CSV)",
                data=csv_data,
                file_name="배차_요약_리스트.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        if calculate:
            st.warning("데이터를 입력해 주세요.")
        else:
            st.info("왼쪽 박스에 데이터를 붙여넣고 [배차 최적화 시작] 버튼을 누르시면 여기에 결과가 표시됩니다.")
