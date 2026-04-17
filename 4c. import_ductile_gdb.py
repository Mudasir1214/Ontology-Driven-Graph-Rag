import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# --- Local database configuration ---
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

INPUT_DATA_FOLDER = "./input_data/data_ductile.json"  # The new JSON file to import

# Property cleaning function (unchanged)
def clean_props(props):
    cleaned = {}
    for k, v in props.items():
        if isinstance(v, (dict, list)):
            cleaned[k] = json.dumps(v, ensure_ascii=False)
        else:
            cleaned[k] = v
    return cleaned

def import_extra_data():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    # Read new file
    try:
        with open(INPUT_DATA_FOLDER, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read file: {e}")
        return

    with driver.session() as session:
        # Note: There is no "clear database" command here! Directly append!
        
        # 1. Import new nodes
        print(f"📦 Appending import of {len(data['nodes'])} new nodes...")
        for node in data['nodes']:
            labels = ":".join(node['labels'])
            safe_props = clean_props(node['properties'])
            
            # Use MERGE: If this ID already exists in the database (e.g., M-FIRE module), it remains unchanged; otherwise, it will be created.
            query = f"MERGE (n:{labels} {{id: $id}}) SET n += $props"
            session.run(query, id=node['id'], props=safe_props)
        
        # 2. Import new relationships
        print(f"🔗 Appending {len(data['relationships'])} new relationships...")
        count = 0
        for rel in data['relationships']:
            query = f"""
            MATCH (a {{id: $start}}), (b {{id: $end}})
            MERGE (a)-[r:{rel['type']}]->(b)
            """
            result = session.run(query, start=rel['start'], end=rel['end'])
            info = result.consume()
            if info.counters.relationships_created > 0:
                count += 1
        
        print(f"✅ Successfully appended {count} new connections!")

    driver.close()

if __name__ == "__main__":
    import_extra_data()