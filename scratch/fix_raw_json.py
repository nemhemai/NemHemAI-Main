import os
import json

raw_dir = r"d:\NH_RAG\data\raw"
issues = []
fixed_count = 0

for f in os.listdir(raw_dir):
    if not f.endswith('.json'):
        continue
    
    path = os.path.join(raw_dir, f)
    with open(path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
        except Exception as e:
            print(f"Error parsing {f}: {e}")
            continue
            
    modified = False
    
    # Check issuing_authority
    if not data.get('issuing_authority'):
        print(f"{f}: Missing issuing_authority")
        data['issuing_authority'] = 'Unknown Authority'
        modified = True
        
    # Check jurisdiction
    if data.get('jurisdiction') not in ['central', 'state', 'municipal']:
        print(f"{f}: Invalid jurisdiction: {data.get('jurisdiction')}")
        # Try to infer or default
        if 'municip' in str(data.get('jurisdiction', '')).lower() or 'bmc' in str(data.get('issuing_authority', '')).lower():
            data['jurisdiction'] = 'municipal'
        elif 'india' in str(data.get('issuing_authority', '')).lower():
            data['jurisdiction'] = 'central'
        else:
            data['jurisdiction'] = 'state'
        modified = True
        
    # Check security_level
    if data.get('security_level') not in ['public', 'internal', 'confidential']:
        print(f"{f}: Invalid security_level: {data.get('security_level')}")
        data['security_level'] = 'public'
        modified = True
        
    if modified:
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        fixed_count += 1

print(f"Fixed {fixed_count} files out of {len([f for f in os.listdir(raw_dir) if f.endswith('.json')])} JSON files.")
