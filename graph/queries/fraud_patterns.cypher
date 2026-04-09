// UniGRAPH Part 4 - Fraud Detection Patterns
// Graph model assumed in this file:
// (Account)-[:SENT]->(Transaction)-[:RECEIVED]->(Account)

// -----------------------------------------------------------------------------
// 4.1 Round-Trip / Circular Fund Flow Detection
// Money goes A -> B -> C -> ... -> back to A (3 to 6 account hops)
// -----------------------------------------------------------------------------
MATCH path = (start:Account)-[:SENT|RECEIVED*6..12]->(start)
WHERE length(path) % 2 = 0
  AND ALL(i IN range(0, size(relationships(path)) - 1)
      WHERE (i % 2 = 0 AND type(relationships(path)[i]) = 'SENT')
         OR (i % 2 = 1 AND type(relationships(path)[i]) = 'RECEIVED'))
WITH start, path,
  [i IN range(0, size(relationships(path)) - 1, 2) | coalesce(relationships(path)[i].amount, 0.0)] AS amounts,
  [i IN range(0, size(relationships(path)) - 1, 2) | relationships(path)[i].timestamp] AS timestamps
WHERE size(amounts) >= 3
  AND (reduce(s = 0.0, a IN amounts | s + a) / size(amounts)) > 10000
  AND ALL(ts IN timestamps WHERE ts >= datetime() - duration({hours: 24}))
RETURN
  start.id AS origin_account,
  [n IN nodes(path) WHERE 'Account' IN labels(n) | n.id] AS account_chain,
  amounts,
  timestamps,
  size(amounts) AS hop_count,
  reduce(s = 0.0, a IN amounts | s + a) AS total_amount_cycled
ORDER BY total_amount_cycled DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.2 Layering Detection (Multi-Hop Fund Movement)
// 3-5 hops, each hop within 2 hours of previous
// -----------------------------------------------------------------------------
MATCH path = (origin:Account)-[:SENT|RECEIVED*6..10]->(destination:Account)
WHERE origin <> destination
  AND length(path) % 2 = 0
  AND ALL(i IN range(0, size(relationships(path)) - 1)
      WHERE (i % 2 = 0 AND type(relationships(path)[i]) = 'SENT')
         OR (i % 2 = 1 AND type(relationships(path)[i]) = 'RECEIVED'))
WITH origin, destination, path,
     [i IN range(0, size(relationships(path)) - 1, 2) | relationships(path)[i]] AS sentRels,
     [n IN nodes(path) WHERE 'Account' IN labels(n) | n] AS accs
WHERE size(sentRels) >= 3 AND size(sentRels) <= 5
  AND ALL(r IN sentRels WHERE r.timestamp >= datetime() - duration({hours: 48}))
  AND ALL(i IN range(0, size(sentRels)-2)
      WHERE duration.between(sentRels[i].timestamp, sentRels[i+1].timestamp).hours <= 2)
  AND coalesce(origin.risk_score, 0.0) > 30
RETURN
  origin.id AS source_account,
  destination.id AS final_destination,
  [n IN accs | n.id] AS account_chain,
  [r IN sentRels | r.amount] AS amounts,
  [r IN sentRels | r.channel] AS channels,
  [r IN sentRels | r.timestamp] AS timestamps,
  size(sentRels) AS layers,
  origin.risk_score AS source_risk
ORDER BY layers DESC, source_risk DESC
LIMIT 100;

// -----------------------------------------------------------------------------
// 4.3 Structuring / Smurfing Detection
// 4.3.a One sender repeatedly just below threshold
// -----------------------------------------------------------------------------
MATCH (sender:Account)-[r:SENT]->(txn:Transaction)-[:RECEIVED]->(receiver:Account)
WHERE r.timestamp >= datetime() - duration({hours: 24})
  AND txn.amount >= 40000 AND txn.amount < 50000
WITH sender, collect(txn) AS txns, collect(r) AS rels,
     count(txn) AS txn_count, sum(txn.amount) AS total_amount
WHERE txn_count >= 3
RETURN
  sender.id AS entity_account,
  'SENDER_STRUCTURING' AS pattern_type,
  txn_count,
  total_amount,
  [t IN txns | t.id] AS transaction_ids,
  [t IN txns | t.amount] AS amounts,
  [t IN txns | t.timestamp] AS timestamps,
  sender.risk_score AS account_risk_score
ORDER BY txn_count DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.3.b Multiple senders funneling below-threshold amounts into one receiver
// -----------------------------------------------------------------------------
MATCH (sender:Account)-[r:SENT]->(txn:Transaction)-[:RECEIVED]->(receiver:Account)
WHERE r.timestamp >= datetime() - duration({hours: 24})
  AND txn.amount >= 40000 AND txn.amount < 50000
WITH receiver, collect(DISTINCT sender) AS senders,
     collect(txn) AS txns, sum(txn.amount) AS total_received
WHERE size(senders) >= 4
RETURN
  receiver.id AS entity_account,
  'RECEIVER_AGGREGATION' AS pattern_type,
  size(senders) AS distinct_senders,
  total_received,
  [s IN senders | s.id] AS sender_accounts,
  [t IN txns | t.id] AS transaction_ids,
  [t IN txns | t.amount] AS amounts,
  [t IN txns | t.timestamp] AS timestamps
ORDER BY distinct_senders DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.4 Dormant Account Awakening Detection
// -----------------------------------------------------------------------------
MATCH (receiver:Account)<-[r:RECEIVED]-(txn:Transaction)
WHERE receiver.is_dormant = true
   OR (receiver.last_active < datetime() - duration({days: 90})
       AND txn.amount > 50000)
WITH receiver, txn, r,
     duration.between(
       datetime(receiver.last_active),
       datetime(r.timestamp)
     ).days AS dormant_days
WHERE dormant_days > 90
RETURN
  receiver.id AS dormant_account,
  receiver.last_active AS was_last_active,
  dormant_days,
  txn.id AS awakening_transaction,
  txn.amount AS awakening_amount,
  txn.channel AS channel,
  txn.timestamp AS activation_timestamp,
  receiver.kyc_tier AS kyc_tier,
  receiver.risk_score AS risk_score
ORDER BY dormant_days DESC, txn.amount DESC
LIMIT 100;

// -----------------------------------------------------------------------------
// 4.5 Mule Account Network Detection
// -----------------------------------------------------------------------------
MATCH (sender:Account)-[:SENT]->(in_txn:Transaction)-[:RECEIVED]->(mule:Account)
      -[:SENT]->(out_txn:Transaction)-[:RECEIVED]->(final:Account)
WHERE duration.between(
        datetime(in_txn.timestamp),
        datetime(out_txn.timestamp)
      ).hours <= 2
  AND sender <> final
WITH mule,
     collect(DISTINCT sender) AS senders,
     collect(DISTINCT final) AS receivers,
     sum(in_txn.amount) AS total_received,
     sum(out_txn.amount) AS total_forwarded,
     count(in_txn) AS in_count,
     count(out_txn) AS out_count
WHERE size(senders) >= 3 AND size(receivers) >= 2
RETURN
  mule.id AS mule_account,
  size(senders) AS distinct_senders,
  size(receivers) AS distinct_receivers,
  in_count AS inbound_txns,
  out_count AS outbound_txns,
  total_received,
  total_forwarded,
  (total_received - total_forwarded) AS retained_amount,
  mule.account_age_days AS account_age_days,
  mule.kyc_tier AS kyc_tier,
  mule.risk_score AS current_risk_score
ORDER BY size(senders) DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.6 Fan-Out Detection (One Account Spraying to Many)
// -----------------------------------------------------------------------------
MATCH (sender:Account)-[r:SENT]->(txn:Transaction)-[:RECEIVED]->(receiver:Account)
WHERE r.timestamp >= datetime() - duration({hours: 6})
WITH sender,
     collect(DISTINCT receiver) AS receivers,
     collect(txn) AS txns,
     sum(txn.amount) AS total_sent,
     count(txn) AS txn_count
WHERE size(receivers) >= 5
RETURN
  sender.id AS fan_out_account,
  size(receivers) AS receiver_count,
  txn_count,
  total_sent,
  [rcv IN receivers | rcv.id] AS receiver_accounts,
  [rcv IN receivers | rcv.risk_score] AS receiver_risk_scores,
  sender.community_id AS community
ORDER BY receiver_count DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.7 Fan-In Detection (Many Accounts Sending to One)
// -----------------------------------------------------------------------------
MATCH (sender:Account)-[r:SENT]->(txn:Transaction)-[:RECEIVED]->(receiver:Account)
WHERE r.timestamp >= datetime() - duration({hours: 6})
WITH receiver,
     collect(DISTINCT sender) AS senders,
     collect(txn) AS txns,
     sum(txn.amount) AS total_received,
     count(txn) AS txn_count
WHERE size(senders) >= 5
RETURN
  receiver.id AS aggregating_account,
  size(senders) AS sender_count,
  txn_count,
  total_received,
  [s IN senders | s.id] AS sender_accounts,
  [s IN senders | s.community_id] AS sender_communities,
  receiver.account_age_days AS account_age_days,
  receiver.kyc_tier AS kyc_tier
ORDER BY total_received DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.8 Shared Device Risk (Multiple Accounts, One Device)
// -----------------------------------------------------------------------------
MATCH (d:Device)<-[:USED_DEVICE]-(t1:Transaction)<-[:SENT]-(a1:Account),
      (d)<-[:USED_DEVICE]-(t2:Transaction)<-[:SENT]-(a2:Account)
WHERE a1 <> a2
  AND NOT (a1)-[:LINKED_TO {link_type: 'SAME_CUSTOMER'}]-(a2)
WITH d, collect(DISTINCT a1) + collect(DISTINCT a2) AS accounts
UNWIND accounts AS a
WITH d, collect(DISTINCT a) AS unique_accounts
WHERE size(unique_accounts) >= 2
RETURN
  d.id AS shared_device,
  size(unique_accounts) AS account_count,
  [a IN unique_accounts | a.id] AS accounts_sharing_device,
  [a IN unique_accounts | a.risk_score] AS risk_scores,
  d.account_count AS device_account_count,
  d.first_seen AS device_first_seen
ORDER BY account_count DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 4.9 GDS - PageRank + Louvain (scheduled job)
// Requires Neo4j Graph Data Science plugin (gds.* procedures).
// -----------------------------------------------------------------------------
CALL gds.graph.project.cypher(
  'fund-flow-graph',
  'MATCH (a:Account) RETURN id(a) AS id',
  'MATCH (a:Account)-[:SENT]->(t:Transaction)-[:RECEIVED]->(b:Account) RETURN id(a) AS source, id(b) AS target, coalesce(t.amount, 0.0) AS amount'
)
YIELD graphName, nodeCount, relationshipCount;

CALL gds.pageRank.write('fund-flow-graph', {
  maxIterations: 20,
  dampingFactor: 0.85,
  writeProperty: 'pagerank'
})
YIELD nodePropertiesWritten, ranIterations;

CALL gds.louvain.write('fund-flow-graph', {
  writeProperty: 'community_id',
  includeIntermediateCommunities: false
})
YIELD communityCount, modularity;

CALL gds.graph.drop('fund-flow-graph')
YIELD graphName;

// -----------------------------------------------------------------------------
// 4.10 Full Subgraph Extraction for a Flagged Account (2-hop)
// -----------------------------------------------------------------------------
MATCH (center:Account {id: $accountId})
OPTIONAL MATCH path1 = (center)-[:SENT]->(t1:Transaction)-[:RECEIVED]->(n1:Account)
OPTIONAL MATCH path2 = (n1)-[:SENT]->(t2:Transaction)-[:RECEIVED]->(n2:Account)
OPTIONAL MATCH path3 = (center)<-[:RECEIVED]-(t3:Transaction)<-[:SENT]-(n3:Account)
WITH center,
     collect(DISTINCT n1) + collect(DISTINCT n2) + collect(DISTINCT n3) AS neighborsRaw,
     collect(DISTINCT t1) + collect(DISTINCT t2) + collect(DISTINCT t3) AS txRaw
UNWIND neighborsRaw AS n
WITH center, collect(DISTINCT n) AS neighbors, txRaw
UNWIND txRaw AS t
WITH center, neighbors, collect(DISTINCT t) AS transactions
RETURN
  center,
  neighbors,
  transactions,
  size(neighbors) AS neighborhood_size,
  size(transactions) AS transaction_count,
  reduce(s = 0.0, tx IN transactions | s + coalesce(tx.amount, 0.0)) AS total_volume;
