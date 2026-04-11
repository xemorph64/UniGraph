from __future__ import annotations

import argparse
import asyncio
import json

from neo4j import AsyncGraphDatabase


DEMO_DELETE_QUERY = """
MATCH (n)
WHERE
    (n:Account AND (
        n.id STARTS WITH 'ACC-NORMAL-' OR
        n.id STARTS WITH 'ACC-LAYER-' OR
        n.id STARTS WITH 'ACC-DORMANT-' OR
        n.id STARTS WITH 'ACC-MULE-'
    )) OR
    (n:Transaction AND (
        n.id STARTS WITH 'TXN-LAYER-' OR
        n.id STARTS WITH 'TXN-DORMANT-' OR
        n.id STARTS WITH 'TXN-MULE-'
    )) OR
    (n:Alert AND (
        n.id STARTS WITH 'ALT-LAYER-' OR
        n.id STARTS WITH 'ALT-DORM-' OR
        n.id STARTS WITH 'ALT-MULE-'
    )) OR
    (n:Device AND n.id STARTS WITH 'DEV-MULE-')
WITH count(n) AS to_delete, collect(n) AS nodes
FOREACH (node IN nodes | DETACH DELETE node)
RETURN to_delete AS deleted_count
"""


async def _cleanup(uri: str, user: str, password: str) -> dict:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            result = await session.run(DEMO_DELETE_QUERY)
            record = await result.single()
            deleted_count = int(record["deleted_count"]) if record else 0
        return {"status": "ok", "deleted_count": deleted_count}
    finally:
        await driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove known demo-seeded UniGRAPH graph entities from Neo4j"
    )
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="unigraph_dev")
    args = parser.parse_args()

    outcome = asyncio.run(_cleanup(args.uri, args.user, args.password))
    print(json.dumps(outcome, indent=2))


if __name__ == "__main__":
    main()
