import json
import os
import glob
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# --- Local database configuration ---
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

INPUT_DATA_FOLDER = "./input_data/batch_data"  # Make sure your JSON files are in this folder

def normalize_props(node_type, props):
    """
    Deep cleaning based on your JSON structure
    """
    if not props: return {}
    
    cleaned = {}
    
    # --- 1. Special handling for Material (critical fix) ---
    # Extract raw_text from attributes and promote it to text property
    if node_type.lower() == 'material':
        attrs = props.get('attributes')
        if isinstance(attrs, dict):
            if 'raw_text' in attrs:
                cleaned['text'] = attrs['raw_text']  # promote core text
            if 'application' in attrs:
                cleaned['application'] = attrs['application']
            # Do not keep the original complex attributes dictionary to avoid interference
    
    # --- 2. Handling for Rule ---
    # Ensure text field exists
    if 'text' in props:
        cleaned['text'] = props['text']

    # --- 3. General cleaning ---
    for k, v in props.items():
        # Skip ID (handled separately) and already processed attributes
        if k in ['id', 'Id', 'attributes']: continue
        
        # Normalize key names (convert to lowercase for easier retrieval)
        new_k = k.lower()
        
        # Map aliases
        if new_k == 'note': new_k = 'description'
        if new_k == 'value': new_k = 'value' # keep value
        
        # Process values
        if isinstance(v, (dict, list)):
            # Convert list or dict to string for storage
            cleaned[new_k] = json.dumps(v, ensure_ascii=False)
        else:
            cleaned[new_k] = v
            
    return cleaned

def clear_database(session):
    print("🧹 Clearing database (to prevent data contamination)...")
    session.run("MATCH (n) DETACH DELETE n")
    print("✅ Database cleared")

def import_file(session, file_path):
    filename = os.path.basename(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ {filename} read failed: {e}")
        return

    nodes_container = data.get('nodes')
    if not nodes_container: return

    node_count = 0
    
    # Handle dictionary format nodes (as shown in your snippet)
    if isinstance(nodes_container, dict):
        label_map = {
            "document": "Document", "chapter": "Chapter", "module": "Module",
            "rule": "Rule", "component": "Component", "material": "Material",
            "constraintGroups": "ConstraintGroup", "constraints": "Constraint",
            # ... other mappings remain default
        }
        
        for key, content in nodes_container.items():
            if not content: continue
            
            label = label_map.get(key, key.capitalize())
            items = content if isinstance(content, list) else [content]
            
            for item in items:
                if not item: continue
                
                # Get ID
                nid = item.get('id') or item.get('Id')
                if not nid: continue
                
                # Call cleaning function
                props = normalize_props(key, item)
                
                # Import node
                query = f"MERGE (n:{label} {{id: $id}}) SET n += $props"
                session.run(query, id=nid, props=props)
                node_count += 1

    # Handle relationships
    rels = data.get('relationships') or data.get('relations') or []
    rel_count = 0
    for rel in rels:
        start = rel.get('from') or rel.get('start')
        end = rel.get('to') or rel.get('end')
        rtype = rel.get('type')
        
        if start and end and rtype:
            query = f"""
            MATCH (a {{id: $start}}), (b {{id: $end}})
            MERGE (a)-[r:{rtype}]->(b)
            """
            session.run(query, start=start, end=end)
            rel_count += 1

    print(f"✅ {filename}: Nodes {node_count}, Relationships {rel_count}")

def main():
    if not os.path.exists(INPUT_DATA_FOLDER):
        print(f"❌ Folder {INPUT_DATA_FOLDER} does not exist")
        return

    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as session:
        clear_database(session) # Recommended to clear first for a clean state
        
        json_files = glob.glob(os.path.join(INPUT_DATA_FOLDER, "*.json"))
        print(f"📂 Starting import of {len(json_files)} files...")
        
        for f in json_files:
            import_file(session, f)
            
    driver.close()
    print("\n🎉 Import completed! The data structure is now more suitable for retrieval.")

if __name__ == "__main__":
    main()