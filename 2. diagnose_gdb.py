import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_AUTH = (os.getenv("NEO4J_USER_NAME"), os.getenv("NEO4J_PASSWORD"))

def diagnose():
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        print("=== Checking database node properties ===")
        # Randomly fetch 5 nodes to check whether property names are lowercase or capitalized
        result = session.run("MATCH (n) RETURN labels(n) as lbl, keys(n) as props, n LIMIT 5")
        for record in result:
            print(f"Label: {record['lbl']}")
            print(f"Property names (Keys): {record['props']}") 
            # Focus here! Is it ['name', 'value'] or ['Name', 'Value']?
            print("-" * 30)
            
    driver.close()

if __name__ == "__main__":
    diagnose()