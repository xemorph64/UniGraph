// Scheduled GDS jobs for fund flow analytics.
// Requires graph-data-science plugin.

CALL gds.graph.project.cypher(
  'unigraph-flow',
  'MATCH (a:Account) RETURN id(a) AS id',
  'MATCH (a:Account)-[:SENT]->(t:Transaction)-[:RECEIVED]->(b:Account) RETURN id(a) AS source, id(b) AS target, coalesce(t.amount, 0.0) AS amount'
)
YIELD graphName, nodeCount, relationshipCount;

CALL gds.pageRank.write('unigraph-flow', {
  maxIterations: 20,
  dampingFactor: 0.85,
  writeProperty: 'pagerank'
})
YIELD nodePropertiesWritten, ranIterations;

CALL gds.louvain.write('unigraph-flow', {
  writeProperty: 'community_id'
})
YIELD communityCount, modularity;

CALL gds.betweenness.write('unigraph-flow', {
  writeProperty: 'betweenness'
})
YIELD nodePropertiesWritten;

CALL gds.graph.drop('unigraph-flow')
YIELD graphName;
