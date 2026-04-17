import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# --- Local database configuration ---
# The password here must match the one you just set in the browser!
URI = os.getenv("NEO4J_URI")
AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

def create_initial_data():
    print("Connecting to database...")
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
        print("✅ Connection successful!")
    except Exception as e:
        print(f"❌ Connection failed. Please check if the password is correct or if the terminal window is closed.\nError details: {e}")
        return

    # Cypher query: create the Avengers relationship graph
    cypher_query = """
    MERGE (p1:Person {name: '钢铁侠', id: 'IronMan'})
    MERGE (p2:Person {name: '美国队长', id: 'Cap'})
    MERGE (p3:Person {name: '雷神', id: 'Thor'})
    MERGE (p4:Person {name: '灭霸', id: 'Thanos'})
    
    MERGE (p1)-[:RELATION {type: '战友'}]->(p2)
    MERGE (p3)-[:RELATION {type: '战友'}]->(p1)
    MERGE (p1)-[:RELATION {type: '敌人'}]->(p4)
    MERGE (p2)-[:RELATION {type: '敌人'}]->(p4)
    """

    with driver.session() as session:
        session.run(cypher_query)
        print("✅ Data has been successfully written to the local database! Go run app.py to check it out!")

    driver.close()

if __name__ == "__main__":
    create_initial_data()