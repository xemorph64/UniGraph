from __future__ import annotations

import argparse
from neo4j import GraphDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed synthetic graph data into Neo4j")
    parser.add_argument("--neo4j-uri", default="bolt://localhost:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="unigraph_dev")
    parser.add_argument("--accounts", type=int, default=100)
    args = parser.parse_args()

    driver = GraphDatabase.driver(args.neo4j_uri, auth=(args.neo4j_user, args.neo4j_password))
    with driver.session() as session:
        session.run(
            """
            UNWIND range(1, $n) AS i
            MERGE (:Account {id: 'ACC-SEED-' + toString(i)})
            """,
            n=args.accounts,
        ).consume()
    driver.close()
    print(f"Seeded {args.accounts} Account nodes")


if __name__ == "__main__":
    main()
