# UniGRAPH — Master Opencode Agent Prompt
## PSBs Hackathon IDEA 2.0 | Team "Beyond Just Programming"

---

# 🎯 MISSION BRIEFING

You are an expert full-stack engineer tasked with making the **UniGRAPH** system fully
operational for a hackathon demo. UniGRAPH is an AI-powered, graph-native fund flow
tracking and fraud detection platform designed as a plugin for Union Bank of India's
Finacle Core Banking System.

**Your single most important goal**: By the end of your work, a judge should be able to
watch a live demo where a fraud transaction is injected, triggers an alert in under 500ms,
shows up in a visual graph explorer, and generates a draft STR compliance report — all in
one unbroken flow.

**Tech stack**: React + TypeScript (frontend) | FastAPI Python (backend) | Neo4j (graph DB)
| Redis | Cassandra | Apache Kafka | Flink | Apache Drools | PyTorch Geometric GNN |
XGBoost | SHAP | Groq API for LLM (llama-3.1-70b-versatile) | Docker Compose

**Repository root**: You are already inside the repo. Read the files before writing.

---

# 📋 ABSOLUTE RULES — READ BEFORE WRITING A SINGLE LINE OF CODE

1. **READ BEFORE WRITE**: Before modifying any file, read it completely. Never overwrite
   working code with stubs. Use targeted edits only.

2. **NEVER HARDCODE SECRETS**: All credentials go in `.env` (which already exists as
   `.env.example`). Copy `.env.example` to `.env` if it doesn't exist and fill in the
   values shown in this prompt.

3. **PRESERVE WHAT WORKS**: The repo already has P1/P2/P3 work done. The implementation
   plan confirms: docker-compose.yml has 12 services, ML models are implemented, backend
   routers are implemented, frontend App.tsx exists. Do NOT rewrite these from scratch.
   Fix gaps and wire things together.

4. **TEST EVERY STEP**: After implementing each major piece, run the verification command
   listed in the "VERIFICATION GATES" section. Do not proceed to the next step if the
   current step's verification fails.

5. **ASYNC EVERYTHING**: All Python DB operations must use async drivers. All FastAPI
   endpoints must be `async def`. No blocking calls in the event loop.

6. **TYPE HINTS EVERYWHERE**: Every Python function needs type hints. Every TypeScript
   component needs interfaces. This is non-negotiable for a banking system.

7. **STRUCTURED LOGGING**: Use `structlog` for Python logging. Every log entry must be
   JSON with `timestamp`, `service`, `level`, `event`, and relevant context fields.

8. **LLM IS GROQ**: The `.env` uses `GROQ_API_KEY`. The LLM service calls
   `https://api.groq.com/openai/v1/chat/completions` with model `llama-3.1-70b-versatile`.
   Do NOT attempt to set up Ollama or vLLM — that requires GPU hardware we don't have for
   the hackathon. Use Groq for speed and reliability.

9. **DEMO-FIRST PRIORITY ORDER**: If you must choose between features, always prioritize
   in this order:
   - (1) End-to-end pipeline working (data flows from mock CBS → Neo4j → alert)
   - (2) Graph explorer visual (Cytoscape.js showing fraud network)
   - (3) Real-time alerts via WebSocket
   - (4) STR report generation with LLM narrative
   - (5) Dashboard metrics and charts
   - (6) Everything else

10. **HACKATHON SHORTCUTS ARE OK**: You may use SQLite instead of Cassandra for
    transaction history if Cassandra is slow to set up. You may use in-memory Python
    dicts as a fallback for Redis if Redis is down. Always make the system degrade
    gracefully, never crash.

---

# 🏗️ PHASE 0: ENVIRONMENT SETUP

## Step 0.1 — Verify repository structure

Run these commands to understand what already exists:

```bash
ls -la
cat README.md
ls backend/app/routers/
ls frontend/src/
ls ml/models/
ls docker/
cat .env.example
```

## Step 0.2 — Create .env file

Create `.env` in the repo root with these values (fill in your actual Groq API key):

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=unigraph_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Cassandra
CASSANDRA_CONTACT_POINTS=localhost
CASSANDRA_KEYSPACE=unigraph_ts

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081

# JWT
JWT_SECRET=unigraph_hackathon_secret_2026_very_long_string_change_in_prod
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=480

# ML Service
ML_SERVICE_URL=http://localhost:8002

# LLM (Groq — fast, free tier available)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.1-70b-versatile
GROQ_API_URL=https://api.groq.com/openai/v1/chat/completions

# Finacle (mock for hackathon)
FINACLE_API_URL=http://localhost:8000/api/v1/mock/finacle
FINACLE_CLIENT_ID=mock_client
FINACLE_CLIENT_SECRET=mock_secret

# FIU-IND (mock for hackathon)
FIU_IND_API_URL=http://localhost:8000/api/v1/mock/fiu-ind
FIU_IND_MTLS_CERT_PATH=./compliance/certs/mock.crt

# NCRP (mock for hackathon)
NCRP_API_URL=http://localhost:8000/api/v1/mock/ncrp
NCRP_API_KEY=mock_ncrp_key

# App
APP_ENV=development
APP_DEBUG=true
APP_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Demo mode (seeds data automatically, no real Finacle needed)
DEMO_MODE=true
DEMO_SEED_ON_STARTUP=true
```

## Step 0.3 — Install all dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt
pip install groq httpx structlog python-dotenv pytest pytest-asyncio
cd ..

# ML service
cd ml
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

## Step 0.4 — Start Docker Compose stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

Wait 60 seconds for all services to become healthy, then verify:

```bash
docker compose -f docker/docker-compose.yml ps
# All 12 services should show "healthy" or "running"
```

If Neo4j, Kafka, or Redis fail to start, check logs:
```bash
docker compose -f docker/docker-compose.yml logs neo4j
docker compose -f docker/docker-compose.yml logs kafka-1
docker compose -f docker/docker-compose.yml logs redis
```

---

# 🔧 PHASE 1: FIX THE BACKEND CORE

## Step 1.1 — Audit and fix backend/app/config.py

Read `backend/app/config.py`. It should load from `.env`. Ensure it has ALL of these
settings. If any are missing, add them:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_CORS_ORIGINS: str = "http://localhost:5173"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "unigraph_dev"

    REDIS_URL: str = "redis://localhost:6379/0"

    CASSANDRA_CONTACT_POINTS: str = "localhost"
    CASSANDRA_KEYSPACE: str = "unigraph_ts"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480

    ML_SERVICE_URL: str = "http://localhost:8002"

    # LLM — Groq
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"

    FINACLE_API_URL: str = ""
    FINACLE_CLIENT_ID: str = ""
    FINACLE_CLIENT_SECRET: str = ""

    FIU_IND_API_URL: str = ""
    NCRP_API_URL: str = ""
    NCRP_API_KEY: str = ""

    DEMO_MODE: bool = True
    DEMO_SEED_ON_STARTUP: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

## Step 1.2 — Fix the Neo4j service (backend/app/services/neo4j_service.py)

Read the existing file. Ensure it implements ALL of these methods with proper async Neo4j
driver usage. If the file exists but methods are stubs, complete them:

```python
"""
Neo4j service for UniGRAPH.
Uses the async neo4j Python driver.
All queries must be async.
"""
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, Any
import structlog
from ..config import settings

logger = structlog.get_logger()

class Neo4jService:
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Initialize Neo4j async driver."""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        # Verify connectivity
        await self.driver.verify_connectivity()
        logger.info("neo4j_connected", uri=settings.NEO4J_URI)

    async def close(self):
        if self.driver:
            await self.driver.close()

    async def initialize_schema(self):
        """Create constraints and indexes on startup."""
        constraints = [
            "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT customer_id_unique IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX account_risk IF NOT EXISTS FOR (a:Account) ON (a.risk_score)",
            "CREATE INDEX txn_timestamp IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)",
            "CREATE INDEX alert_status IF NOT EXISTS FOR (al:Alert) ON (al.status)",
        ]
        async with self.driver.session() as session:
            for stmt in constraints + indexes:
                try:
                    await session.run(stmt)
                except Exception as e:
                    logger.warning("schema_stmt_failed", stmt=stmt[:60], error=str(e))
        logger.info("neo4j_schema_initialized")

    async def upsert_account(self, account_id: str, customer_id: str,
                              account_type: str = "SAVINGS", kyc_tier: int = 1,
                              risk_score: float = 0.0, is_dormant: bool = False) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (a:Account {id: $id})
                ON CREATE SET
                    a.customer_id = $customer_id,
                    a.account_type = $account_type,
                    a.kyc_tier = $kyc_tier,
                    a.risk_score = $risk_score,
                    a.is_dormant = $is_dormant,
                    a.community_id = 0,
                    a.pagerank = 0.0,
                    a.created_at = datetime()
                ON MATCH SET
                    a.risk_score = $risk_score,
                    a.is_dormant = $is_dormant
                RETURN a
                """,
                id=account_id, customer_id=customer_id, account_type=account_type,
                kyc_tier=kyc_tier, risk_score=risk_score, is_dormant=is_dormant
            )
            record = await result.single()
            return dict(record["a"]) if record else {}

    async def create_transaction_node(self, txn: dict) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (t:Transaction {id: $txn_id})
                ON CREATE SET
                    t.amount = $amount,
                    t.channel = $channel,
                    t.timestamp = datetime($timestamp),
                    t.from_account = $from_account,
                    t.to_account = $to_account,
                    t.risk_score = $risk_score,
                    t.is_flagged = $is_flagged,
                    t.rule_violations = $rule_violations,
                    t.description = $description,
                    t.device_id = $device_id
                RETURN t
                """,
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                channel=txn.get("channel", "IMPS"),
                timestamp=txn.get("timestamp", "2026-04-10T00:00:00Z"),
                from_account=txn["from_account"],
                to_account=txn["to_account"],
                risk_score=txn.get("risk_score", 0.0),
                is_flagged=txn.get("is_flagged", False),
                rule_violations=txn.get("rule_violations", []),
                description=txn.get("description", ""),
                device_id=txn.get("device_id", "unknown")
            )
            # Create SENT relationship between accounts
            await session.run(
                """
                MATCH (src:Account {id: $from_account})
                MATCH (dst:Account {id: $to_account})
                MERGE (src)-[r:SENT {txn_id: $txn_id}]->(dst)
                ON CREATE SET
                    r.amount = $amount,
                    r.timestamp = datetime($timestamp),
                    r.channel = $channel
                """,
                from_account=txn["from_account"],
                to_account=txn["to_account"],
                txn_id=txn["txn_id"],
                amount=txn["amount"],
                timestamp=txn.get("timestamp", "2026-04-10T00:00:00Z"),
                channel=txn.get("channel", "IMPS")
            )
            record = await result.single()
            return dict(record["t"]) if record else {}

    async def get_account_subgraph(self, account_id: str, hops: int = 2) -> dict:
        """Get N-hop subgraph for Cytoscape visualization."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH path = (center:Account {id: $account_id})-[:SENT*1..$hops]-(neighbor)
                UNWIND nodes(path) as n
                WITH collect(DISTINCT n) as nodes_list, path
                UNWIND relationships(path) as r
                WITH nodes_list, collect(DISTINCT r) as rels_list
                RETURN nodes_list, rels_list
                """,
                account_id=account_id, hops=hops
            )
            nodes = []
            edges = []
            seen_nodes = set()
            seen_edges = set()
            async for record in result:
                for node in record["nodes_list"]:
                    node_id = node.element_id
                    if node_id not in seen_nodes:
                        seen_nodes.add(node_id)
                        props = dict(node)
                        props["labels"] = list(node.labels)
                        nodes.append(props)
                for rel in record["rels_list"]:
                    rel_id = rel.element_id
                    if rel_id not in seen_edges:
                        seen_edges.add(rel_id)
                        edges.append({
                            "id": rel_id,
                            "type": rel.type,
                            "source": dict(rel.start_node).get("id", ""),
                            "target": dict(rel.end_node).get("id", ""),
                            **dict(rel)
                        })
            return {"nodes": nodes, "edges": edges}

    async def create_alert(self, alert: dict) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                CREATE (al:Alert {
                    id: $alert_id,
                    transaction_id: $transaction_id,
                    account_id: $account_id,
                    risk_score: $risk_score,
                    risk_level: $risk_level,
                    shap_top3: $shap_top3,
                    rule_flags: $rule_flags,
                    status: 'OPEN',
                    recommendation: $recommendation,
                    created_at: datetime(),
                    assigned_to: null
                })
                RETURN al
                """,
                **alert
            )
            record = await result.single()
            return dict(record["al"]) if record else {}

    async def get_alerts(self, status: Optional[str] = None,
                          min_risk_score: Optional[int] = None,
                          limit: int = 50) -> list[dict]:
        filters = []
        params: dict[str, Any] = {"limit": limit}
        if status:
            filters.append("al.status = $status")
            params["status"] = status
        if min_risk_score is not None:
            filters.append("al.risk_score >= $min_risk_score")
            params["min_risk_score"] = float(min_risk_score)
        where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (al:Alert)
                {where_clause}
                RETURN al
                ORDER BY al.created_at DESC
                LIMIT $limit
                """,
                **params
            )
            alerts = []
            async for record in result:
                a = dict(record["al"])
                # Convert datetime objects to strings
                for k, v in a.items():
                    if hasattr(v, "isoformat"):
                        a[k] = v.isoformat()
                alerts.append(a)
            return alerts

    async def get_alert_by_id(self, alert_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (al:Alert {id: $alert_id}) RETURN al",
                alert_id=alert_id
            )
            record = await result.single()
            if record:
                a = dict(record["al"])
                for k, v in a.items():
                    if hasattr(v, "isoformat"):
                        a[k] = v.isoformat()
                return a
            return None

    async def update_alert_status(self, alert_id: str, status: str,
                                   assigned_to: Optional[str] = None) -> dict:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (al:Alert {id: $alert_id})
                SET al.status = $status,
                    al.assigned_to = $assigned_to,
                    al.updated_at = datetime()
                RETURN al
                """,
                alert_id=alert_id, status=status, assigned_to=assigned_to
            )
            record = await result.single()
            return dict(record["al"]) if record else {}

    async def get_transaction(self, txn_id: str) -> Optional[dict]:
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (t:Transaction {id: $txn_id}) RETURN t",
                txn_id=txn_id
            )
            record = await result.single()
            if record:
                t = dict(record["t"])
                for k, v in t.items():
                    if hasattr(v, "isoformat"):
                        t[k] = v.isoformat()
                return t
            return None

    async def get_graph_stats(self) -> dict:
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (a:Account) WITH count(a) as accounts
                MATCH (t:Transaction) WITH accounts, count(t) as transactions
                MATCH (al:Alert) WITH accounts, transactions, count(al) as alerts
                MATCH (al:Alert {status: 'OPEN'}) WITH accounts, transactions, alerts, count(al) as open_alerts
                RETURN accounts, transactions, alerts, open_alerts
            """)
            record = await result.single()
            if record:
                return dict(record)
            return {"accounts": 0, "transactions": 0, "alerts": 0, "open_alerts": 0}

    async def find_fraud_patterns(self) -> list[dict]:
        """Find rapid layering patterns in the graph."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH path = (a:Account)-[:SENT*3..6]->(b:Account)
                WHERE a <> b
                WITH path, length(path) as hops,
                     reduce(total=0, r IN relationships(path) | total + r.amount) as total_flow
                WHERE total_flow > 100000
                RETURN
                    [n IN nodes(path) | n.id] as account_chain,
                    hops,
                    total_flow
                ORDER BY total_flow DESC
                LIMIT 10
            """)
            patterns = []
            async for record in result:
                patterns.append({
                    "account_chain": record["account_chain"],
                    "hops": record["hops"],
                    "total_flow": record["total_flow"]
                })
            return patterns

neo4j_service = Neo4jService()
```

## Step 1.3 — Fix the LLM service to use Groq

Create/fix `backend/app/services/llm_service.py` to use Groq API:

```python
"""
LLM service using Groq API (llama-3.1-70b-versatile).
Data stays secure — Groq is used for hackathon demo only.
In production, replace with on-premise Qwen 3.5 9B via vLLM.
"""
import httpx
import structlog
from typing import Optional
from ..config import settings

logger = structlog.get_logger()

STR_NARRATIVE_PROMPT = """You are UniGRAPH's AML investigation assistant for Union Bank of India.
You analyze suspicious transaction patterns and generate FIU-IND compliant STR narratives.
Always be professional, specific, and cite transaction IDs and amounts.
Respond in formal banking compliance language.

Generate a Suspicious Transaction Report (STR) narrative for the following case:

Case ID: {case_id}
Flagged Account: {account_id}
Risk Score: {risk_score}/100
Risk Level: {risk_level}

Transaction Chain:
{transaction_chain}

Rule Violations Detected:
{rule_violations}

Top Risk Factors (SHAP):
{shap_reasons}

Generate a concise STR narrative (max 500 words) covering:
1. Nature of suspicion
2. Transaction pattern description
3. Why this matches a known fraud typology
4. Recommended investigation steps
"""

CASE_SUMMARY_PROMPT = """Summarize this fraud investigation case for an investigator:

Account: {account_id}
Risk Score: {risk_score}
Alerts: {alert_count}
Rule violations: {rule_violations}
Transaction pattern: {pattern_description}

Provide a 3-sentence summary of:
1. What happened
2. Why it's suspicious
3. What to investigate next
"""

class LLMService:
    def __init__(self):
        self.api_url = settings.GROQ_API_URL
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL

    async def _call_groq(self, system_prompt: str, user_message: str,
                          max_tokens: int = 1000) -> str:
        if not self.api_key or self.api_key == "your_groq_api_key_here":
            logger.warning("groq_api_key_not_set")
            return self._mock_llm_response(user_message)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error("groq_api_error", error=str(e))
                return self._mock_llm_response(user_message)

    def _mock_llm_response(self, context: str) -> str:
        """Fallback when Groq API key is not configured."""
        return """SUSPICIOUS TRANSACTION REPORT — DRAFT

Based on the analysis performed by UniGRAPH's ML ensemble, this account has been
flagged for exhibiting patterns consistent with rapid layering fraud. Multiple
high-value transactions were detected within a compressed time window, with funds
moving through several intermediary accounts before reaching the destination.

The transaction velocity (8 transactions in 47 minutes) significantly exceeds the
account's historical baseline. The GraphSAGE GNN model detected that this account
belongs to a community with elevated fraud risk (community risk score: 0.87).

RECOMMENDED INVESTIGATION STEPS:
1. Freeze account pending investigation under PMLA 2002 Section 12
2. Request KYC documents from originating branch
3. Cross-reference beneficiary accounts with MuleHunter.AI database
4. File STR with FIU-IND within 7 days if suspicion is confirmed

[Note: This is a demo response. Configure GROQ_API_KEY for live LLM generation.]
"""

    async def generate_str_narrative(self, case_data: dict) -> str:
        """Generate STR narrative for a fraud case."""
        prompt = STR_NARRATIVE_PROMPT.format(
            case_id=case_data.get("case_id", "CASE-DEMO-001"),
            account_id=case_data.get("account_id", "ACC-UNKNOWN"),
            risk_score=case_data.get("risk_score", 0),
            risk_level=case_data.get("risk_level", "HIGH"),
            transaction_chain=case_data.get("transaction_chain", "No chain data"),
            rule_violations=", ".join(case_data.get("rule_violations", [])),
            shap_reasons="\n".join(case_data.get("shap_top3", []))
        )
        system = ("You are a senior AML compliance officer at Union Bank of India. "
                  "You write precise, professional STR reports in plain English. "
                  "Be specific about amounts, account IDs, and timestamps.")
        return await self._call_groq(system, prompt, max_tokens=800)

    async def summarize_case(self, case_data: dict) -> str:
        """Generate a quick case summary for investigators."""
        prompt = CASE_SUMMARY_PROMPT.format(**case_data)
        system = "You are a fraud investigation assistant. Be concise and actionable."
        return await self._call_groq(system, prompt, max_tokens=300)

    async def answer_investigator_question(self, question: str,
                                            context: dict) -> str:
        """Answer investigator's natural language questions about a case."""
        system = ("You are UniGRAPH's AML investigation assistant. "
                  "Answer questions about fraud cases using the provided context. "
                  "Always cite specific data points. Be direct and professional.")
        user_msg = f"""Case context: {context}

Investigator question: {question}

Answer in 2-3 sentences using specific data from the context."""
        return await self._call_groq(system, user_msg, max_tokens=400)

llm_service = LLMService()
```

## Step 1.4 — Implement the fraud scoring pipeline

Create/fix `backend/app/services/fraud_scorer.py` (new file if it doesn't exist):

```python
"""
Fraud scoring pipeline that combines rule-based and ML signals.
In demo mode, uses simplified heuristics when ML service is unavailable.
"""
import asyncio
import random
import uuid
from datetime import datetime
from typing import Optional
import structlog
from .neo4j_service import neo4j_service
from ..config import settings

logger = structlog.get_logger()

FRAUD_TYPOLOGIES = {
    "RAPID_LAYERING": {
        "description": "Multiple high-value transactions in rapid succession across accounts",
        "risk_boost": 30,
        "severity": "HIGH"
    },
    "STRUCTURING": {
        "description": "Transactions structured to avoid CTR threshold of ₹10L",
        "risk_boost": 25,
        "severity": "HIGH"
    },
    "DORMANT_AWAKENING": {
        "description": "Dormant account suddenly receiving/sending large amounts",
        "risk_boost": 35,
        "severity": "CRITICAL"
    },
    "MULE_NETWORK": {
        "description": "Account linked to mule network via shared device/IP",
        "risk_boost": 40,
        "severity": "CRITICAL"
    },
    "ROUND_TRIPPING": {
        "description": "Funds returned to originating account via circular path",
        "risk_boost": 28,
        "severity": "HIGH"
    }
}

class FraudScorer:
    async def score_transaction(self, txn: dict) -> dict:
        """
        Score a transaction using rule-based heuristics + ML signals.
        Returns: {risk_score, risk_level, recommendation, rule_violations, shap_top3}
        """
        risk_score = 0.0
        rule_violations = []
        shap_contributions = []

        amount = txn.get("amount", 0)
        channel = txn.get("channel", "IMPS")
        from_account = txn.get("from_account", "")
        is_dormant = txn.get("is_dormant", False)
        device_account_count = txn.get("device_account_count", 1)
        velocity_1h = txn.get("velocity_1h", 0)
        velocity_24h = txn.get("velocity_24h", 0)

        # Rule 1: High value transaction
        if amount > 500000:  # > ₹5L
            risk_score += 20
            shap_contributions.append(f"high_amount_₹{amount/100000:.1f}L: +20")
        elif amount > 100000:  # > ₹1L
            risk_score += 10
            shap_contributions.append(f"elevated_amount_₹{amount/100000:.1f}L: +10")

        # Rule 2: Velocity check
        if velocity_1h >= 5:
            risk_score += 25
            rule_violations.append("RAPID_LAYERING")
            shap_contributions.append(f"velocity_1h_{velocity_1h}_txns: +25")
        elif velocity_1h >= 3:
            risk_score += 12
            shap_contributions.append(f"elevated_velocity_1h_{velocity_1h}: +12")

        # Rule 3: Structuring detection (amounts just below ₹10L CTR threshold)
        if 800000 <= amount <= 990000:
            risk_score += 22
            rule_violations.append("STRUCTURING")
            shap_contributions.append("amount_near_ctr_threshold: +22")

        # Rule 4: Dormant account
        if is_dormant:
            risk_score += 35
            rule_violations.append("DORMANT_AWAKENING")
            shap_contributions.append("dormant_account_activity: +35")

        # Rule 5: Mule network (device shared by many accounts)
        if device_account_count > 3:
            risk_score += 30
            rule_violations.append("MULE_NETWORK")
            shap_contributions.append(f"device_shared_{device_account_count}_accounts: +30")

        # Rule 6: Channel switching (high risk channels)
        if channel in ["CASH", "SWIFT"]:
            risk_score += 8
            shap_contributions.append(f"high_risk_channel_{channel}: +8")

        # Rule 7: High 24h velocity
        if velocity_24h >= 10:
            risk_score += 15
            shap_contributions.append(f"velocity_24h_{velocity_24h}_txns: +15")

        # Cap at 100
        risk_score = min(round(risk_score), 100)

        # Determine risk level and recommendation
        if risk_score >= 90:
            risk_level = "CRITICAL"
            recommendation = "BLOCK"
        elif risk_score >= 80:
            risk_level = "HIGH"
            recommendation = "HOLD"
        elif risk_score >= 60:
            risk_level = "MEDIUM"
            recommendation = "REVIEW"
        else:
            risk_level = "LOW"
            recommendation = "ALLOW"

        result = {
            "txn_id": txn.get("txn_id", str(uuid.uuid4())),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "rule_violations": rule_violations,
            "shap_top3": shap_contributions[:3],
            "gnn_fraud_probability": min(risk_score / 100, 1.0),
            "if_anomaly_score": min(risk_score / 120, 1.0),
            "xgboost_risk_score": risk_score,
            "model_version": "unigraph-demo-v1.0",
            "scoring_timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.info("transaction_scored",
                    txn_id=result["txn_id"],
                    risk_score=risk_score,
                    risk_level=risk_level,
                    violations=rule_violations)

        return result

    async def should_create_alert(self, score_result: dict) -> bool:
        return score_result["risk_score"] >= 60

fraud_scorer = FraudScorer()
```

## Step 1.5 — Implement the demo data seeder

Create `scripts/demo_seeder.py` if it doesn't exist. This populates Neo4j with
synthetic fraud scenarios for the demo:

```python
"""
Demo data seeder for UniGRAPH hackathon demo.
Seeds 3 compelling fraud scenarios into Neo4j:
1. Rapid layering (6-hop chain)
2. Dormant account awakening
3. Mule network (shared device)

Run: python scripts/demo_seeder.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random
from neo4j import AsyncGraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "unigraph_dev")

async def seed_demo_data():
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    async with driver.session() as session:
        print("🌱 Clearing old demo data...")
        await session.run("MATCH (n) DETACH DELETE n")

        print("📊 Creating normal accounts...")
        # Create 50 normal accounts
        for i in range(1, 51):
            acc_id = f"ACC-NORMAL-{i:03d}"
            await session.run("""
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 1, risk_score: $risk, is_dormant: false,
                    community_id: 1, pagerank: 0.1, branch_code: 'MUM001',
                    created_at: datetime()
                })
            """, id=acc_id, cust_id=f"CUST-{i:03d}", risk=random.uniform(0, 15))

        print("🚨 SCENARIO 1: Rapid Layering (6-hop chain)...")
        layering_accounts = [f"ACC-LAYER-{i:03d}" for i in range(1, 8)]
        base_time = datetime.utcnow() - timedelta(minutes=30)

        for i, acc_id in enumerate(layering_accounts):
            await session.run("""
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 2, risk_score: $risk, is_dormant: false,
                    community_id: 2, pagerank: 0.3, branch_code: 'DEL001',
                    created_at: datetime()
                })
            """, id=acc_id, cust_id=f"CUST-LAYER-{i:03d}", risk=50 + i * 5)

        amounts = [750000, 748000, 745000, 743000, 740000, 738000]
        for i in range(len(layering_accounts) - 1):
            txn_time = (base_time + timedelta(minutes=i * 5)).isoformat() + "Z"
            txn_id = f"TXN-LAYER-{i+1:03d}"
            amount = amounts[i]
            await session.run("""
                MATCH (src:Account {id: $from_id})
                MATCH (dst:Account {id: $to_id})
                CREATE (t:Transaction {
                    id: $txn_id, amount: $amount, channel: 'IMPS',
                    timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                    risk_score: 85.0, is_flagged: true,
                    rule_violations: ['RAPID_LAYERING'],
                    description: 'Payment transfer', device_id: 'DEV-LAYER-001'
                })
                CREATE (src)-[:SENT {txn_id: $txn_id, amount: $amount,
                    timestamp: datetime($ts), channel: 'IMPS'}]->(dst)
            """, from_id=layering_accounts[i], to_id=layering_accounts[i+1],
                txn_id=txn_id, amount=amount, ts=txn_time)

        # Create alert for layering
        await session.run("""
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-LAYER-001',
                account_id: 'ACC-LAYER-001', risk_score: 87.0, risk_level: 'HIGH',
                shap_top3: ['velocity_1h_6_txns: +25', 'high_amount_₹7.5L: +20',
                             'rapid_succession_pattern: +15'],
                rule_flags: ['RAPID_LAYERING'], status: 'OPEN',
                recommendation: 'HOLD',
                created_at: datetime(), assigned_to: null
            })
        """, alert_id=f"ALT-LAYER-{uuid.uuid4().hex[:8].upper()}")

        print("💤 SCENARIO 2: Dormant Account Awakening...")
        dormant_acc = "ACC-DORMANT-001"
        await session.run("""
            CREATE (a:Account {
                id: $id, customer_id: 'CUST-DORMANT-001', account_type: 'SAVINGS',
                kyc_tier: 1, risk_score: 90.0, is_dormant: true,
                dormant_since: datetime('2025-09-01T00:00:00Z'),
                community_id: 3, pagerank: 0.05, branch_code: 'MUM002',
                created_at: datetime()
            })
        """, id=dormant_acc)

        receiver_acc = "ACC-DORMANT-RECV-001"
        await session.run("""
            CREATE (a:Account {
                id: $id, customer_id: 'CUST-RECV-001', account_type: 'CURRENT',
                kyc_tier: 2, risk_score: 40.0, is_dormant: false,
                community_id: 3, pagerank: 0.2, branch_code: 'MUM003',
                created_at: datetime()
            })
        """, id=receiver_acc)

        dormant_txn_time = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
        await session.run("""
            MATCH (src:Account {id: $from_id})
            MATCH (dst:Account {id: $to_id})
            CREATE (t:Transaction {
                id: 'TXN-DORMANT-001', amount: 1500000, channel: 'NEFT',
                timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                risk_score: 91.0, is_flagged: true,
                rule_violations: ['DORMANT_AWAKENING'],
                description: 'Transfer after 212 days dormancy',
                device_id: 'DEV-NEW-001'
            })
            CREATE (src)-[:SENT {txn_id: 'TXN-DORMANT-001', amount: 1500000,
                timestamp: datetime($ts), channel: 'NEFT'}]->(dst)
        """, from_id=dormant_acc, to_id=receiver_acc, ts=dormant_txn_time)

        await session.run("""
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-DORMANT-001',
                account_id: 'ACC-DORMANT-001', risk_score: 91.0, risk_level: 'CRITICAL',
                shap_top3: ['dormant_account_212_days: +35', 'high_amount_₹15L: +20',
                             'new_device_first_use: +12'],
                rule_flags: ['DORMANT_AWAKENING'], status: 'OPEN',
                recommendation: 'BLOCK',
                created_at: datetime(), assigned_to: null
            })
        """, alert_id=f"ALT-DORM-{uuid.uuid4().hex[:8].upper()}")

        print("🔗 SCENARIO 3: Mule Network (shared device)...")
        mule_device = "DEV-MULE-SHARED-001"
        mule_accounts = [f"ACC-MULE-{i:03d}" for i in range(1, 6)]

        for i, acc_id in enumerate(mule_accounts):
            await session.run("""
                CREATE (a:Account {
                    id: $id, customer_id: $cust_id, account_type: 'SAVINGS',
                    kyc_tier: 1, risk_score: $risk, is_dormant: false,
                    community_id: 4, pagerank: 0.15, branch_code: 'BLR001',
                    created_at: datetime()
                })
                CREATE (d:Device {id: $device_id, device_type: 'Android',
                    account_count: 5, first_seen: datetime()})
                MERGE (a)-[:USED_DEVICE {last_used: datetime()}]->(d)
            """, id=acc_id, cust_id=f"CUST-MULE-{i:03d}",
                risk=60 + i * 5, device_id=mule_device)

        # Create transactions between mule accounts
        for i in range(len(mule_accounts) - 1):
            mule_txn_time = (datetime.utcnow() - timedelta(hours=i)).isoformat() + "Z"
            await session.run("""
                MATCH (src:Account {id: $from_id})
                MATCH (dst:Account {id: $to_id})
                CREATE (t:Transaction {
                    id: $txn_id, amount: $amount, channel: 'UPI',
                    timestamp: datetime($ts), from_account: $from_id, to_account: $to_id,
                    risk_score: 82.0, is_flagged: true,
                    rule_violations: ['MULE_NETWORK'],
                    description: 'UPI transfer', device_id: $device_id
                })
                CREATE (src)-[:SENT {txn_id: $txn_id, amount: $amount,
                    timestamp: datetime($ts), channel: 'UPI'}]->(dst)
            """, from_id=mule_accounts[i], to_id=mule_accounts[i+1],
                txn_id=f"TXN-MULE-{i+1:03d}", amount=50000 * (i + 1),
                ts=mule_txn_time, device_id=mule_device)

        await session.run("""
            CREATE (al:Alert {
                id: $alert_id, transaction_id: 'TXN-MULE-001',
                account_id: 'ACC-MULE-001', risk_score: 83.0, risk_level: 'HIGH',
                shap_top3: ['device_shared_5_accounts: +30', 'mule_cluster_detected: +25',
                             'transaction_pattern_upi_rapid: +15'],
                rule_flags: ['MULE_NETWORK'], status: 'OPEN',
                recommendation: 'HOLD',
                created_at: datetime(), assigned_to: null
            })
        """, alert_id=f"ALT-MULE-{uuid.uuid4().hex[:8].upper()}")

        print("✅ Demo data seeded successfully!")
        print(f"   - 50 normal accounts")
        print(f"   - 7 layering accounts + 6 transactions + 1 alert")
        print(f"   - 1 dormant account + 1 transaction + 1 alert")
        print(f"   - 5 mule accounts + 4 transactions + 1 alert")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
```

---

# 🔧 PHASE 2: FIX THE BACKEND API ENDPOINTS

## Step 2.1 — Fix backend/app/main.py

Read the existing `backend/app/main.py`. Ensure it:
1. Starts the Neo4j connection on startup
2. Seeds demo data if `DEMO_SEED_ON_STARTUP=true`
3. Includes ALL routers
4. Has a WebSocket manager for real-time alerts

The main.py should look like this (read existing first, add what's missing):

```python
import asyncio
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .services.neo4j_service import neo4j_service
from .routers import transactions, accounts, alerts, cases, reports, ws, fraud_scoring, enforcement

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("unigraph_starting", env=settings.APP_ENV)
    try:
        await neo4j_service.connect()
        await neo4j_service.initialize_schema()
        logger.info("neo4j_ready")
    except Exception as e:
        logger.error("neo4j_connection_failed", error=str(e))
        logger.warning("running_without_neo4j_demo_will_use_fallback")

    if settings.DEMO_SEED_ON_STARTUP and settings.DEMO_MODE:
        try:
            # Import and run seeder
            import subprocess
            import sys
            logger.info("seeding_demo_data")
            # Don't block startup — run seeder in background
            asyncio.create_task(_seed_demo_data_async())
        except Exception as e:
            logger.error("demo_seed_failed", error=str(e))

    yield

    # Shutdown
    await neo4j_service.close()
    logger.info("unigraph_shutdown")

async def _seed_demo_data_async():
    """Run demo seeder as background task after startup."""
    await asyncio.sleep(5)  # Wait for services to be ready
    try:
        import subprocess
        import sys
        subprocess.run([sys.executable, "scripts/demo_seeder.py"], check=True)
        logger.info("demo_data_seeded")
    except Exception as e:
        logger.error("demo_seed_background_failed", error=str(e))

app = FastAPI(
    title="UniGRAPH — AI-Powered Fraud Detection API",
    version="1.0.0",
    description="Graph-native fund flow tracking for Union Bank of India",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    Instrumentator().instrument(app).expose(app)
except Exception:
    pass  # Prometheus optional for hackathon

# Include all routers
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(ws.router, prefix="/api/v1", tags=["websocket"])
app.include_router(fraud_scoring.router, prefix="/api/v1/fraud", tags=["fraud-scoring"])
app.include_router(enforcement.router, prefix="/api/v1/enforcement", tags=["enforcement"])

@app.get("/health")
async def health():
    neo4j_ok = False
    try:
        stats = await neo4j_service.get_graph_stats()
        neo4j_ok = True
    except Exception:
        stats = {}
    return {
        "status": "healthy",
        "version": "1.0.0",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "graph_stats": stats,
        "demo_mode": settings.DEMO_MODE
    }

@app.get("/api/v1/demo/reset")
async def reset_demo():
    """Reset demo data — useful for re-running the demo during judging."""
    try:
        import subprocess, sys
        subprocess.run([sys.executable, "scripts/demo_seeder.py"], check=True)
        return {"status": "demo_data_reset", "message": "3 fraud scenarios reloaded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

## Step 2.2 — Fix the alerts router

Read `backend/app/routers/alerts.py`. Ensure these endpoints work and return real data:

- `GET /api/v1/alerts` — returns list of alerts from Neo4j
- `GET /api/v1/alerts/{alert_id}` — returns single alert
- `POST /api/v1/alerts/{alert_id}/acknowledge` — updates status to INVESTIGATING
- `POST /api/v1/alerts/{alert_id}/escalate` — updates status + sets escalation flag

The router must import and use `neo4j_service` to fetch real data. If any endpoint
returns mock data instead of Neo4j data, fix it to use the service.

## Step 2.3 — Fix the reports router for STR generation

Read `backend/app/routers/reports.py`. Ensure the STR generation endpoint works:

```
POST /api/v1/reports/str/generate
Body: {"alert_id": "ALT-xxx", "case_notes": "..."}
Response: {"str_id": "STR-xxx", "narrative": "...", "status": "draft"}
```

This endpoint must:
1. Fetch the alert from Neo4j
2. Fetch the related account subgraph
3. Call `llm_service.generate_str_narrative(case_data)`
4. Return the narrative with metadata

## Step 2.4 — Fix the WebSocket for real-time alerts

Read `backend/app/routers/ws.py`. Ensure the WebSocket endpoint at
`/api/v1/ws/alerts` is working. It should:
1. Accept WebSocket connections
2. Send existing OPEN alerts when client connects
3. Allow broadcasting new alerts via a manager

Add a `ConnectionManager` class:

```python
from fastapi import WebSocket
from typing import List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()
```

---

# 🔧 PHASE 3: FIX THE TRANSACTION INGESTION ENDPOINT

## Step 3.1 — Create a working transaction ingestion flow

In `backend/app/routers/transactions.py`, ensure the `POST /api/v1/transactions/ingest`
endpoint does the FULL pipeline:

1. Receive transaction JSON
2. Score it with `fraud_scorer.score_transaction(txn)`
3. Create Account nodes in Neo4j (upsert) via `neo4j_service.upsert_account()`
4. Create Transaction node + SENT relationship in Neo4j
5. If risk_score >= 60: create Alert in Neo4j, broadcast via WebSocket manager
6. Return the full scoring result

This is the endpoint the demo will use to inject fraud scenarios in real time.

Full implementation example:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from ..services.neo4j_service import neo4j_service
from ..services.fraud_scorer import fraud_scorer
from ..routers.ws import manager as ws_manager

router = APIRouter()

class TransactionIngest(BaseModel):
    txn_id: Optional[str] = None
    from_account: str
    to_account: str
    amount: float
    channel: str = "IMPS"
    customer_id: Optional[str] = None
    description: Optional[str] = "Transfer"
    device_id: Optional[str] = None
    is_dormant: bool = False
    device_account_count: int = 1
    velocity_1h: int = 0
    velocity_24h: int = 0

@router.post("/ingest")
async def ingest_transaction(txn: TransactionIngest):
    txn_dict = txn.dict()
    txn_dict["txn_id"] = txn_dict.get("txn_id") or f"TXN-{uuid.uuid4().hex[:12].upper()}"
    txn_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    txn_dict["device_id"] = txn_dict.get("device_id") or "DEV-UNKNOWN"

    # Score the transaction
    score_result = await fraud_scorer.score_transaction(txn_dict)
    txn_dict["risk_score"] = score_result["risk_score"]
    txn_dict["rule_violations"] = score_result["rule_violations"]
    txn_dict["is_flagged"] = score_result["risk_score"] >= 60

    # Upsert accounts in Neo4j
    await neo4j_service.upsert_account(
        txn.from_account, txn.customer_id or f"CUST-{txn.from_account}",
        is_dormant=txn.is_dormant, risk_score=score_result["risk_score"]
    )
    await neo4j_service.upsert_account(
        txn.to_account, f"CUST-{txn.to_account}"
    )

    # Write to Neo4j graph
    await neo4j_service.create_transaction_node(txn_dict)

    # Create alert if high risk
    alert = None
    if await fraud_scorer.should_create_alert(score_result):
        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        alert = await neo4j_service.create_alert({
            "alert_id": alert_id,
            "transaction_id": txn_dict["txn_id"],
            "account_id": txn.from_account,
            "risk_score": score_result["risk_score"],
            "risk_level": score_result["risk_level"],
            "shap_top3": score_result["shap_top3"],
            "rule_flags": score_result["rule_violations"],
            "recommendation": score_result["recommendation"]
        })

        # Broadcast real-time alert via WebSocket
        await ws_manager.broadcast({
            "type": "ALERT_FIRED",
            "alert_id": alert_id,
            "txn_id": txn_dict["txn_id"],
            "account_id": txn.from_account,
            "risk_score": score_result["risk_score"],
            "risk_level": score_result["risk_level"],
            "recommendation": score_result["recommendation"],
            "shap_summary": " | ".join(score_result["shap_top3"][:2]),
            "timestamp": txn_dict["timestamp"]
        })

    return {
        "txn_id": txn_dict["txn_id"],
        "scoring": score_result,
        "alert_created": alert is not None,
        "alert_id": alert.get("id") if alert else None,
        "graph_written": True
    }
```

---

# 🔧 PHASE 4: FIX THE FRONTEND

## Step 4.1 — Audit frontend/src/App.tsx

Read the existing `frontend/src/App.tsx`. It should have routes for:
- `/` → Dashboard
- `/alerts` → Alert Inbox
- `/graph` → Graph Explorer
- `/cases` → Case Management
- `/reports` → Report Studio

If any routes are missing, add them. Do NOT rewrite the whole file.

## Step 4.2 — Fix the API service layer

Read `frontend/src/services/api.ts`. Ensure it exports these functions:

```typescript
// Base URL from env
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  // Alerts
  getAlerts: (params?: {status?: string, min_risk_score?: number}) =>
    fetch(`${API_BASE}/api/v1/alerts?${new URLSearchParams(params as any)}`).then(r => r.json()),

  getAlert: (id: string) =>
    fetch(`${API_BASE}/api/v1/alerts/${id}`).then(r => r.json()),

  acknowledgeAlert: (id: string) =>
    fetch(`${API_BASE}/api/v1/alerts/${id}/acknowledge`, {method: 'POST'}).then(r => r.json()),

  // Accounts
  getAccountSubgraph: (accountId: string, hops: number = 2) =>
    fetch(`${API_BASE}/api/v1/accounts/${accountId}/graph?hops=${hops}`).then(r => r.json()),

  // Transactions
  ingestTransaction: (txn: object) =>
    fetch(`${API_BASE}/api/v1/transactions/ingest`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(txn)
    }).then(r => r.json()),

  // Reports
  generateSTR: (alertId: string, notes?: string) =>
    fetch(`${API_BASE}/api/v1/reports/str/generate`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({alert_id: alertId, case_notes: notes || ''})
    }).then(r => r.json()),

  // Health
  getHealth: () =>
    fetch(`${API_BASE}/health`).then(r => r.json()),

  // Graph stats
  getGraphStats: () =>
    fetch(`${API_BASE}/health`).then(r => r.json()).then(h => h.graph_stats || {}),

  // Demo
  resetDemo: () =>
    fetch(`${API_BASE}/api/v1/demo/reset`).then(r => r.json()),
};
```

## Step 4.3 — Build the Graph Explorer component (MOST IMPORTANT)

This is your "wow moment". The graph explorer must use Cytoscape.js to show the fraud
network visually.

Create/fix `frontend/src/components/GraphExplorer/GraphExplorer.tsx`:

```typescript
import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { api } from '../../services/api';

interface GraphExplorerProps {
  accountId?: string;
  onAlertSelect?: (alert: any) => void;
}

const RISK_COLORS: Record<string, string> = {
  high: '#ef4444',    // red-500
  medium: '#f97316',  // orange-500
  low: '#22c55e',     // green-500
  default: '#6366f1', // indigo-500
};

function getRiskColor(riskScore: number): string {
  if (riskScore >= 80) return RISK_COLORS.high;
  if (riskScore >= 60) return RISK_COLORS.medium;
  if (riskScore >= 30) return RISK_COLORS.default;
  return RISK_COLORS.low;
}

export function GraphExplorer({ accountId, onAlertSelect }: GraphExplorerProps) {
  const cyRef = useRef<HTMLDivElement>(null);
  const cyInstance = useRef<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(accountId || '');
  const [hops, setHops] = useState(2);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  const loadGraph = async (accId: string) => {
    if (!accId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAccountSubgraph(accId, hops);
      renderGraph(data);
    } catch (e) {
      setError('Failed to load graph. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = (data: { nodes: any[], edges: any[] }) => {
    if (!cyRef.current) return;

    const elements = [
      ...data.nodes.map((node: any) => ({
        data: {
          id: node.id || node.element_id,
          label: node.id,
          riskScore: node.risk_score || 0,
          type: (node.labels || ['Account'])[0],
          isDormant: node.is_dormant || false,
          communityId: node.community_id || 0,
        }
      })),
      ...data.edges.map((edge: any) => ({
        data: {
          id: edge.id || `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
          amount: edge.amount || 0,
          channel: edge.channel || '',
          label: edge.amount ? `₹${(edge.amount/1000).toFixed(0)}K` : '',
        }
      }))
    ];

    if (cyInstance.current) {
      cyInstance.current.destroy();
    }

    cyInstance.current = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: any) => getRiskColor(ele.data('riskScore')),
            'label': 'data(label)',
            'color': '#ffffff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'width': (ele: any) => Math.max(40, Math.min(80, ele.data('riskScore') * 0.8)),
            'height': (ele: any) => Math.max(40, Math.min(80, ele.data('riskScore') * 0.8)),
            'border-width': 2,
            'border-color': '#ffffff',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
          }
        },
        {
          selector: 'node[isDormant = true]',
          style: {
            'border-color': '#fbbf24',
            'border-width': 4,
            'border-style': 'dashed',
          }
        },
        {
          selector: 'edge',
          style: {
            'width': (ele: any) => Math.max(1, Math.min(6, ele.data('amount') / 100000)),
            'line-color': '#94a3b8',
            'target-arrow-color': '#94a3b8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '9px',
            'color': '#64748b',
            'text-rotation': 'autorotate',
          }
        },
        {
          selector: ':selected',
          style: {
            'border-color': '#facc15',
            'border-width': 4,
            'line-color': '#facc15',
          }
        }
      ],
      layout: {
        name: 'cose',
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        coolingFactor: 0.99,
        minTemp: 1.0
      }
    });

    // Click handler for node expansion
    cyInstance.current.on('tap', 'node', async (evt: any) => {
      const node = evt.target;
      const nodeId = node.data('id');
      // Expand 1 more hop from clicked node
      try {
        const expanded = await api.getAccountSubgraph(nodeId, 1);
        const newElements = [
          ...expanded.nodes.map((n: any) => ({
            data: {
              id: n.id, label: n.id, riskScore: n.risk_score || 0,
              type: (n.labels || ['Account'])[0], isDormant: n.is_dormant || false,
            }
          })),
          ...expanded.edges.map((e: any) => ({
            data: { id: e.id, source: e.source, target: e.target,
                    amount: e.amount || 0, label: e.amount ? `₹${(e.amount/1000).toFixed(0)}K` : '' }
          }))
        ];
        cyInstance.current.add(newElements);
        cyInstance.current.layout({ name: 'cose', fit: true }).run();
      } catch (e) { /* ignore */ }
    });

    setStats({ nodes: elements.filter(e => !e.data.source).length,
                edges: elements.filter(e => e.data.source).length });
  };

  // Load initial demo graph
  useEffect(() => {
    if (accountId) {
      setSelectedAccount(accountId);
      loadGraph(accountId);
    } else {
      // Load layering scenario by default
      loadGraph('ACC-LAYER-001');
    }
  }, [accountId]);

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* Controls */}
      <div className="flex items-center gap-3 p-3 bg-gray-800 border-b border-gray-700">
        <input
          type="text"
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          placeholder="Account ID (e.g. ACC-LAYER-001)"
          className="flex-1 px-3 py-1.5 bg-gray-700 text-white rounded text-sm border border-gray-600 focus:border-indigo-500 outline-none"
        />
        <select
          value={hops}
          onChange={(e) => setHops(Number(e.target.value))}
          className="px-2 py-1.5 bg-gray-700 text-white rounded text-sm border border-gray-600"
        >
          {[1,2,3,4].map(h => <option key={h} value={h}>{h} hop{h>1?'s':''}</option>)}
        </select>
        <button
          onClick={() => loadGraph(selectedAccount)}
          disabled={loading}
          className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Explore'}
        </button>
        <div className="text-xs text-gray-400">
          {stats.nodes} nodes · {stats.edges} edges
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-3 py-1.5 bg-gray-850 border-b border-gray-700 text-xs">
        {[
          { color: '#ef4444', label: 'Critical risk (80+)' },
          { color: '#f97316', label: 'High risk (60-79)' },
          { color: '#6366f1', label: 'Medium risk' },
          { color: '#22c55e', label: 'Low risk' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1 text-gray-400">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span>{label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 text-gray-400 ml-2">
          <div className="w-3 h-3 rounded-full border-2 border-dashed border-yellow-400" />
          <span>Dormant</span>
        </div>
      </div>

      {/* Graph canvas */}
      <div className="flex-1 relative">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-red-900/50 border border-red-700 rounded p-4 text-red-300 text-sm max-w-sm text-center">
              {error}
              <br />
              <button onClick={() => loadGraph(selectedAccount)}
                className="mt-2 px-3 py-1 bg-red-700 hover:bg-red-600 rounded text-xs">
                Retry
              </button>
            </div>
          </div>
        )}
        <div ref={cyRef} className="w-full h-full" style={{ minHeight: '500px' }} />
      </div>

      {/* Quick-load demo scenarios */}
      <div className="flex items-center gap-2 p-2 bg-gray-800 border-t border-gray-700">
        <span className="text-xs text-gray-500">Demo scenarios:</span>
        {[
          { label: '🔴 Rapid Layering', id: 'ACC-LAYER-001' },
          { label: '💤 Dormant Awakening', id: 'ACC-DORMANT-001' },
          { label: '🔗 Mule Network', id: 'ACC-MULE-001' },
        ].map(({ label, id }) => (
          <button key={id}
            onClick={() => { setSelectedAccount(id); loadGraph(id); }}
            className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
```

Make sure `cytoscape` is installed:
```bash
cd frontend && npm install cytoscape @types/cytoscape
```

## Step 4.4 — Build the Alert Inbox component

Create/fix `frontend/src/components/AlertInbox/AlertInbox.tsx` with:
- Real-time WebSocket connection for live alerts
- List of alerts fetched from `GET /api/v1/alerts`
- Risk score badges (red for CRITICAL/HIGH, orange for MEDIUM)
- Click on alert → loads graph for that account
- "Generate STR" button per alert

```typescript
import { useEffect, useState, useCallback } from 'react';
import { api } from '../../services/api';

interface Alert {
  id: string;
  account_id: string;
  transaction_id: string;
  risk_score: number;
  risk_level: string;
  recommendation: string;
  rule_flags: string[];
  shap_top3: string[];
  status: string;
  created_at: string;
}

const RISK_BADGE_STYLES: Record<string, string> = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-orange-500 text-white',
  MEDIUM: 'bg-yellow-500 text-black',
  LOW: 'bg-green-600 text-white',
};

interface AlertInboxProps {
  onAccountSelect?: (accountId: string) => void;
  onSTRGenerate?: (alert: Alert, narrative: string) => void;
}

export function AlertInbox({ onAccountSelect, onSTRGenerate }: AlertInboxProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'INVESTIGATING'>('ALL');

  const fetchAlerts = useCallback(async () => {
    try {
      const data = await api.getAlerts(filter === 'ALL' ? {} : { status: filter });
      setAlerts(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to fetch alerts:', e);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // WebSocket for real-time alerts
  useEffect(() => {
    const wsUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000')
      .replace('http', 'ws') + '/api/v1/ws/alerts';
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'ALERT_FIRED') {
        // Prepend new alert
        const newAlert: Alert = {
          id: data.alert_id,
          account_id: data.account_id,
          transaction_id: data.txn_id,
          risk_score: data.risk_score,
          risk_level: data.risk_level,
          recommendation: data.recommendation,
          rule_flags: [],
          shap_top3: [data.shap_summary],
          status: 'OPEN',
          created_at: data.timestamp,
        };
        setAlerts(prev => [newAlert, ...prev]);
      }
    };

    return () => ws.close();
  }, []);

  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  const handleGenerateSTR = async (alert: Alert) => {
    setGenerating(alert.id);
    try {
      const result = await api.generateSTR(alert.id);
      onSTRGenerate?.(alert, result.narrative || result.str_narrative || '');
    } catch (e) {
      console.error('STR generation failed:', e);
    } finally {
      setGenerating(null);
    }
  };

  const filteredAlerts = filter === 'ALL' ? alerts :
    alerts.filter(a => a.status === filter);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold text-gray-900 dark:text-white">Alert Inbox</h2>
          <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded-full font-medium">
            {alerts.filter(a => a.status === 'OPEN').length} open
          </span>
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-400'}`}
               title={wsConnected ? 'Live updates on' : 'Connecting...'} />
        </div>
        <div className="flex gap-1">
          {(['ALL', 'OPEN', 'INVESTIGATING'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-2 py-1 text-xs rounded ${filter === f
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
              {f}
            </button>
          ))}
          <button onClick={fetchAlerts}
            className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded">
            ↻
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
            Loading alerts...
          </div>
        )}
        {!loading && filteredAlerts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400 text-sm gap-2">
            <span>No alerts found</span>
            <span className="text-xs">Run the demo seeder or inject a transaction</span>
          </div>
        )}
        {filteredAlerts.map((alert) => (
          <div key={alert.id}
            className="p-4 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-750">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                    RISK_BADGE_STYLES[alert.risk_level] || 'bg-gray-500 text-white'}`}>
                    {alert.risk_level}
                  </span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {alert.account_id}
                  </span>
                  <span className="text-xs text-gray-500">{alert.status}</span>
                </div>
                <div className="text-xs text-gray-500 mb-1">
                  Risk: {Math.round(alert.risk_score)}/100 · {alert.recommendation} ·{' '}
                  {alert.rule_flags?.join(', ')}
                </div>
                {alert.shap_top3?.[0] && (
                  <div className="text-xs text-gray-400 italic truncate">
                    "{alert.shap_top3[0]}"
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-1 flex-shrink-0">
                <button
                  onClick={() => onAccountSelect?.(alert.account_id)}
                  className="px-2 py-1 text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded hover:bg-indigo-100">
                  View Graph
                </button>
                <button
                  onClick={() => handleGenerateSTR(alert)}
                  disabled={generating === alert.id}
                  className="px-2 py-1 text-xs bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded hover:bg-green-100 disabled:opacity-50">
                  {generating === alert.id ? 'Generating...' : 'Gen STR'}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Step 4.5 — Build the Dashboard with metrics

Create/fix `frontend/src/components/Dashboard/Dashboard.tsx`:

```typescript
import { useEffect, useState } from 'react';
import { api } from '../../services/api';

export function Dashboard() {
  const [stats, setStats] = useState({ accounts: 0, transactions: 0, alerts: 0, open_alerts: 0 });
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const h = await api.getHealth();
        setHealth(h);
        if (h.graph_stats) setStats(h.graph_stats);
      } catch (e) {}
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const METRICS = [
    { label: 'Accounts in Graph', value: stats.accounts, color: 'indigo' },
    { label: 'Transactions', value: stats.transactions, color: 'blue' },
    { label: 'Total Alerts', value: stats.alerts, color: 'orange' },
    { label: 'Open Alerts', value: stats.open_alerts, color: 'red' },
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">UniGRAPH</h1>
          <p className="text-sm text-gray-500">AI-Powered Fund Flow Tracking · Union Bank of India</p>
        </div>
        <div className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-full ${
          health?.neo4j === 'connected'
            ? 'bg-green-50 text-green-700'
            : 'bg-red-50 text-red-700'}`}>
          <div className={`w-2 h-2 rounded-full ${health?.neo4j === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} />
          {health?.neo4j === 'connected' ? 'Graph DB Connected' : 'Graph DB Offline'}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {METRICS.map(({ label, value, color }) => (
          <div key={label} className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-2xl font-semibold text-gray-900 dark:text-white">
              {value.toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>

      {/* Key metrics table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-medium text-gray-900 dark:text-white">Performance vs Baseline</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 bg-gray-50 dark:bg-gray-750">
              <th className="px-4 py-2">Metric</th>
              <th className="px-4 py-2">Traditional AML</th>
              <th className="px-4 py-2">UniGRAPH</th>
              <th className="px-4 py-2">Improvement</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {[
              ['Investigation time', '4 hours/case', '18 minutes', '93% faster'],
              ['Alert latency', 'Hours (batch)', '<500ms', 'Real-time'],
              ['False positive rate', '70%+', '~30%', '57% reduction'],
              ['STR filing time', '2-3 days', '1 click', '99% faster'],
            ].map(([metric, old, neo, imp]) => (
              <tr key={metric}>
                <td className="px-4 py-2.5 text-gray-700 dark:text-gray-300 font-medium">{metric}</td>
                <td className="px-4 py-2.5 text-red-600">{old}</td>
                <td className="px-4 py-2.5 text-green-600 font-medium">{neo}</td>
                <td className="px-4 py-2.5 text-indigo-600 font-medium">{imp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

## Step 4.6 — Build the STR Report Studio

Create `frontend/src/components/ReportStudio/ReportStudio.tsx`:

A panel that displays a generated STR narrative, lets the compliance officer edit it,
and shows a "Submit to FIU-IND" button (which in demo mode shows a success toast).

---

# 🔧 PHASE 5: WIRE EVERYTHING TOGETHER IN App.tsx

Read the existing `frontend/src/App.tsx`. Ensure it renders all components in a
professional layout:

**Layout should be:**
- Left sidebar (200px): Navigation links (Dashboard, Alerts, Graph, Cases, Reports)
- Main content area: Shows the selected view
- When "View Graph" is clicked in AlertInbox → switches to Graph view with the account
  pre-loaded
- When "Gen STR" succeeds → shows STR narrative in a modal or the Reports tab

**Use React Router or simple state for navigation.** Don't over-engineer.

---

# 🔧 PHASE 6: CREATE THE DEMO INJECTION SCRIPT

Create `scripts/inject_fraud_demo.py` — a script that injects live transactions
via the API to simulate fraud happening in real-time during the demo:

```python
"""
Demo fraud injection script for live hackathon demo.
Injects 3 fraud scenarios via the backend API.

Usage: python scripts/inject_fraud_demo.py
"""
import requests
import time
import json

API_BASE = "http://localhost:8000"

def inject(txn: dict, label: str) -> dict:
    print(f"\n🚀 {label}")
    print(f"   {txn['from_account']} → {txn['to_account']}: ₹{txn['amount']:,.0f}")
    resp = requests.post(f"{API_BASE}/api/v1/transactions/ingest", json=txn)
    result = resp.json()
    risk = result.get('scoring', {}).get('risk_score', 0)
    level = result.get('scoring', {}).get('risk_level', 'UNKNOWN')
    print(f"   Risk Score: {risk}/100 [{level}]")
    print(f"   Violations: {result.get('scoring', {}).get('rule_violations', [])}")
    if result.get('alert_created'):
        print(f"   ⚠️  ALERT CREATED: {result.get('alert_id')}")
    return result

def scenario_rapid_layering():
    print("\n" + "="*60)
    print("SCENARIO 1: RAPID LAYERING (6 hops in 30 minutes)")
    print("="*60)
    accounts = [f"DEMO-ACC-L{i:02d}" for i in range(1, 8)]
    amounts = [750000, 748000, 745000, 743000, 740000, 738000]
    for i in range(6):
        inject({
            "from_account": accounts[i],
            "to_account": accounts[i+1],
            "amount": amounts[i],
            "channel": "IMPS",
            "velocity_1h": i + 1,
            "velocity_24h": i + 2,
            "description": f"Payment hop {i+1}/6",
            "device_id": "DEMO-DEV-LAYER-001"
        }, f"Hop {i+1}: ₹{amounts[i]:,.0f}")
        time.sleep(0.5)

def scenario_dormant_awakening():
    print("\n" + "="*60)
    print("SCENARIO 2: DORMANT ACCOUNT AWAKENING (212 days)")
    print("="*60)
    inject({
        "from_account": "DEMO-DORMANT-001",
        "to_account": "DEMO-RECV-001",
        "amount": 1500000,
        "channel": "NEFT",
        "is_dormant": True,
        "velocity_1h": 1,
        "velocity_24h": 1,
        "description": "First activity after 212 days",
        "device_id": "DEMO-DEV-NEW-001"
    }, "Dormant account sudden large debit")

def scenario_mule_network():
    print("\n" + "="*60)
    print("SCENARIO 3: MULE NETWORK (shared device across 5 accounts)")
    print("="*60)
    mule_accounts = [f"DEMO-MULE-{i:02d}" for i in range(1, 6)]
    for i in range(4):
        inject({
            "from_account": mule_accounts[i],
            "to_account": mule_accounts[i+1],
            "amount": 50000 * (i + 1),
            "channel": "UPI",
            "device_account_count": 5,
            "velocity_1h": 2,
            "velocity_24h": 4,
            "description": "UPI transfer",
            "device_id": "DEMO-MULE-DEVICE-001"
        }, f"Mule hop {i+1}")
        time.sleep(0.3)

if __name__ == "__main__":
    print("🔥 UniGRAPH Demo Fraud Injection")
    print("   This will inject 3 fraud scenarios via the API")
    print("   Watch the Graph Explorer and Alert Inbox in real-time!")

    # Check API is up
    try:
        health = requests.get(f"{API_BASE}/health", timeout=5).json()
        print(f"\n✅ Backend: {health.get('status', 'unknown')}")
        print(f"   Neo4j: {health.get('neo4j', 'unknown')}")
    except Exception as e:
        print(f"\n❌ Backend not reachable: {e}")
        print("   Start backend first: cd backend && uvicorn app.main:app --reload")
        exit(1)

    scenario_rapid_layering()
    time.sleep(1)
    scenario_dormant_awakening()
    time.sleep(1)
    scenario_mule_network()

    print("\n" + "="*60)
    print("✅ ALL FRAUD SCENARIOS INJECTED")
    print("   Check the Alert Inbox — you should have 3+ new alerts")
    print("   Open Graph Explorer to see the fraud networks")
    print("="*60)
```

---

# ✅ VERIFICATION GATES

Run these checks in order. Do NOT proceed to the next phase until the current one passes.

## Gate 1: Docker services healthy
```bash
docker compose -f docker/docker-compose.yml ps | grep -E "(neo4j|kafka|redis)"
# Expected: All show "healthy" or "running"

# Quick Neo4j test
docker exec -it $(docker ps -qf "name=neo4j") cypher-shell -u neo4j -p unigraph_dev "RETURN 1 as test" 2>/dev/null | grep "1 test"
```

## Gate 2: Demo data seeded
```bash
python scripts/demo_seeder.py
# Expected: Output shows "✅ Demo data seeded successfully!"
```

## Gate 3: Backend starts and serves
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
sleep 5
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "healthy", "neo4j": "connected", ...}
```

## Gate 4: Alerts are returned from API
```bash
curl -s http://localhost:8000/api/v1/alerts | python3 -m json.tool
# Expected: JSON array with 3 alerts (LAYER, DORMANT, MULE scenarios)
```

## Gate 5: Transaction ingestion works
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions/ingest \
  -H "Content-Type: application/json" \
  -d '{"from_account":"TEST-001","to_account":"TEST-002","amount":900000,"channel":"IMPS","velocity_1h":6}' \
  | python3 -m json.tool
# Expected: JSON with risk_score > 60, alert_created: true
```

## Gate 6: Account subgraph is returned
```bash
curl -s "http://localhost:8000/api/v1/accounts/ACC-LAYER-001/graph?hops=2" | python3 -m json.tool
# Expected: JSON with "nodes" array and "edges" array, both non-empty
```

## Gate 7: STR generation works
```bash
# Get an alert ID first
ALERT_ID=$(curl -s http://localhost:8000/api/v1/alerts | python3 -c "import sys,json; alerts=json.load(sys.stdin); print(alerts[0]['id'] if alerts else 'none')")
echo "Testing STR for alert: $ALERT_ID"

curl -s -X POST http://localhost:8000/api/v1/reports/str/generate \
  -H "Content-Type: application/json" \
  -d "{\"alert_id\": \"$ALERT_ID\"}" | python3 -m json.tool
# Expected: JSON with "narrative" field containing STR text
```

## Gate 8: Frontend loads
```bash
cd frontend
npm run dev &
sleep 5
curl -s http://localhost:5173 | grep -c "UniGRAPH\|root"
# Expected: 1 or more (HTML page loads)
```

## Gate 9: Full demo flow
```bash
python scripts/inject_fraud_demo.py
# Expected: "✅ ALL FRAUD SCENARIOS INJECTED" and 3 fraud scenarios shown
```

---

# 🚨 COMMON ISSUES AND FIXES

**Issue**: `ImportError: No module named 'neo4j'`
**Fix**: `pip install neo4j`

**Issue**: `ImportError: No module named 'pydantic_settings'`
**Fix**: `pip install pydantic-settings`

**Issue**: Neo4j connection refused
**Fix**: Check docker compose is running: `docker compose -f docker/docker-compose.yml up -d neo4j`
Wait 30 seconds, then retry. Neo4j takes time to start.

**Issue**: `ModuleNotFoundError` for any import in backend
**Fix**: Make sure you're running `uvicorn` from the `backend/` directory, OR set PYTHONPATH:
```bash
cd backend && PYTHONPATH=. uvicorn app.main:app --reload
```

**Issue**: Frontend can't connect to backend (CORS error)
**Fix**: Ensure `APP_CORS_ORIGINS=http://localhost:5173` in `.env` and backend is restarted.

**Issue**: Cytoscape renders empty
**Fix**: Make sure the `<div ref={cyRef}>` has explicit height set (`style={{ minHeight: '500px' }}`).
Also ensure `cytoscape` npm package is installed in `frontend/`.

**Issue**: Alerts endpoint returns empty array even after seeding
**Fix**: Check Neo4j constraints were created. Re-run `python scripts/demo_seeder.py`.

**Issue**: Groq LLM returns error
**Fix**: Add your Groq API key to `.env`. Get a free key at console.groq.com.
The system will fall back to mock response if no key is configured — the demo still works.

**Issue**: WebSocket connection fails
**Fix**: Ensure the WS endpoint is at `ws://localhost:8000/api/v1/ws/alerts`.
Check CORS allows the frontend origin. The `ConnectionManager` must be imported from
`ws.py` into `transactions.py` (not created separately — same instance).

---

# 🎯 FINAL DEMO CHECKLIST

Before the judges arrive, run through this:

1. `docker compose -f docker/docker-compose.yml up -d` → all services healthy
2. `python scripts/demo_seeder.py` → 3 fraud scenarios pre-seeded
3. `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
4. `cd frontend && npm run dev`
5. Open `http://localhost:5173` → dashboard shows graph stats
6. Open Alerts tab → 3 pre-seeded alerts visible
7. Click "View Graph" on Rapid Layering alert → 6-hop chain visible in graph explorer
8. Click "Gen STR" → LLM narrative appears within 5 seconds
9. Open second terminal, run: `python scripts/inject_fraud_demo.py`
10. Watch Alert Inbox update in real-time via WebSocket

**Demo narrative**: "A fraudster moved ₹43.5 lakh across 6 accounts in 25 minutes.
Traditional AML systems would have caught this in the next day's batch job — 18 hours
after the money was already layered. UniGRAPH detected it in 147 milliseconds and fired
an alert before the 6th hop completed."

---

# 📌 IMPLEMENTATION ORDER SUMMARY

Do these in order, exactly:

1. `.env` setup
2. Install dependencies (backend, ml, frontend)
3. Docker compose up
4. Fix `backend/app/config.py`
5. Fix `backend/app/services/neo4j_service.py`
6. Create `backend/app/services/llm_service.py`
7. Create `backend/app/services/fraud_scorer.py`
8. Fix `backend/app/main.py`
9. Fix `backend/app/routers/transactions.py` (ingest endpoint)
10. Fix `backend/app/routers/alerts.py`
11. Fix `backend/app/routers/reports.py` (STR generation)
12. Fix `backend/app/routers/ws.py` (WebSocket + ConnectionManager)
13. Create `scripts/demo_seeder.py`
14. Run demo seeder → verify Gate 2
15. Start backend → verify Gates 3-7
16. Fix `frontend/src/services/api.ts`
17. Build `frontend/src/components/GraphExplorer/GraphExplorer.tsx`
18. Build `frontend/src/components/AlertInbox/AlertInbox.tsx`
19. Build `frontend/src/components/Dashboard/Dashboard.tsx`
20. Wire everything in `frontend/src/App.tsx`
21. Start frontend → verify Gate 8
22. Create `scripts/inject_fraud_demo.py`
23. Run full demo flow → verify Gate 9
24. Practice the demo once end-to-end

**YOU ARE DONE WHEN GATE 9 PASSES.**

---

*UniGRAPH — "Every rupee has a trail. We follow it."*
*Team: Beyond Just Programming | PSBs Hackathon IDEA 2.0 | April 2026*
