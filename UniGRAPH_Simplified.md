# UniGRAPH: Simplified Fraud Detection Architecture

UniGRAPH is a real-time fraud detection system that combines **Graph Analytics**, **Rule-Based Logic**, and **Machine Learning** to identify complex financial crime patterns (like money laundering and mule networks).

---

## 1. High-Level Architecture
The system follows a linear data pipeline from transaction occurrence to fraud alert.

**Data Flow:**
`Core Banking System (CBS)` $\rightarrow$ `Kafka` $\rightarrow$ `Flink (Enrichment)` $\rightarrow$ `Neo4j/Cassandra` $\rightarrow$ `Drools (Rules)` $\rightarrow$ `GraphSAGE (ML)` $\rightarrow$ `Alert/Case Management`

---

## 2. Core Components

### A. Data Ingestion & Enrichment
*   **Ingestion**: Captures transactions from CBS via Change Data Capture (CDC/Debezium) and streams them into **Kafka**.
*   **Enrichment**: **Apache Flink** consumes raw transactions and adds context (KYC status, Geo-risk, Device reputation) from lookup tables in real-time.

### B. Graph Intelligence (The "Brain")
*   **Storage**: **Neo4j** stores the network of Accounts, Customers, and Devices.
*   **Relationships**: Tracks `SENT` (money flow), `OWNS` (customer-account), and `USED_DEVICE` (shared hardware).
*   **GDS (Graph Data Science)**: Runs algorithms to find "structural" fraud:
    *   **PageRank**: Identifies influential/central accounts.
    *   **Louvain**: Detects tight-knit fraud communities.
    *   **Betweenness**: Finds bridge accounts used for layering.

### C. Detection Layers
The system uses a "Defense in Depth" approach with two layers:

1.  **Rule-Based Layer (Drools)**: 
    *   **Purpose**: Catch known, deterministic patterns.
    *   **Examples**: "Rapid Layering" (5+ hops in 30 mins), "Dormant Awakening" (Sudden large txn after 6 months).
    *   **Strength**: Instant, explainable, and easy to update.

2.  **ML-Based Layer (GraphSAGE)**:
    *   **Purpose**: Catch unknown, evolving patterns using graph embeddings.
    *   **Mechanism**: Learns the "shape" of fraud. It doesn't just look at a transaction, but at the *neighborhood* of the account.
    *   **Strength**: Detects sophisticated anomalies that rules miss.

### D. Storage & Monitoring
*   **Cassandra**: Stores the time-series history of transactions for fast retrieval.
*   **Redis**: Tracks real-time velocity (e.g., "How many txns in the last hour?").
*   **Prometheus/Grafana**: Monitors system health and detection latency.

---

## 3. The Detection Pipeline (Step-by-Step)

1.  **Transaction Arrives**: A payment is made.
2.  **Enrich**: Flink adds user risk scores and device flags.
3.  **Graph Update**: The transaction is written as a `SENT` edge in Neo4j.
4.  **Rule Check**: Drools checks if this txn triggers any red-flag rules.
5.  **ML Score**: GraphSAGE generates a fraud probability based on the account's graph neighborhood.
6.  **Decision**: If (Rule = High) OR (ML Score > Threshold) $\rightarrow$ **Trigger Alert**.

---

## 4. Essential Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Messaging** | Kafka | Event streaming backbone |
| **Processing** | Flink | Real-time data enrichment |
| **Graph DB** | Neo4j | Network analysis & GDS |
| **TS DB** | Cassandra | High-volume transaction history |
| **Rules** | Drools | Deterministic fraud patterns |
| **ML** | PyTorch + PyG | GraphSAGE model for embeddings |
| **Cache** | Redis | Real-time velocity counters |
| **Orchestration**| Kubernetes | Scalable deployment |

---

## 5. Simplified Implementation Roadmap

### Phase 1: Foundation
*   Set up **Docker** with Kafka, Neo4j, and Cassandra.
*   Build the basic ingestion pipeline (Mock CBS $\rightarrow$ Kafka $\rightarrow$ Neo4j).

### Phase 2: Deterministic Detection
*   Implement **Neo4j Cypher** queries for basic fraud patterns.
*   Integrate **Drools** to automate these rules.

### Phase 3: Predictive Intelligence
*   Extract graph features using **Neo4j GDS**.
*   Train and deploy the **GraphSAGE** model for probabilistic scoring.
