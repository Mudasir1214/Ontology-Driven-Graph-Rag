import json
import os
import glob
from dotenv import load_dotenv
from neo4j import GraphDatabase, exceptions

# --- Configuration ---
# Load environment variables
load_dotenv()

# --- Local database configuration ---
# The password here must match the one you just set in the browser!
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

INPUT_DATA_FOLDER = "./input_data/batch_data"  # Make sure your JSON files are in this folder

def clean_props(props):
    """Clean properties by converting nested dict/list into string to prevent errors"""
    if not props: return {}
    cleaned = {}
    for k, v in props.items():
        if k in ['id', 'Id']: continue 
        if isinstance(v, (dict, list)):
            cleaned[k] = json.dumps(v, ensure_ascii=False)
        else:
            cleaned[k] = v
    return cleaned

def import_file(session, file_path):
    filename = os.path.basename(file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ {filename} failed to read: {e}")
        return

    # --- 1. Node import ---
    nodes_container = data.get('nodes')
    node_count = 0
    
    if isinstance(nodes_container, list):
        for node in nodes_container:
            if not node: continue
            labels_list = node.get('labels', [])
            labels = ":".join(labels_list)
            # Compatible with id and Id
            nid = node.get('id') or node.get('Id')
            props = clean_props(node.get('properties', {}))
            
            if nid and labels:
                # Optimization: using dynamic labels has slight risk, but your approach works
                # Best practice is to explicitly define labels, but this is acceptable in a generic script
                query = f"MERGE (n:`{labels}` {{id: $id}}) SET n += $props" 
                session.run(query, id=nid, props=props)
                node_count += 1
                
    elif isinstance(nodes_container, dict):
        # Label mapping table
        label_map = {
            "document": "Document", "chapter": "Chapter", "module": "Module",
            "rule": "Rule", "component": "Component", "material": "Material",
            "constraintGroups": "ConstraintGroup", "constraints": "Constraint",
            "space": "Space", "workstep": "WorkStep", "interface": "Interface",
            "product": "Product", "supplier": "Supplier"
        }
        
        for key, content in nodes_container.items():
            if not content: continue
            
            label = label_map.get(key, key.capitalize())
            items = content if isinstance(content, list) else [content]
            
            for item in items:
                if not item: continue
                nid = item.get('id') or item.get('Id')
                if not nid: continue
                
                props = clean_props(item)
                # Use backticks around label to avoid errors from special characters
                query = f"MERGE (n:`{label}` {{id: $id}}) SET n += $props"
                session.run(query, id=nid, props=props)
                node_count += 1
    
    # --- 2. Relationship import ---
    list_a = data.get('relationships') or []
    list_b = data.get('relations') or []
    rels_container = list_a + list_b
    
    rel_count = 0
    
    for rel in rels_container:
        if not rel: continue
        
        start_id = rel.get('start') or rel.get('from')
        end_id = rel.get('end') or rel.get('to')
        rtype = rel.get('type')
        
        if start_id and end_id and rtype:
            # If labels are not specified here and no index exists, performance will be slow
            # If you know the labels (e.g., Document), it's better to specify: MATCH (a:Document {id: $start})
            query = f"""
            MATCH (a {{id: $start}}), (b {{id: $end}})
            MERGE (a)-[r:`{rtype}`]->(b)
            """
            session.run(query, start=start_id, end=end_id)
            rel_count += 1

    print(f"✅ {filename} import successful (Nodes: {node_count}, Relationships: {rel_count})")

def main():
    if not os.path.exists(INPUT_DATA_FOLDER):
        os.makedirs(INPUT_DATA_FOLDER) # If it does not exist, create folder automatically for convenience
        print(f"⚠️ Folder '{INPUT_DATA_FOLDER}' does not exist. It has been created. Please place JSON files inside and run again.")
        return

    json_files = glob.glob(os.path.join(INPUT_DATA_FOLDER, "*.json"))
    if not json_files:
         print(f"⚠️ No .json files found in folder '{INPUT_DATA_FOLDER}'.")
         return

    print(f"📂 Found {len(json_files)} files. Starting batch import...\n")
    
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity() # Verify connection
        
        with driver.session() as session:
            for file_path in json_files:
                import_file(session, file_path)
                
        driver.close()
        print("\n🎉 All processing completed!")
    except exceptions.AuthError:
        print("\n❌ Authentication failed: incorrect username or password. Please check AUTH configuration.")
    except Exception as e:
        print(f"\n❌ Connection or execution error: {e}")

if __name__ == "__main__":
    main()