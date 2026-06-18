import csv
import os
import math
import sys

def clean_num(val):
    if not val:
        return 0.0
    val_clean = "".join(c for c in val if c.isdigit() or c == '.' or c == '-')
    if not val_clean:
        return 0.0
    try:
        return float(val_clean)
    except ValueError:
        return 0.0

def load_truck_database():
    truck_size_path = r"c:\Users\30240ydh\.gemini\antigravity\scratch\Truck Batch\truck size.csv"
    if not os.path.exists(truck_size_path):
        print(f"Error: {truck_size_path} not found.")
        sys.exit(1)
        
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

def load_parts_database():
    parts_path = r"c:\Users\30240ydh\.gemini\antigravity\scratch\Truck Batch\Truck batch.csv"
    if not os.path.exists(parts_path):
        print(f"Error: {parts_path} not found.")
        sys.exit(1)
        
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
        width_idx = header_stripped.index('가로')
        length_idx = header_stripped.index('세로')
    except ValueError:
        part_no_idx = 1
        name_idx = 2
        weight_idx = 4
        width_idx = 9
        length_idx = 10
        
    for i in range(header_idx + 1, len(rows)):
        row = rows[i]
        if not row or len(row) <= max(part_no_idx, name_idx, weight_idx, width_idx, length_idx):
            continue
        part_no = row[part_no_idx].strip()
        if not part_no:
            continue
            
        part_name = row[name_idx].strip()
        weight = clean_num(row[weight_idx])
        width = clean_num(row[width_idx])
        length = clean_num(row[length_idx])
        
        parts[part_no.upper()] = {
            'part_no': part_no,
            'name': part_name,
            'weight': weight,
            'width': width,
            'length': length
        }
    return parts

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
                'part_no': it['part_no']
            })
            
    total_weight_tons = total_weight_kg / 1000.0
    
    results = []
    for truck in trucks:
        t_w = truck['width']
        t_l = truck['length']
        t_limit = truck['limit_weight']
        t_safe = truck['safe_weight']
        
        weight_ok = total_weight_tons <= t_limit
        safe_weight_ok = total_weight_tons <= t_safe
        
        slot_dimensions = [(s['width'], s['length']) for s in physical_slots]
        size_ok, oriented_items, shelves = can_fit_shelf(slot_dimensions, t_w, t_l)
        
        results.append({
            'truck': truck,
            'weight_ok': weight_ok,
            'safe_weight_ok': safe_weight_ok,
            'size_ok': size_ok,
            'total_weight_tons': total_weight_tons,
            'shelves': shelves
        })
        
    return results, physical_slots

def recommend_trucks(results):
    valid_safety = []
    valid_max = []
    
    for r in results:
        if r['size_ok']:
            if r['weight_ok'] and r['safe_weight_ok']:
                valid_safety.append(r)
            elif r['weight_ok']:
                valid_max.append(r)
                
    valid_safety.sort(key=lambda x: x['truck']['limit_weight'])
    valid_max.sort(key=lambda x: x['truck']['limit_weight'])
    
    return valid_safety, valid_max

def pack_multiple_trucks(physical_slots, trucks):
    remaining_slots = list(physical_slots)
    remaining_slots.sort(key=lambda x: (x['weight'], x['width'] * x['length']), reverse=True)
    
    dispatched_trucks = []
    
    # Sort trucks by capacity descending to prioritize larger trucks for partitioning
    sorted_trucks_desc = sorted(trucks, key=lambda x: x['limit_weight'], reverse=True)
    
    while remaining_slots:
        # Optimization: Check if all remaining slots can fit in any single truck (find smallest that fits)
        fit_all_truck = None
        for truck in sorted(trucks, key=lambda x: x['limit_weight']):
            t_w = truck['width']
            t_l = truck['length']
            t_limit = truck['limit_weight']
            
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
        # Otherwise, pack greedily into the largest available truck
        for truck in sorted_trucks_desc:
            t_w = truck['width']
            t_l = truck['length']
            t_limit = truck['limit_weight']
            
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
                'truck': {'name': '배차 불가 (규격 초과)', 'width': 0, 'length': 0, 'limit_weight': 0},
                'slots': [unfit_slot],
                'weight_tons': unfit_slot['weight'] / 1000.0
            })
            
    return dispatched_trucks

def main():
    print("=" * 60)
    print("                배차 계산기 (Dispatch Calculator)                ")
    print("=" * 60)
    
    trucks = load_truck_database()
    parts = load_parts_database()
    
    print(f"차량 데이터베이스: {len(trucks)}대 로드 완료.")
    print(f"품번 데이터베이스: {len(parts)}개 로드 완료.")
    print("-" * 60)
    
    while True:
        print("\n[안내] 품번과 수량을 입력해주세요. 여러 항목을 한 번에 입력할 수 있습니다.")
        print("포맷: [품번] [수량] [3단적재여부(선택, '3' 또는 '3단' 입력)]")
        print("예시:")
        print("  137001101CCN00 4")
        print("  122401101CC00 2 3단")
        print("입력을 완료하려면 'done' 또는 빈 줄을 입력하십시오. 종료하려면 'exit'를 입력하십시오.")
        print("-" * 60)
        
        inputs = []
        while True:
            try:
                line = input("> ").strip()
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                return
                
            if line.lower() == 'exit':
                print("프로그램을 종료합니다.")
                return
            if line.lower() == 'done' or not line:
                break
                
            parts_split = line.replace(',', ' ').split()
            if not parts_split:
                continue
                
            part_no = parts_split[0].upper()
            qty = 1
            stack = 1
            
            if len(parts_split) > 1:
                qty_val = clean_num(parts_split[1])
                qty = int(qty_val) if qty_val > 0 else 1
                
            if len(parts_split) > 2:
                stack_str = parts_split[2]
                if '3' in stack_str:
                    stack = 3
                    
            if part_no not in parts:
                print(f"경고: 데이터베이스에 '{part_no}' 품번이 없습니다. 다시 입력해 주세요.")
                continue
                
            inputs.append({
                'part_no': part_no,
                'qty': qty,
                'stack': stack
            })
            print(f"추가됨: {part_no} | 수량: {qty}개 | 적재 방식: {'3단 적재' if stack == 3 else '1단 적재'}")
            
        if not inputs:
            print("입력된 항목이 없습니다.")
            continue
            
        items_to_pack = []
        for inp in inputs:
            part_info = parts[inp['part_no']]
            items_to_pack.append({
                'part_no': part_info['part_no'],
                'name': part_info['name'],
                'width': part_info['width'] + 200,   # 가로 양쪽 100mm 추가 (총 +200mm)
                'length': part_info['length'] + 200, # 세로 양쪽 100mm 추가 (총 +200mm)
                'orig_width': part_info['width'],
                'orig_length': part_info['length'],
                'weight': part_info['weight'],
                'qty': inp['qty'],
                'stack': inp['stack']
            })
            
        print("\n" + "=" * 60)
        print("                          계산 결과                          ")
        print("=" * 60)
        
        print("요청한 제품 목록 (여유 치수 가로+200mm, 세로+200mm 적용):")
        total_weight_kg = 0.0
        for it in items_to_pack:
            weight_str = f"{it['weight'] * it['qty'] / 1000.0:.3f} 톤"
            stack_str = "3단 적재" if it['stack'] == 3 else "1단 적재"
            print(f"- {it['part_no']} ({it['name']}): {it['qty']}개 | 크기: {int(it['orig_width'])}x{int(it['orig_length'])} mm (여유적용: {int(it['width'])}x{int(it['length'])} mm) | 총 중량: {weight_str} | 적재: {stack_str}")
            total_weight_kg += it['weight'] * it['qty']
            
        total_weight_tons = total_weight_kg / 1000.0
        print(f"총 중량 합계: {total_weight_tons:.3f} 톤")
        print("-" * 60)
        
        results, physical_slots = evaluate_dispatch(items_to_pack, trucks)
        valid_safety, valid_max = recommend_trucks(results)
        
        if valid_safety:
            print("[추천] 안전 적재 기준을 만족하는 차량:")
            best_r = valid_safety[0]
            print(f"👉 1순위 추천: {best_r['truck']['name']} (크기: {int(best_r['truck']['width'])}x{int(best_r['truck']['length'])} mm | 안전 적재: {best_r['truck']['safe_weight']}톤 | 실제 적재량: {best_r['total_weight_tons']:.3f}톤)")
            
            if len(valid_safety) > 1:
                print("기타 가능한 차량:")
                for r in valid_safety[1:]:
                    print(f"   - {r['truck']['name']} (안전 적재: {r['truck']['safe_weight']}톤)")
        elif valid_max:
            print("[알림] 안전 적재 기준을 초과하지만 최대 적재 한도 내에 위치한 차량:")
            best_r = valid_max[0]
            print(f"👉 1순위 추천 (한계 적재): {best_r['truck']['name']} (크기: {int(best_r['truck']['width'])}x{int(best_r['truck']['length'])} mm | 최대 적재량: {best_r['truck']['limit_weight']}톤 | 실제 적재량: {best_r['total_weight_tons']:.3f}톤)")
            print("⚠️ 경고: 적정 적재 중량을 초과하여 차량에 무리가 갈 수 있으니 주의 바랍니다.")
            
            if len(valid_max) > 1:
                print("기타 가능한 차량:")
                for r in valid_max[1:]:
                    print(f"   - {r['truck']['name']} (최대 적재: {r['truck']['limit_weight']}톤)")
        else:
            print("❌ 단일 차량 배차 불가: 단일 차량의 적재 크기 또는 중량 한도를 초과합니다.")
            print("\n[추천] 다중 차량 분할 배차안:")
            dispatched = pack_multiple_trucks(physical_slots, trucks)
            for idx, d in enumerate(dispatched):
                t_name = d['truck']['name']
                print(f"🚛 차량 {idx+1}: {t_name} (실제 적재량: {d['weight_tons']:.3f} 톤)")
                print("   적재된 제품 슬롯:")
                slot_counts = {}
                for slot in d['slots']:
                    slot_counts[slot['part_no']] = slot_counts.get(slot['part_no'], 0) + 1
                for part, cnt in slot_counts.items():
                    print(f"   - {part}: {cnt} 슬롯 분량")
                    
        print("=" * 60)

if __name__ == "__main__":
    main()
