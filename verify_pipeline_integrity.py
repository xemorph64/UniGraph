import pandas as pd
from neo4j import GraphDatabase
import json
import time

# Configuration (adjust as needed)
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "unigraph_dev" # Placeholder - update if needed
DATASET_PATH = "transactions_dataset.csv"

def verify_pipeline():
    print("--- Starting Pipeline Integrity Check ---")
    
    # 1. Load sample data
    df = pd.read_csv(DATASET_PATH)
    sample_tx = df.iloc[0]
    tx_id = sample_tx['txn_id']
    print(f"Checking Transaction ID: {tx_id}")

    # 2. Check Neo4j for record
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        result = session.run("MATCH (t:Transaction {id: }) RETURN t", id=str(tx_id))
        record = result.single()
        
        if record:
            print("[PASS] Transaction found in Neo4j.")
            data = record['t']
            print(f"Data: {dict(data)}")
        else:
            print("[FAIL] Transaction NOT found in Neo4j.")

    # 3. Check ML score inference (simulated check)
    # This assumes a standard way to check the last inference
    # We will refine this after seeing the first run results.
    print("--- Pipeline Check Complete ---")

if __name__ == "__main__":
    verify_pipeline()
