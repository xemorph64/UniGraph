// Investigation query pack.

// 1) Two-hop neighborhood around an account.
MATCH (center:Account {id: $accountId})
OPTIONAL MATCH p = (center)-[*1..2]-(n)
RETURN center, collect(DISTINCT n) AS neighbors, collect(DISTINCT p) AS paths;

// 2) Recent suspicious transactions for an account.
MATCH (a:Account {id: $accountId})-[:SENT]->(t:Transaction)
WHERE coalesce(t.risk_score, 0) >= 60
RETURN t.id AS txn_id, t.amount AS amount, t.channel AS channel, t.timestamp AS txn_time, t.risk_score AS risk_score
ORDER BY txn_time DESC
LIMIT 100;

// 3) Shortest path between two accounts.
MATCH (a:Account {id: $fromAccountId}), (b:Account {id: $toAccountId})
MATCH p = shortestPath((a)-[*..6]-(b))
RETURN p;
