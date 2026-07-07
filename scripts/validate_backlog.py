#!/usr/bin/env python3
import os
import sys
import re

def parse_id_parts(item_id):
    match = re.match(r"^([a-zA-Z0-9]+)-B([0-9]+)(?:\.B[0-9]+)?$", item_id)
    if match:
        cycle = match.group(1)
        num = int(match.group(2))
        return cycle, num
    return None, None

def cycle_key(cycle_name):
    parts = []
    for idx, part in enumerate(re.split(r'(\d+)', cycle_name)):
        if idx % 2 == 0:
            parts.append(part.upper())
        else:
            parts.append(int(part))
    return tuple(parts)

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
                    if 'id' in item and item['id']:
                        clean_id = re.sub(r'[*_`]', '', item['id']).strip()
                        # Extract ID from markdown link if present
                        link_match = re.match(r"^\[([^\]]+)\]\(([^\)]+)\)$", clean_id)
                        if link_match:
                            clean_id = link_match.group(1).strip()
                            
                        # Ignore placeholder or empty lines
                        if clean_id in ['', '—', '-']:
                            continue
                            
                        item['id'] = clean_id
                        if 'status' in item and item['status']:
                            item['status'] = re.sub(r'[*_`]', '', item['status']).strip()
                        items.append(item)
                            
    if headers is None or 'id' not in headers or 'status' not in headers:
        print("Error: Could not find a valid backlog table index with 'ID' and 'Status' columns.", file=sys.stderr)
        sys.exit(1)
        
    if 'depends on' not in headers:
        print("Warning: 'Depends on' column is missing from backlog table index. Dependency validation will be skipped.", file=sys.stderr)
        
    return items

def parse_markdown_section(content, section_name):
    """
    Extracts the content of a markdown section by name.
    """
    lines = content.split('\n')
    section_lines = []
    in_section = False
    in_code_block = False
    section_level = None
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            
        if not in_code_block:
            match = re.match(r"^(#+)\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                name = match.group(2).strip()
                name_clean = re.sub(r'[*_`]', '', name).strip().lower()
                if name_clean == section_name.lower():
                    in_section = True
                    section_level = level
                    continue
                elif in_section and level <= section_level:
                    break
                    
        if in_section:
            section_lines.append(line)
            
    if in_section:
        return '\n'.join(section_lines).strip()
    return ""

def parse_detail_metadata(detail_path):
    if not os.path.exists(detail_path):
        return {}
    with open(detail_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    metadata_table = parse_markdown_section(content, "Metadata")
    if not metadata_table:
        return {}
    
    result = {}
    for line in metadata_table.split('\n'):
        line_str = line.strip()
        if line_str.startswith('|'):
            cells = [c.strip() for c in line_str.split('|')[1:-1]]
            if len(cells) >= 2:
                field = re.sub(r'[*_`]', '', cells[0]).strip().lower()
                value = re.sub(r'[*_`]', '', cells[1]).strip()
                if field == 'field' or re.match(r"^:-*-*|-*-*:-*|-*-*$", field):
                    continue
                result[field] = value.lower()
    return result


def parse_detail_status(detail_path):
    metadata = parse_detail_metadata(detail_path)
    return metadata.get('status')

def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    backlog_path = os.path.join(project_root, "docs", "megaplan", "backlog.md")
    backlog_items_dir = os.path.join(project_root, "docs", "megaplan", "backlog-items")
    
    if not os.path.exists(backlog_path):
        print(f"Error: Backlog file not found at '{backlog_path}'", file=sys.stderr)
        sys.exit(1)
        
    items = parse_backlog_index(backlog_path)
    errors = []
    
    if not items:
        print("Error: No backlog items found in the index table.", file=sys.stderr)
        sys.exit(1)
        
    # Check for orphaned files (matching both B-item and Bug ID structures)
    all_detail_files = []
    if os.path.exists(backlog_items_dir):
        for f in os.listdir(backlog_items_dir):
            if f.endswith(".md"):
                item_id = os.path.splitext(f)[0]
                if re.match(r"^[a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?$", item_id):
                    all_detail_files.append(item_id)
                    
    indexed_ids = {item.get('id') for item in items if item.get('id')}
    for detail_id in all_detail_files:
        if detail_id not in indexed_ids:
            errors.append(f"Orphaned B-item: Detail file '{detail_id}.md' exists at '{os.path.join(backlog_items_dir, detail_id + '.md')}', but is not listed in the backlog index.")

    cycle_items = {}
    status_map = {item.get('id'): item.get('status', '').strip().lower() for item in items if item.get('id')}
    ALLOWED_STATUSES = {'pending', 'ready', 'in-progress', 'blocked', 'external', 'done', 'superseded'}
    
    for item in items:
        item_id = item.get('id')
        index_status = item.get('status', '').strip()
        index_status = re.sub(r'[*_`]', '', index_status).strip().lower()
        if not item_id:
            continue
            
        # Check ID regex format
        if not re.match(r"^[a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?$", item_id):
            errors.append(f"Malformed B-item ID in backlog table index: '{item_id}'")
            continue

        # Check status vocabulary in index
        if index_status not in ALLOWED_STATUSES:
            errors.append(f"Invalid status '{index_status}' for item {item_id} in backlog index. Allowed statuses: {sorted(ALLOWED_STATUSES)}")
            
        detail_path = os.path.join(backlog_items_dir, f"{item_id}.md")
        if not os.path.exists(detail_path):
            errors.append(f"Missing B-item: {item_id} listed in index, but no detail file exists at '{detail_path}'")
            continue
            
        detail_status = parse_detail_status(detail_path)
        if detail_status is None:
            errors.append(f"Invalid B-item: {item_id} exists at '{detail_path}', but has no valid status in its Metadata table")
            continue
            
        # Check status vocabulary in detail file
        if detail_status not in ALLOWED_STATUSES:
            errors.append(f"Invalid status '{detail_status}' for item {item_id} in detail file. Allowed statuses: {sorted(ALLOWED_STATUSES)}")
            
        if index_status != detail_status:
            errors.append(f"Status mismatch for {item_id}: index has '{index_status}', detail has '{detail_status}'")
            
        # Parse and check dependencies from index table if 'Depends on' column is present
        depends_on_raw = item.get('depends on', '').strip()
        dependencies = []
        if depends_on_raw and depends_on_raw not in ['—', '-', '']:
            for part in re.split(r'[,;]+', depends_on_raw):
                clean_part = re.sub(r'[*_`]', '', part).strip()
                link_match = re.match(r"^\[([^\]]+)\]\(([^\)]+)\)$", clean_part)
                if link_match:
                    clean_part = link_match.group(1).strip()
                if re.match(r"^[a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?$", clean_part):
                    dependencies.append(clean_part)
                else:
                    errors.append(f"Dependency error for {item_id}: Malformed dependency ID '{clean_part}' listed.")
                    
        if index_status in ['in-progress', 'done']:
            for dep in dependencies:
                dep_status = status_map.get(dep)
                if dep_status is None:
                    if re.match(r"^[a-zA-Z0-9]+-B[0-9]+(?:\.B[0-9]+)?$", dep):
                        errors.append(f"Dependency error for {item_id}: depends on '{dep}', which is not defined in the backlog index.")
                elif dep_status not in ['done', 'superseded']:
                    errors.append(f"Dependency violation: Item {item_id} is '{index_status}', but its dependency '{dep}' is '{dep_status}' (must be 'done' or 'superseded').")

        # Validate workflow step field (Karpathy Layer enforcement)
        ALLOWED_WORKFLOW_STEPS = {'document-pre', 'document (pre)', 'red', 'green', 'blue', 'document-post', 'document (post)', 'complete'}
        workflow_step = item.get('workflow step')
        if workflow_step:
            clean_step = re.sub(r'[*_`]', '', workflow_step).strip().lower()
            if clean_step not in ('', '—', '-') and clean_step not in ALLOWED_WORKFLOW_STEPS:
                errors.append(f"Invalid Workflow Step '{workflow_step}' for item {item_id}. Allowed: {sorted(ALLOWED_WORKFLOW_STEPS)}")

        if index_status == 'in-progress':
            detail_metadata = parse_detail_metadata(detail_path)
            detail_workflow = detail_metadata.get('workflow step', '')
            if detail_workflow in ('', '—', '-'):
                errors.append(f"Workflow Step missing: Item {item_id} is in-progress but has no Workflow Step set in its detail file metadata")

            spec_path = os.path.join(project_root, "SPEC.md")
            if os.path.exists(spec_path):
                spec_mtime = os.path.getmtime(spec_path)
                detail_mtime = os.path.getmtime(detail_path)
                if detail_mtime > spec_mtime:
                    errors.append(f"SPEC.md is stale: {item_id} was modified after SPEC.md was compiled. Re-run compile_spec.py")

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
