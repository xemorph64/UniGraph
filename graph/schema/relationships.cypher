// Relationship definitions for UniGRAPH base graph model.

MATCH (c:Customer {id: 'CUST-SEED-001'}), (a:Account {id: 'ACC-SEED-001'})
MERGE (c)-[:OWNS]->(a);

MATCH (a:Account {id: 'ACC-SEED-001'}), (t:Transaction {id: 'TXN-SEED-001'})
MERGE (a)-[:SENT {txn_id: 'TXN-SEED-001', amount: 1000.0, timestamp: datetime()}]->(t);

MATCH (t:Transaction {id: 'TXN-SEED-001'}), (a:Account {id: 'ACC-SEED-001'})
MERGE (t)-[:RECEIVED {txn_id: 'TXN-SEED-001', amount: 1000.0, timestamp: datetime()}]->(a);

MATCH (t:Transaction {id: 'TXN-SEED-001'}), (d:Device {id: 'DEV-SEED-001'})
MERGE (t)-[:USED_DEVICE]->(d);

MATCH (t:Transaction {id: 'TXN-SEED-001'}), (ip:IP {ip_address: 'IP-SEED-001'})
MERGE (t)-[:FROM_IP]->(ip);

MATCH (t:Transaction {id: 'TXN-SEED-001'}), (al:Alert {id: 'ALERT-SEED-001'})
MERGE (t)-[:FLAGGED_AS]->(al);
