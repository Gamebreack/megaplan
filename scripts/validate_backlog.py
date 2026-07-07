#!/usr/bin/env python3
import os
import sys
import re

def parse_id_parts(item_id):
    match = re.match(r"^([a-zA-Z0-9]+)-B([0-9]+)", item_id)
    if match:
        cycle = match.group(1)
        num = int(match.group(2))
        return cycle, num
    return None, None

def cycle_key(cycle_name):
    if cycle_name.isdigit():
        return (0, int(cycle_name))
    else:
        return (1, cycle_name.upper())

def parse_backlog_index(backlog_path):
    if not os.path.exists(backlog_path):
        print(f"Error: Backlog file not found at '{backlog_path}'", file=sys.stderr)
        sys.exit(1)
        
    with open(backlog_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    in_index = False
    headers = None
    items = []
    
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("#"):
            if re.match(r"^##+\s+Index", line_str, re.IGNORECASE):
                in_index = True
                continue
            elif in_index:
                in_index = False
                
        if in_index:
            if line_str.startswith("|"):
                cells = [c.strip() for c in line_str.split("|")[1:-1]]
                if not cells:
                    continue
                if all(re.match(r"^:-*-*|-*-*:-*|-*-*$", cell) for cell in cells):
                    continue
                if headers is None:
                    headers = [c.lower() for c in cells]
                else:
                    item = {}
                    for i, head in enumerate(headers):
                        if i < len(cells):
                            item[head] = cells[i]
                    if 'id' in item and item['id'] and not item['id'].lower().startswith('id'):
                        item['id'] = re.sub(r'[*_`]', '', item['id']).strip()
                        items.append(item)
    return items

def parse_detail_status(detail_path):
    if not os.path.exists(detail_path):
        return None
    with open(detail_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    match = re.search(r"##\s+Metadata\s*\n(.*?)(?=\n##|$)", content, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    
    metadata_table = match.group(1).strip()
    for line in metadata_table.split('\n'):
        line_str = line.strip()
        if line_str.startswith('|'):
            cells = [c.strip() for c in line_str.split('|')[1:-1]]
            if len(cells) >= 2:
                field = cells[0].strip().lower()
                value = cells[1].strip()
                if field == 'field' or re.match(r"^:-*-*|-*-*:-*|-*-*$", field):
                    continue
                if field == 'status':
                    return value.lower()
    return None

def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    backlog_path = os.path.join(project_root, "docs", "megaplan", "backlog.md")
    backlog_items_dir = os.path.join(project_root, "docs", "megaplan", "backlog-items")
    
    if not os.path.exists(backlog_path):
        print(f"Error: Backlog file not found at '{backlog_path}'", file=sys.stderr)
        sys.exit(1)
        
    items = parse_backlog_index(backlog_path)
    errors = []
    
    cycle_items = {}
    
    for item in items:
        item_id = item.get('id')
        index_status = item.get('status', '').strip().lower()
        if not item_id:
            continue
            
        detail_path = os.path.join(backlog_items_dir, f"{item_id}.md")
        if not os.path.exists(detail_path):
            errors.append(f"Missing B-item: {item_id} listed in index, but no detail file exists at '{detail_path}'")
            continue
            
        detail_status = parse_detail_status(detail_path)
        if detail_status is None:
            errors.append(f"Invalid B-item: {item_id} exists at '{detail_path}', but has no valid status in its Metadata table")
            continue
            
        if index_status != detail_status:
            errors.append(f"Status mismatch for {item_id}: index has '{index_status}', detail has '{detail_status}'")
            
        # Keep track of status for cycle gating
        cycle, _ = parse_id_parts(item_id)
        if cycle:
            if cycle not in cycle_items:
                cycle_items[cycle] = []
            cycle_items[cycle].append((item_id, index_status))
            
    # Check cycle gating
    sorted_cycles = sorted(cycle_items.keys(), key=cycle_key)
    for idx, cycle in enumerate(sorted_cycles):
        incomplete_items = [item_id for item_id, status in cycle_items[cycle] if status not in ['done', 'superseded']]
        if incomplete_items:
            for later_cycle in sorted_cycles[idx+1:]:
                for item_id, status in cycle_items[later_cycle]:
                    if status in ['in-progress', 'done']:
                        errors.append(
                            f"Cycle gating violation: Item {item_id} in later cycle '{later_cycle}' is '{status}', "
                            f"but earlier cycle '{cycle}' has incomplete items: {', '.join(incomplete_items)}"
                        )
                        
    if errors:
        print("Backlog validation failed with the following errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
        
    print("Backlog validation passed successfully.")
    sys.exit(0)

if __name__ == "__main__":
    main()
