# [cite_start]UniGraph Intelligent Fund Flow Tracking System MASTER DOCUMENT Idea Hackathon 2.0 PS3 [cite: 430]

[cite_start]**IDEA HACKATHON 2.0 PS3 PROBLEM STATEMENT 3** [cite: 432]

## [cite_start]UniGraph [cite: 433]
[cite_start]Intelligent Fund Flow Tracking System for Fraud Detection Anti-Money Laundering Graph Analytics Machine Learning FIU Compliance [cite: 434]

[cite_start]**MASTER PROJECT DOCUMENT Version 1.0 March 2026** [cite: 435]

[cite_start]*Ojas Rehan S Rehan P* [cite: 436]

---

## [cite_start]Table of Contents [cite: 439]

| Section | Page |
| :--- | :--- |
| **1. Executive Summary** | [cite_start]4 [cite: 440] |
| **2. Problem Statement** | [cite_start]5 [cite: 440] |
| 2.1 Why Existing Systems Fail | [cite_start]5 [cite: 440] |
| 2.2 The Core Structural Gap | [cite_start]5 [cite: 440] |
| 2.3 Regulatory Urgency (Why Indian Banks Need This Now) | [cite_start]5 [cite: 440] |
| **3. Solution Overview - UniGraph** | [cite_start]6 [cite: 440] |
| 3.1 Product Identity | [cite_start]6 [cite: 440] |
| 3.2 Four Pillars of the Solution | [cite_start]6 [cite: 440] |
| - End-to-End Visual Fund Tracing (Pillar 1) | [cite_start]6 [cite: 440] |
| - Real-Time ML-Driven Pattern Detection (Pillar 2) | [cite_start]6 [cite: 440] |
| - Explainable Evidence Packages (Pillar 3) | [cite_start]6 [cite: 440] |
| - Automated FIU-IND STR Generation (Pillar 4) | [cite_start]6 [cite: 440] |
| 3.3 Key Unique Selling Points (USPs) | [cite_start]6 [cite: 440] |
| **4. System Architecture** | [cite_start]8 [cite: 440] |
| 4.1 Five-Layer Architecture Overview | [cite_start]8 [cite: 440] |
| 4.2 End-to-End Data Flow - 11 Steps | [cite_start]8 [cite: 440] |
| **5. Layer-by-Layer Technical Deep Dive** | [cite_start]10 [cite: 440] |
| 5.1 L1 - Data Ingestion Layer | [cite_start]10 [cite: 440] |
| 5.2 L2 - Graph Storage Layer | [cite_start]10 [cite: 440] |
| 5.3 L3 - ML and AI Detection Layer | [cite_start]10 [cite: 440] |
| 5.4 L4 - Investigation and Visualisation Layer | [cite_start]11 [cite: 440] |
| 5.5 L5 - FIU Reporting Layer | [cite_start]11 [cite: 440] |
| **6. Fraud Typologies and Detection Methods** | [cite_start]12 [cite: 440] |
| 6.1 Rapid Layering | [cite_start]12 [cite: 440] |
| 6.2 Circular Transactions (Round-Tripping) | [cite_start]12 [cite: 440] |
| 6.3 Structuring (Smurfing) | [cite_start]12 [cite: 440] |
| 6.4 Dormant Account Activation | [cite_start]13 [cite: 440] |
| 6.5 Customer Profile Mismatch | [cite_start]13 [cite: 440] |
| 6.6 Additional Fraud Types Detected | [cite_start]14 [cite: 440] |
| **7. Data Schema - Financial Knowledge Graph** | [cite_start]15 [cite: 444] |
| 7.1 Node Definitions | [cite_start]15 [cite: 444] |
| 7.2 Edge Definitions | [cite_start]16 [cite: 444] |
| 7.3 Schema Requirements by Fraud Algorithm | [cite_start]16 [cite: 444] |
| **8. Graph Algorithms - Neo4j GDS Library** | [cite_start]18 [cite: 444] |
| **9. Complete Technology Stack with Justifications** | [cite_start]19 [cite: 444] |
| **10. Build Roadmap - 34-Week Delivery Plan** | [cite_start]21 [cite: 444] |
| 10.1 Recommended Team Composition | [cite_start]22 [cite: 444] |
| **11. Competitive Positioning and Innovation** | [cite_start]23 [cite: 444] |
| 11.1 UniGraph vs. Traditional AML Systems | [cite_start]23 [cite: 444] |
| 11.2 Supporting Research and References | [cite_start]23 [cite: 444] |
| **12. Glossary of Key Terms** | [cite_start]24 [cite: 444] |

---

## [cite_start]1. Executive Summary [cite: 448]

[cite_start]UniGraph is an intelligent Anti-Money Laundering (AML) and Financial Network Intelligence platform built to solve Problem Statement 3 of the Idea Hackathon 2.0. [cite: 449] [cite_start]The system constructs a real-time Financial Knowledge Graph from multi-channel transaction streams and KYC records, modelling every relationship between accounts, entities, branches, and channels as a live, queryable network. [cite: 450] 

[cite_start]Using a combination of graph analytics and a three-model machine learning ensemble, UniGraph detects five high-priority fraud typologies that are completely invisible to traditional relational database systems: rapid layering, round-tripping (circular transactions), structuring (smurfing), dormant account activation, and customer profile mismatch. [cite: 451] [cite_start]The platform gives compliance investigators full transaction traceability through an interactive visual graph explorer, automated evidence compilation, and an AI-assisted STR narrative generator for direct FIU-IND submission. [cite: 452]

[cite_start]**Why this approach is necessary** [cite: 453]
* [cite_start]Real-time AI analytics cuts fraud processing time by 80% and reduces manual investigator workload by over 50%. [cite: 454]
* [cite_start]Legacy rule-based systems are progressively losing effectiveness against modern, coordinated financial crime because they look at individual transactions, not the network relationships between them. [cite: 455] [cite_start]UniGraph fixes this structural gap. [cite: 456]

**Key Metrics**
* [cite_start]**< 500ms** Alert Latency [cite: 457]
* [cite_start]**100K TPS** Sustained Throughput [cite: 458]
* [cite_start]**> 92%** Detection Recall [cite: 459]
* [cite_start]**< 5%** False Positive Rate [cite: 460]

---

## [cite_start]2. Problem Statement [cite: 463]

[cite_start]**Official PS3 - Idea Hackathon 2.0** [cite: 464]
[cite_start]Develop an intelligent Fund Flow Tracking system that maps and visualises the end-to-end movement of funds within the bank across accounts, products, branches, and channels. [cite: 465] [cite_start]The system should use graph analytics and machine learning to identify suspicious fund flow patterns such as rapid layering through multiple accounts, circular transactions (round-tripping), structuring below reporting thresholds, sudden activation of dormant accounts for high-value transfers, and mismatches between declared customer profiles and actual fund movement behaviour. [cite: 466] [cite_start]The solution should enable investigators to trace the complete journey of funds and generate evidence packages for reporting to the Financial Intelligence Unit (FIU). [cite: 467]

### [cite_start]2.1 Why Existing Systems Fail [cite: 468]
[cite_start]Traditional Core Banking Systems (CBS) store transaction data in flat, relational SQL tables. [cite: 469] [cite_start]This structure is efficient for recording individual events but fundamentally incapable of answering the questions fraud investigators actually need. [cite: 470] [cite_start]Consider the query: 'Show me every account that received money from Account X in the last 48 hours, and then forwarded it somewhere within 30 minutes.' [cite: 471] [cite_start]Answering this in SQL requires JOINs across dozens of tables [cite: 472] it can take minutes or hours. [cite_start]By then, [cite: 474] [cite_start]the funds have moved. [cite: 473] 

[cite_start]The KPMG Machine Learning in Financial Crime Compliance report (2025) confirms this directly: legacy systems relying on static rules are progressively losing effectiveness against modern fraud. [cite: 475] [cite_start]The IBA Draft Framework on Money Mule Accounts (April 2025) similarly notes that 'the rapid adaptation of techniques by criminals and limitations in existing monitoring systems necessitate a more robust and dynamic framework' leveraging AI and ML. [cite: 476]

### [cite_start]2.2 The Core Structural Gap [cite: 477]
[cite_start]Fraud is a relationship problem, but existing systems only look at individual events. [cite: 478] A single ₹49,000 cash deposit is entirely normal. [cite_start]Forty-seven such deposits made across different branches on the same day by accounts all connected to the same beneficial owner - that is a structuring ring. [cite: 479] No SQL query will surface this pattern in real time. [cite_start]Only a graph database, with native multi-hop traversal, can. [cite: 480]

### [cite_start]2.3 Regulatory Urgency (Why Indian Banks Need This Now) [cite: 481]

| Regulatory Body / Framework | Requirement Relevant to This System |
| :--- | :--- |
| **FATF Recommendations** | [cite_start]Member countries must implement transaction monitoring and file STRs within 7 days of suspicion. [cite: 482] |
| **FIU-IND (India)** | Banks must file STRs electronically in standardised XML format. [cite_start]Non-compliance results in monetary penalties and licence risk. [cite: 482] |
| **RBI AML Guidelines** | [cite_start]Mandates real-time transaction monitoring, customer risk profiling, and cross-channel activity tracking. [cite: 482] |
| **IBA Draft Framework (April 2025)** | [cite_start]Explicitly calls for AI/ML-driven dynamic frameworks to detect money mule rings acknowledging that static rule systems are insufficient. [cite: 482] |
| **KPMG FCC Report (2025)** | [cite_start]Validates the transition from isolated transaction monitoring to behaviour-based network monitoring using ML. [cite: 482] |

---

## [cite_start]3. Solution Overview - UniGraph [cite: 485]

[cite_start]UniGraph re-architects how a bank thinks about its transaction data. [cite: 486] [cite_start]Instead of rows in a table, every account becomes a node, and every financial transaction becomes a directed, time-stamped, weighted edge in a live graph. [cite: 487] [cite_start]This transformation means the system can answer relationship questions instantly questions that are impossible for traditional databases to answer in real time. [cite: 488]

### [cite_start]3.1 Product Identity [cite: 489]

| Attribute | Details |
| :--- | :--- |
| **Product Name** | [cite_start]UniGraph [cite: 490] |
| **Tagline** | See the network. [cite_start]Stop the crime. [cite: 490] |
| **Category** | [cite_start]AML and Financial Crime Intelligence Platform [cite: 490] |
| **Target Users** | [cite_start]Bank Compliance Officers, AML Investigators, Risk Managers, FIU Liaison Officers [cite: 490] |
| **Deployment Model** | [cite_start]On-premise or Private Cloud - required for RBI data-localisation compliance. [cite: 490] |

### [cite_start]3.2 Four Pillars of the Solution [cite: 491]

* [cite_start]**Pillar 1 - End-to-End Visual Fund Tracing:** [cite: 492] [cite_start]Neo4j maps the entire multi-hop journey of funds in milliseconds. [cite: 493] [cite_start]An investigator clicks on any account and immediately sees every upstream source and downstream destination across all channels - UPI, NEFT, RTGS, IMPS, cards in a single visual graph. [cite: 494] [cite_start]This turns a 300-row spreadsheet into a glowing network map that makes the crime immediately visible. [cite: 495]
* [cite_start]**Pillar 2 - Real-Time ML-Driven Pattern Detection:** [cite: 496] [cite_start]A three-model ensemble runs continuously on every transaction: a Drools rule engine for hard regulatory rules, a GraphSAGE Graph Neural Network for structural pattern recognition, and an Isolation Forest for behavioural anomaly detection. [cite: 497] These three models combine into a unified 0-100 risk score. [cite_start]Scores above 80 trigger an investigator alert within 500 milliseconds. [cite: 498]
* [cite_start]**Pillar 3 - Explainable Evidence Packages:** [cite: 499] Regulators reject black-box AI scores. [cite_start]Every alert comes with a fully auditable evidence package: the specific graph path that triggered the alert, all transaction IDs and timestamps, the risk score breakdown by model, and a KYC mismatch comparison. [cite: 500] [cite_start]Every piece of evidence is human-readable and court-presentable. [cite: 501]
* [cite_start]**Pillar 4 - Automated FIU-IND STR Generation:** [cite: 502] [cite_start]A locally-hosted LLM (Qwen 3.5 9B via Ollama, running entirely on-premise for zero data leakage) auto-drafts the investigation narrative. [cite: 503] [cite_start]The system formats the complete STR into the exact XML schema required by FIU-IND for one-click submission, reducing a 2-4 hour manual process to a 5-minute review-and-approve workflow. [cite: 504]

### [cite_start]3.3 Key Unique Selling Points (USPs) [cite: 505]

* [cite_start]**AI-Powered Investigation Narrative Generator:** Structured suspicious activity summary, chronological timeline explanation, risk reasoning paragraph, and FIU-ready narrative - all auto-generated, massively reducing investigator workload. [cite: 506]
* [cite_start]**Graph-Native Architecture:** Built on Neo4j with the GDS library of 65+ algorithms. [cite: 509] [cite_start]Multi-hop traversal that takes hours in SQL runs in milliseconds. [cite: 510]
* [cite_start]**On-Premise LLM with Zero Data Leakage:** Sensitive financial data never leaves the bank. [cite: 511] [cite_start]Ollama hosts Qwen 3.5 9B locally, satisfying the strictest data sovereignty and RBI compliance requirements. [cite: 512]
* [cite_start]**Binary ML Classification with Explainability:** XGBoost outputs a definitive Yes/No fraud decision backed by SHAP feature importance values, making every automated decision auditable by a human reviewer. [cite: 513]
* [cite_start]**Autonomous Investigation Agent:** Proactively expands the investigation graph, cross-references related entities, and pre-populates case notes before a human opens the alert. [cite: 514]

---

## [cite_start]4. System Architecture [cite: 517]

[cite_start]UniGraph uses a five-layer, event-driven microservices architecture deployed on Kubernetes. [cite: 518] [cite_start]Each layer is independently scalable - if alert volume spikes, only the ML detection layer needs to scale out, without touching the ingestion or storage layers. [cite: 519] [cite_start]Data flows in a single direction: from source systems through ingestion, graph storage, ML detection, investigation, and finally regulatory reporting. [cite: 520] 

[cite_start]**Architecture Philosophy:** [cite: 521] Event-driven + Graph-native + ML ensemble. [cite_start]This trio enables bank-scale transaction volumes (100,000+ TPS), sub-500ms fraud detection, and court-ready evidence generation all without touching production databases or creating a single point of failure. [cite: 522, 523]

### [cite_start]4.1 Five-Layer Architecture Overview [cite: 524]

| Layer | Name | Core Components | Primary Purpose |
| :--- | :--- | :--- | :--- |
| **L1** | Data Ingestion | Debezium CDC, Apache Kafka, Apache Flink, Schema Registry | [cite_start]Capture every transaction in real-time and enrich it before downstream processing. [cite: 525] |
| **L2** | Graph Storage | Neo4j Graph DB, Apache Cassandra, Redis Cache | [cite_start]Store accounts as nodes and transactions as edges for instant multi-hop traversal. [cite: 525] |
| **L3** | ML Detection | Drools Rules, GraphSAGE GNN, Isolation Forest, XGBoost Ensemble | [cite_start]Scan the transaction graph continuously for all five fraud typologies. [cite: 525] |
| **L4** | Investigation UI | React.js, Cytoscape.js, Node.js WebSockets, Case Management | [cite_start]Interactive visual interface for alert triage, case management, and graph exploration. [cite: 525] |
| **L5** | FIU Reporting | Ollama + Qwen 3.5 9B, STR Generator, FIU-IND API, Audit Logger | [cite_start]Auto-draft and submit Suspicious Transaction Reports with complete evidence packages. [cite: 525] |

### [cite_start]4.2 End-to-End Data Flow - 11 Steps [cite: 526]

[cite_start]Every transaction that enters the bank goes through the following journey. [cite: 527] [cite_start]Understanding this flow end-to-end is critical for both building the system and explaining it to judges. [cite: 528]

* **Step 01 | [cite_start]Transaction Initiated $(t=0ms)$:** [cite: 529] [cite_start]A customer initiates a transfer via mobile app, branch counter, or API. [cite: 530] [cite_start]The Core Banking System records it in Oracle or Temenos and emits a database commit to the transaction log. [cite: 531]
* **Step 02 | [cite_start]CDC Capture $(t=10ms)$:** [cite: 532] [cite_start]Debezium detects the DB commit via the Write-Ahead Log (WAL) and converts it into an Avro-schema event. [cite: 533] [cite_start]This is published to the Kafka topic 'transactions.raw', partitioned by account_id to preserve chronological ordering. [cite: 534]
* **Step 03 | [cite_start]Kafka Buffering and Filtering:** [cite: 535] Apache Kafka acts as a high-speed shock absorber. [cite_start]A FastAPI microservice consumes the stream, drops low-risk retail noise, and aggregates data before downstream processing - preventing system overload during peak hours. [cite: 538]
* **Step 04 | [cite_start]Flink Stream Enrichment $(t=30ms)$:** [cite: 540] [cite_start]Apache Flink joins each event with the Customer Profile store (Redis) to add the KYC risk score, geographic risk data (FATF country classification), and device fingerprint. [cite: 541] [cite_start]The enriched event goes to 'transactions.enriched'. [cite: 542]
* **Step 05 | [cite_start]Graph Write to Neo4j $(t=80ms)$:** [cite: 543] [cite_start]A graph writer service creates or updates Account nodes and a directed TRANSACTED_WITH edge in Neo4j with all relevant properties. [cite: 544] [cite_start]Simultaneously the time-series record is written to Cassandra. [cite: 545]
* **Step 06 | [cite_start]Rule Engine Evaluation $(t=100ms)$:** [cite: 546] [cite_start]The Drools Business Rule Engine evaluates all active AML rules against the enriched transaction. [cite: 547] [cite_start]Triggered rules generate Rule Violation events on the 'alerts.rules' Kafka topic. [cite: 548]
* **Step 07 | [cite_start]Graph Feature Extraction $(t=150ms)$:** [cite: 549] [cite_start]An async job pulls the 2-hop neighbourhood subgraph from Neo4j and computes structural features: degree centrality, betweenness centrality, clustering coefficient, Louvain community ID, and PageRank score. [cite: 550]
* **Step 08 | [cite_start]ML Inference $(t=350ms)$:** [cite: 551] [cite_start]The GraphSAGE GNN receives the subgraph and produces a fraud probability. [cite: 552] The Isolation Forest receives the 30-day behavioural feature vector and produces an anomaly score. [cite_start]Both feed the XGBoost ensemble scorer. [cite: 553]
* **Step 09 | [cite_start]Alert Generation $(t<500ms)$:** [cite: 555] Score >= 80 triggers an investigator alert via WebSocket. Score 60-79 goes to watchlist. [cite_start]Below 60 is logged only. [cite: 556]
* **Step 10 | [cite_start]Investigator Review:** [cite: 558] [cite_start]The investigator views the transaction network in Cytoscape.js, expands nodes, applies filters, and creates a case with attached evidence if suspicion is confirmed. [cite: 559]
* **Step 11 | [cite_start]STR Generation and FIU Submission:** [cite: 560] [cite_start]The local Qwen 3.5 9B LLM auto-drafts the investigation narrative. [cite: 561] [cite_start]The system packages this with transaction IDs, graph export, and stats into FIU-IND XML format and submits via the FIU API. [cite: 562]

---

## [cite_start]5. Layer-by-Layer Technical Deep Dive [cite: 565]

### [cite_start]5.1 L1 - Data Ingestion Layer [cite: 566]
[cite_start]Banks simultaneously operate a Core Banking System, a card processor, SWIFT/NEFT/RTGS gateways, and UPI/mobile platforms - each speaking a different data format. [cite: 567] [cite_start]The ingestion layer unifies all of these into a single ordered, enriched event stream without touching production databases. [cite: 568]

* **Debezium CDC** monitors the database Write-Ahead Log directly. [cite_start]Every INSERT or UPDATE in the CBS is captured as a structured event within milliseconds, with zero impact on the source database no polling, no ETL delays. [cite: 569]
* **Apache Kafka** is the central event bus. [cite_start]All transaction events flow through Kafka topics partitioned by account_id, ensuring chronological ordering per account. [cite: 570] [cite_start]Messages are retained for 7 days, enabling historical replay when a new fraud pattern is discovered after the fact. [cite: 571]
* [cite_start]**Apache Flink** provides true streaming event-at-a-time processing with stateful rolling-window aggregations for velocity calculations. [cite: 572] [cite_start]Unlike Spark Streaming (micro-batch, latency of seconds), Flink achieves sub-second enrichment per event. [cite: 573]
* [cite_start]**Confluent Schema Registry** enforces Avro schema governance across all producers and consumers, ensuring backward compatibility as transaction formats evolve. [cite: 574]

### [cite_start]5.2 L2 - Graph Storage Layer [cite: 576]
This is the architectural core of UniGraph. [cite_start]In Neo4j, every entity is a node stored with direct physical pointers to its relationships. [cite: 577] [cite_start]When you traverse a relationship (a transaction edge), Neo4j follows a pointer - it does not scan a table. [cite: 578] [cite_start]This makes each hop $O(1)$ regardless of total database size. [cite: 579] [cite_start]Finding all accounts 5 hops from a suspect is milliseconds, not minutes. [cite: 580]

* **Neo4j Graph DB** stores the complete Financial Knowledge Graph. [cite_start]Accounts, customers, branches, and devices are nodes. [cite: 581] [cite_start]Transactions, ownership, co-signatories, and device access are edges with full property sets. [cite: 582] [cite_start]The GDS (Graph Data Science) library projects subgraphs into in-memory for algorithm execution, completely isolating analytical workloads from live transactional reads. [cite: 583]
* [cite_start]**Apache Cassandra** stores the full time-series transaction history, optimised with partition key = account_id and clustering key = timestamp, giving $O(1)$ reads for any account's transaction window. [cite: 584]
* [cite_start]**Redis Cache** stores hot subgraphs of frequently investigated accounts for sub-millisecond reads, making the investigator UI noticeably faster during active investigations. [cite: 585]

### [cite_start]5.3 L3 - ML and AI Detection Layer [cite: 586]
* [cite_start]**Model 1: Drools Rule Engine - Hard AML Rules** [cite: 587] [cite_start]Drools evaluates deterministic, human-readable rules at up to 1 million events per second with sub-millisecond latency. [cite: 588] [cite_start]Every rule is fully auditable a compliance officer can read it, a regulator can review it. [cite: 589] Example rules include: any single transaction above Rs. [cite_start]10 Lakh triggers a Currency Transaction Report; [cite: 590] [cite_start]more than 10 transactions from the same account in 15 minutes triggers a velocity alert; [cite: 591] [cite_start]any transaction to a FATF-blacklisted jurisdiction is auto-escalated. [cite: 592]
* [cite_start]**Model 2: GraphSAGE Graph Neural Network** [cite: 593] [cite_start]GraphSAGE (Graph Sample and Aggregate, implemented in PyTorch Geometric) learns to classify accounts by aggregating feature information from their 2-hop neighbourhood. [cite: 594] [cite_start]Node features include transaction velocity, amount percentiles, account age, KYC risk score, and Louvain community membership. [cite: 595] [cite_start]The model captures structural patterns invisible to any rule - for example, detecting that an account connected to three accounts sharing a beneficial owner with a known fraud ring has a structurally anomalous position in the graph. [cite: 596, 599]
* [cite_start]**Model 3: Isolation Forest — Behavioural Anomaly Detection** [cite: 600] [cite_start]Isolation Forest identifies anomalies by how easily they can be isolated in a random partitioning of the feature space. [cite: 600] [cite_start]Anomalous accounts (like a dormant account that suddenly becomes active) are isolated in very few splits. [cite: 601] [cite_start]It requires no labelled training data, making it ideal for novel patterns the GNN has never seen. [cite: 602] [cite_start]The feature vector per account includes 30-day transaction count, average amount, standard deviation, unique counterparty count, channel distribution, and time-of-day pattern. [cite: 603]
* [cite_start]**Ensemble Scorer — Combining All Three Models** [cite: 604] [cite_start]Final Risk Score = (0.3 x Rule Score) + (0.5 x GNN Score) + (0.2 x Isolation Score). [cite: 604] [cite_start]Weights are calibrated via Bayesian optimisation on the validation set. [cite: 605] [cite_start]Any rule engine trigger automatically raises the minimum score to 70. Scores at or above 80 generate an alert; [cite: 606] [cite_start]60-79 go to watchlist; below 60 are logged only. [cite: 607] [cite_start]All model versions are tracked in MLflow with full rollback capability. [cite: 608]

### [cite_start]5.4 L4 — Investigation and Visualisation Layer [cite: 609]
[cite_start]The design philosophy here is simple: investigators should be able to see the crime, not read about it. [cite: 609] [cite_start]A visual graph of money moving through a network communicates in seconds what would take hours of reading spreadsheet rows. [cite: 610]
* [cite_start]The React.js dashboard receives real-time alert updates via WebSocket — no page refresh required. [cite: 611] [cite_start]When an alert fires, it appears on the investigator's screen within 50 milliseconds. [cite: 612]
* [cite_start]Cytoscape.js renders the transaction network as an interactive graph. [cite: 613] [cite_start]Nodes are sized by transaction volume and coloured by risk score. [cite: 614] [cite_start]Investigators can expand any node to see its full history, click any edge to see full transaction details, and filter the view by time window, amount range, or channel type. [cite: 615]
* [cite_start]Case Management provides a complete workflow: Open, Under Review, Escalated, Closed — with investigator notes, evidence attachments, status history, and supervisor review. [cite: 616] [cite_start]Every action is timestamped and attributed for audit compliance. [cite: 617]

### [cite_start]5.5 L5 — FIU Reporting Layer [cite: 618]
[cite_start]This layer converts a confirmed investigation case into a regulatory submission package, reducing a 2-4 hour manual STR writing process to a 5-minute review-and-approve workflow. [cite: 618]
* Ollama hosts Qwen 3.5 9B entirely on-premise. [cite_start]The LLM reads the confirmed graph structure and auto-drafts the investigation narrative following FATF narrative guidelines, including a suspicious activity summary, chronological transaction timeline, typology labels, and recommended action. [cite: 619]
* [cite_start]The STR Generator populates FIU-IND XML format, FATF, and FinCEN SAR templates from structured case data. [cite: 620] [cite_start]Investigators review and approve — they never write from scratch. [cite: 621]
* [cite_start]The Evidence Package Builder produces a one-click export: full transaction trail PDF, graph screenshot, statistical summary, KYC comparison table, and risk score breakdown by model. [cite: 622]
* [cite_start]The Immutable Audit Logger records every system action with a cryptographic hash chain — alert generation, investigator login, model inference, STR submission — creating a tamper-proof compliance record. [cite: 623]

---

## [cite_start]6. Fraud Typologies and Detection Methods [cite: 625]

[cite_start]The five fraud patterns targeted by UniGraph are the exact typologies specified in Problem Statement 3, and they represent the most prevalent forms of bank-level financial crime in India today. [cite: 625] [cite_start]Importantly, each pattern requires a different combination of graph algorithm and ML model to detect reliably — no single technique covers all five. [cite: 626]

### [cite_start]6.1 Rapid Layering [cite: 627]
[cite_start]**SEVERITY LEVEL: CRITICAL** [cite: 627]
[cite_start]Moving funds through multiple accounts and jurisdictions in a quick sequence to break the paper trail. [cite: 627] [cite_start]The faster the money moves through more hands, the harder it becomes to legally trace back to its illegal source. [cite: 628]
* **Real-World Indian Example:** Rs. 20 Lakh is split into four Rs. [cite_start]5 Lakh chunks and instantly wired to crypto exchanges via four different savings accounts, all within 12 minutes of the original transfer. [cite: 629, 630]
* [cite_start]**Graph Detection Method:** Breadth-First Search traversal with time-windowed edge filtering. [cite: 631] [cite_start]If funds traverse more than 3 hops in under 30 minutes, the path is flagged. [cite: 632] [cite_start]The Global_Transaction_ID property on each edge confirms that the money leaving Account B is causally the same money that arrived from Account A. [cite: 633]
* [cite_start]**ML Detection Method:** Temporal Graph Neural Networks learn the typical velocity of legitimate fund movement versus the unnaturally fast pace of layering. [cite: 633] [cite_start]Key features: hop count, time delta between hops, and jurisdictional diversity of accounts in the path. [cite: 634]

### [cite_start]6.2 Circular Transactions (Round-Tripping) [cite: 635]
[cite_start]**SEVERITY LEVEL: HIGH** [cite: 635]
[cite_start]Money is transferred through a chain of accounts and returns to the originating account, creating an illusion of business volume or legitimising illicit funds as revenue. [cite: 635] [cite_start]Often used by companies with the same Ultimate Beneficial Owner. [cite: 636]
* **Real-World Indian Example:** Company A pays Company B Rs. 50 Lakhs, B pays Company C Rs. 48 Lakhs, and C 'invests' Rs. [cite_start]46 Lakhs back into Company A — all three sharing the same UBO. [cite: 637, 638]
* [cite_start]**Graph Detection Method:** Johnson's Algorithm or Tarjan's Strongly Connected Components algorithm detects directed cycles in the transaction graph. [cite: 639] Any cycle of 2-10 hops where the net amount preserved is above Rs. [cite_start]1 Lakh triggers an alert. [cite: 640]
* [cite_start]**ML Detection Method:** Louvain Community Detection identifies clusters of accounts that transact predominantly with each other. [cite: 641] [cite_start]ML models then flag clusters with high internal transaction density but zero external economic purpose — the defining signature of a round-tripping ring. [cite: 642]

### [cite_start]6.3 Structuring (Smurfing) [cite: 643]
[cite_start]**SEVERITY LEVEL: HIGH** [cite: 643]
[cite_start]Deliberately splitting a large sum into multiple smaller transactions to stay below regulatory reporting thresholds. [cite: 645] In India, the PAN card reporting threshold is Rs. [cite_start]50,000 for cash — structuring keeps each transaction just below this level. [cite: 646]
* **Real-World Indian Example:** Rs. [cite_start]49,000 in cash deposited across 10 different bank branches on the same day, all amounts destined for the same beneficiary account. [cite: 647]
* [cite_start]**Graph Detection Method:** Detection of scatter patterns (one source fanning to many low-value destinations) and gather patterns (many small inputs converging into one account). [cite: 648] [cite_start]Sliding window aggregation over 24-hour periods identifies when the sum of sub-threshold transactions from connected accounts exceeds the reporting limit. [cite: 649]
* [cite_start]**ML Detection Method:** Unsupervised clustering groups transactions by time proximity and geographic origin. [cite: 650] [cite_start]Isolation Forest flags accounts where the daily transaction count is more than 3 standard deviations above the 90-day historical baseline. [cite: 651]

### [cite_start]6.4 Dormant Account Activation [cite: 652]
[cite_start]**SEVERITY LEVEL: MEDIUM** [cite: 652]
[cite_start]A long-inactive account suddenly receives and immediately transfers a high-value sum. [cite: 652] [cite_start]This indicates account takeover, a money mule account being activated for the first time, or a shell entity used for a one-time laundering event. [cite: 653]
* **Real-World Indian Example:** A savings account untouched since 2021 suddenly receives a Rs. [cite_start]1.5 Crore RTGS transfer and wires the full amount offshore within 6 hours. [cite: 654, 655]
* [cite_start]**Graph Detection Method:** Monitoring of Degree Centrality changes over time. [cite: 656] [cite_start]A node with zero edges for over 180 days that suddenly becomes a high-traffic hub is flagged as a structural anomaly. [cite: 657] [cite_start]The degree change rate is tracked as a time-series property on the Account node. [cite: 658]
* [cite_start]**ML Detection Method:** Isolation Forest compares the current activity spike against a multi-year historical baseline of zero activity. [cite: 659] [cite_start]The dormancy gap duration and spike magnitude are the most predictive features. [cite: 660]

### [cite_start]6.5 Customer Profile Mismatch [cite: 661]
[cite_start]**SEVERITY LEVEL: HIGH** [cite: 661]
[cite_start]The actual fund movement in terms of volume, frequency, counterparty geography, and channel directly contradicts the customer's declared KYC data — occupation, income, or business type. [cite: 661] [cite_start]This is simultaneously a fraud signal and a KYC compliance failure. [cite: 662]
* **Real-World Indian Example:** A 19-year-old student with zero declared income receiving 50 business payments of Rs. [cite_start]10,000 each per day from corporate accounts across three states. [cite: 663, 664]
* [cite_start]**Graph Detection Method:** Jaccard and Cosine Similarity algorithms compare an account's transaction neighbourhood against peer-group accounts sharing the same declared customer segment. [cite: 665] [cite_start]A student account connected to corporate payment hubs scores near zero similarity to its declared peer group. [cite: 666]
* [cite_start]**ML Detection Method:** Supervised GNN trained on Entity Resolution data. [cite: 668] [cite_start]The model flags accounts whose structural embeddings are geometrically far from the centroid of their declared segment cluster — a measurable, quantifiable deviance from expected behaviour. [cite: 669]

### [cite_start]6.6 Additional Fraud Types Detected [cite: 670]
* [cite_start]**Money Mule Networks:** Innocent individuals tricked into receiving and forwarding stolen funds. [cite: 671] [cite_start]The Weakly Connected Components (WCC) algorithm isolates rings of accounts with a star topology — one controller node connected to many mule accounts, none of which have any economic relationship outside the ring. [cite: 672]
* [cite_start]**Funneling:** Drip-feeding dirty money from hundreds of small disconnected accounts into one central account. [cite: 673] Example: 200 retail accounts each transferring Rs. [cite_start]5,000 into a local bakery's current account over a weekend. [cite: 674] [cite_start]Detection: Fan-in subgraph pattern matching identifies a bipartite structure with a single high degree sink node receiving from many low-degree source nodes. [cite: 675]
* [cite_start]**Trade-Based Money Laundering (TBML):** Using fake or inflated trade invoices to move illicit money across borders. [cite: 676] [cite_start]Detection: Cross-referencing payment amounts against trade reference data, and flagging accounts connected to high-risk trade corridors with over-invoiced payment patterns. [cite: 677] [cite_start]The local LLM also parses transaction reference text to detect fictitious invoice descriptions. [cite: 678]

---

## [cite_start]7. Data Schema — Financial Knowledge Graph [cite: 680]

[cite_start]The financial knowledge graph uses a property graph model. [cite: 680] [cite_start]Nodes represent entities (the who and where), and edges represent relationships (the how, when, and how much). [cite: 681] [cite_start]Every property listed below serves a direct purpose in at least one fraud detection algorithm — nothing is stored just for the sake of completeness. [cite: 682]

### [cite_start]7.1 Node Definitions [cite: 683]

[cite_start]**Account Node — Core Graph Entity** [cite: 683]

| Property | Data Type | Fraud Detection Purpose |
| :--- | :--- | :--- |
| **AccountID** | String (UUID) | Primary key. [cite_start]Unique node identifier in Neo4j. [cite: 683, 684] |
| **Type** | Enum (Savings/Current/NRE/FCNR) | [cite_start]Used in profile mismatch detection — account type vs. observed transaction patterns. [cite: 684, 685] |
| **OpenDate** | DateTime | [cite_start]Calculates account age — new accounts doing high-value transfers is a priority rule. [cite: 685, 686] |
| **Balance** | Decimal (INR) | [cite_start]Baseline for anomaly scoring against incoming transfer amounts. [cite: 686, 687] |
| **RiskScore** | Float (0 to 100) | Continuously updated composite score. [cite_start]Drives alert queue prioritisation. [cite: 687, 688] |
| **Status** | Enum (Active/Dormant/Frozen) | [cite_start]Dormant status + sudden activity = immediate dormant activation alert. [cite: 688, 689] |
| **LastActivityDate** | DateTime | [cite_start]Days-since-activity is the top feature in dormant account Isolation Forest model. [cite: 689] |
| **CommunityID** | Integer | Assigned by Louvain algorithm. [cite_start]Identifies which potential fraud ring this account belongs to. [cite: 689, 690] |
| **PageRankScore** | Float | Computed by Neo4j GDS. [cite_start]High scores indicate potential mule coordinator accounts. [cite: 690, 691] |

[cite_start]**Customer / Entity Node** [cite: 691]

| Property | Data Type | Fraud Detection Purpose |
| :--- | :--- | :--- |
| **CustomerID** | String (UUID) | [cite_start]Links customer KYC identity to all associated accounts. [cite: 691, 692] |
| **KYC_Level** | Enum (Basic/Full/Enhanced) | [cite_start]Enhanced-risk customers require stricter monitoring rules. [cite: 692, 693] |
| **DeclaredIncome** | Decimal (Annual, INR) | [cite_start]Core input for profile mismatch detection — compared against actual fund flow volumes. [cite: 693, 694] |
| **Occupation** | String | [cite_start]Peer group classification for Jaccard similarity comparisons. [cite: 694] |
| **Nationality** | String (ISO country) | [cite_start]FATF high-risk country flag and cross-border transfer risk scoring. [cite: 694, 697] |
| **UBO_ID** | String (FK) | [cite_start]Ultimate Beneficial Owner linkage — exposes shared-UBO round-tripping rings. [cite: 697] |

### [cite_start]7.2 Edge Definitions [cite: 698]

[cite_start]**TRANSACTED_WITH Edge (Account to Account) — The Core Fraud Signal** [cite: 698]

| Property | Data Type | Fraud Detection Purpose |
| :--- | :--- | :--- |
| **Amount** | Decimal (INR) | [cite_start]Primary feature for threshold rules, structuring detection, and weighted graph analytics. [cite: 698, 699] |
| **Timestamp** | DateTime (UTC) | [cite_start]Enables temporal traversal and time-ordered cycle detection — money must flow forward in time. [cite: 699, 700] |
| **TransactionType** | Enum (NEFT/RTGS/IMPS/UPI/SWIFT/Card) | Channel-specific risk profiles. [cite_start]SWIFT automatically triggers enhanced screening. [cite: 700, 701] |
| **Global_Transaction_ID** | String (UUID) | [cite_start]Proves that money leaving Account B is causally the same money that arrived from Account A — essential for multi-hop layering tracing. [cite: 701, 702] |
| **ReferenceText** | String | [cite_start]Parsed by on-premise LLM to detect fictitious invoice descriptions in Trade-Based ML. [cite: 702, 703] |
| **WeightedVolume_24h** | Decimal (INR) | [cite_start]Pre-aggregated sum of all transactions between these two accounts in the last 24 hours — feeds the structuring detection model. [cite: 703] |

### [cite_start]7.3 Schema Requirements by Fraud Algorithm [cite: 704]

| Fraud Pattern | Schema Requirement | Why This Matters |
| :--- | :--- | :--- |
| **Round-Tripping** | [cite_start]Directed edges with Timestamp on every edge. [cite: 704] | [cite_start]Cycles must be detected in chronological order — forward-only time flow prevents false positives. [cite: 705, 706] |
| **Structuring** | [cite_start]Amount and WeightedVolume_24h on edges. [cite: 706] | [cite_start]Sliding window aggregation needs per-edge amounts to detect cumulative threshold evasion. [cite: 706, 707] |
| **Profile Mismatch** | [cite_start]OWNED_BY edge linking Account to Customer with DeclaredIncome. [cite: 707, 708] | [cite_start]ML model compares actual account activity volume against KYC declared income. [cite: 708] |
| **Layering** | [cite_start]Global_Transaction_ID on every edge. [cite: 709, 711] | [cite_start]Proves causal money chain across hops — legally essential for STR evidence. [cite: 711] |
| **Dormant Activation** | [cite_start]LastActivityDate on Account node. [cite: 711, 712] | [cite_start]Degree centrality change detection requires a historical activity baseline to measure against. [cite: 712] |

---

## [cite_start]8. Graph Algorithms — Neo4j GDS Library [cite: 714]

[cite_start]Neo4j's Graph Data Science library provides over 65 graph algorithms exposed as Cypher procedures. [cite: 714] UniGraph uses algorithms from five categories. [cite_start]Critically, these algorithms do not run on the live database — they run on in-memory graph projections, completely isolating analytical compute from transactional reads. [cite: 715] [cite_start]The output of these algorithms (PageRank score, community ID, betweenness centrality) are then written back as node properties and used as ML features. [cite: 716]

| Category | Algorithm | Fraud Use Case | Output |
| :--- | :--- | :--- | :--- |
| **Pathfinding** | Shortest Path (Dijkstra) | [cite_start]Trace minimum-hop fund path from dirty source to clean destination. [cite: 717, 718] | [cite_start]Ordered path with hop count, total amount, elapsed time. [cite: 718, 719] |
| **Pathfinding** | BFS / DFS Traversal | [cite_start]Layering — follow fund chains within tight time windows. [cite: 719, 720] | [cite_start]Ordered account list in fund flow chain. [cite: 720] |
| **Centrality** | PageRank | [cite_start]Identify hub accounts with disproportionate influence — likely mule coordinators. [cite: 720, 721] | [cite_start]Numeric influence score per node. [cite: 721] |
| **Centrality** | Betweenness Centrality | [cite_start]Find critical bridge accounts between disconnected networks — layering intermediaries. [cite: 721, 722] | Bridge score. [cite_start]High = key intermediary. [cite: 722] |
| **Centrality** | Degree Centrality | [cite_start]Detect sudden degree spikes in dormant accounts. [cite: 722, 723] | [cite_start]Current edge count vs. historical baseline. [cite: 723] |
| **Community Detection** | Louvain Modularity | [cite_start]Identify fraud rings — clusters that transact primarily with each other. [cite: 723, 724] | [cite_start]Community ID assigned to each account. [cite: 724] |
| **Community Detection** | Weakly Connected Components | [cite_start]Isolate money mule ring sub-networks. [cite: 724, 725] | [cite_start]Component ID isolating disconnected sub-graphs. [cite: 725] |
| **Similarity** | Jaccard / Cosine Similarity | [cite_start]Profile mismatch — compare transaction neighbourhood against declared peer group. [cite: 725, 726] | Similarity score 0-1. [cite_start]Low = behavioural outlier. [cite: 726] |
| **Node Embeddings** | GraphSAGE | [cite_start]Generate vector representations capturing neighbourhood structure for GNN input. [cite: 726, 727] | [cite_start]128-dimensional embedding per node. [cite: 727] |
| **Node Embeddings** | Node2Vec | [cite_start]Random-walk embeddings for similarity and clustering tasks. [cite: 727, 728] | [cite_start]Embedding vector per node. [cite: 728] |

---

## [cite_start]9. Complete Technology Stack with Justifications [cite: 730]

[cite_start]Every technology in this stack was chosen with a specific technical reason. [cite: 730] [cite_start]The guiding principles were: use the right data structure for the access pattern (graph for relationships, Cassandra for time-series), keep latency below 500ms end-to-end, and keep all sensitive data on-premise. [cite: 731]

| Layer | Technology | Role in System | Why Not the Alternative |
| :--- | :--- | :--- | :--- |
| **Ingestion** | Apache Kafka | [cite_start]Central event bus — ordered, replayable, high throughput. [cite: 732, 733] | RabbitMQ has no log retention. SQS cannot replay. [cite_start]Kafka retains 7 days for fraud backfill. [cite: 733, 734] |
| **Ingestion** | Apache Flink | [cite_start]True streaming enrichment — event-at-a time, stateful. [cite: 734, 735] | Spark Streaming is micro-batch with seconds of latency. [cite_start]Fraud needs milliseconds. [cite: 735, 736] |
| **Ingestion** | Debezium CDC | [cite_start]Zero-impact DB change capture via WAL monitoring. [cite: 736] | ETL batch pipelines are slow. [cite_start]Direct DB polling harms production performance. [cite: 736, 737] |
| **Graph DB** | Neo4j Enterprise | [cite_start]Native graph storage with 65+ GDS algorithms. [cite: 737, 738] | PostgreSQL JOINs are O(n cubed) for multi-hop. [cite_start]Neo4j traversal is O(1) per hop. [cite: 738, 739] |
| **Storage** | Apache Cassandra | [cite_start]Time-series transaction history partitioned by account_id. [cite: 739, 740] | [cite_start]MySQL is not horizontally scalable for write-heavy time series at 100K TPS. [cite: 740, 741] |
| **Storage** | Redis | [cite_start]Hot subgraph cache for investigator UI. [cite: 741] | [cite_start]In-memory Neo4j projections are not persistent across restarts. [cite: 741, 742] |
| **ML** | PyTorch Geometric | [cite_start]GraphSAGE GNN training and inference on transaction subgraphs. [cite: 742, 743] | [cite_start]Standard PyTorch does not natively handle graph-structured data. [cite: 743, 744] |
| **ML** | XGBoost | [cite_start]High-speed binary fraud classifier on tabular and graph features. [cite: 744, 745] | Neural networks are slower and harder to explain. [cite_start]XGBoost + SHAP = fast + auditable. [cite: 745, 746] |
| **ML** | Drools BRE | [cite_start]Deterministic, human readable AML rule execution. [cite: 746, 747] | [cite_start]Hard-coded conditionals are not auditable or updatable by non engineers. [cite: 747, 748] |
| **ML Ops** | MLflow | [cite_start]Model versioning, A/B testing, experiment tracking, rollback. [cite: 748, 749] | [cite_start]Without versioning, model updates in production are irreversible and unauditable. [cite: 749, 750] |
| **Backend** | FastAPI (Python) | [cite_start]REST API and Kafka consumer microservice. [cite: 750] | Django is too heavyweight. [cite_start]Flask lacks async support for Kafka. [cite: 750, 751] |
| **Backend** | Node.js + WebSockets | [cite_start]Real-time alert push to investigator dashboard. [cite: 751, 752] | HTTP polling introduces latency. [cite_start]WebSockets deliver in under 50ms. [cite: 752] |
| **Frontend** | React.js | [cite_start]Component-based investigator dashboard with real-time state. [cite: 752, 753] | Angular is heavier. [cite_start]Vue has fewer enterprise financial tooling integrations. [cite: 753, 754] |
| **Frontend** | Cytoscape.js | [cite_start]Interactive network graph rendering for thousands of nodes. [cite: 754, 755] | [cite_start]D3.js requires extensive custom coding for graph layouts. [cite: 755] |
| **LLM** | Ollama + Qwen 3.5 9B | [cite_start]On-premise STR narrative generation — zero data leaves the bank. [cite: 757, 758] | [cite_start]Cloud LLM APIs send sensitive financial data to third-party servers — RBI non-compliant. [cite: 758, 759] |
| **Orchestration** | Kubernetes + Helm | [cite_start]Container orchestration, auto-scaling, rolling deployments. [cite: 759, 760] | [cite_start]Docker Compose does not support production-grade HA or auto-scaling. [cite: 760, 761] |
| **Orchestration** | Apache Airflow | [cite_start]Scheduled ML retraining, batch analytics, report generation. [cite: 761, 762] | [cite_start]Cron jobs have no dependency management, retry logic, or monitoring. [cite: 762] |

---

## [cite_start]10. Build Roadmap — 34-Week Delivery Plan [cite: 764]

[cite_start]The roadmap is structured into five sequential phases, each with clear deliverables. [cite: 764] [cite_start]Phases are sequential by dependency but support parallel workstreams internally. [cite: 765] [cite_start]The total timeline is 34 weeks from kickoff to production-ready deployment. [cite: 766]

[cite_start]**Phase 1: Foundation and Data Pipeline — Weeks 1-6** [cite: 767]
* [cite_start]Set up Apache Kafka cluster with KRaft and configure topic partitioning strategy by account_id. [cite: 767]
* [cite_start]Implement Debezium CDC connectors for Oracle and Temenos Core Banking databases. [cite: 768]
* [cite_start]Design and deploy Neo4j graph schema with all node labels, relationship types, and property definitions. [cite: 769]
* [cite_start]Build Apache Flink enrichment pipeline: KYC join, geolocation enrichment, device fingerprint append. [cite: 770]
* [cite_start]Configure Confluent Schema Registry with Avro schemas for all event types. [cite: 771]
* [cite_start]Set up Dead Letter Queue (DLQ) for malformed events and basic data quality monitoring dashboards. [cite: 772]

[cite_start]**Phase 2: Graph Analytics and Rule Engine — Weeks 7-12** [cite: 773]
* [cite_start]Implement Neo4j GDS algorithms: PageRank, Louvain, Betweenness Centrality, Shortest Path, WCC. [cite: 773]
* [cite_start]Build Drools rule engine with first 20 AML rules — velocity, threshold, jurisdiction, dormancy. [cite: 774]
* [cite_start]Implement Johnson's Algorithm for cycle detection (round-tripping). [cite: 775]
* [cite_start]Build temporal query layer for sliding window aggregations (structuring detection). [cite: 775]
* [cite_start]Create alert generation pipeline with severity scoring and Kafka output topic for downstream consumption. [cite: 776]
* [cite_start]Set up Cassandra time-series schema with optimised partitioning for investigator queries. [cite: 777]

[cite_start]**Phase 3: ML Models and Ensemble Scorer — Weeks 13-20** [cite: 778]
* [cite_start]Historical data labeling pipeline with input from the bank's fraud investigation team. [cite: 778]
* [cite_start]Feature engineering: extract 30+ graph features per node using GDS algorithms as inputs. [cite: 779]
* [cite_start]Train GraphSAGE GNN using PyTorch Geometric on historical labelled transaction graphs. [cite: 780]
* [cite_start]Train Isolation Forest for behavioural anomaly detection on account activity feature vectors. [cite: 781]
* [cite_start]Train XGBoost ensemble scorer and calibrate risk score thresholds using ROC curve analysis. [cite: 782]
* [cite_start]Set up MLflow model registry with versioning, A/B testing framework, and weekly automated retraining via Airflow. [cite: 783]

[cite_start]**Phase 4: Investigator Dashboard and Case Management — Weeks 21-28** [cite: 784]
* [cite_start]Build React and Cytoscape.js graph explorer: expand and collapse nodes, filter by time, amount, and channel. [cite: 784]
* [cite_start]Implement real-time WebSocket alert delivery from Node.js backend to React frontend. [cite: 785]
* [cite_start]Case management module: full CRUD, status workflow, evidence attachment, notes, and supervisor review. [cite: 786]
* [cite_start]Alert queue UI with priority sorting, bulk assignment, and filter and search capabilities. [cite: 787]
* [cite_start]Role-based access control: Analyst, Senior Investigator, Manager, and Auditor roles with permission scoping. [cite: 788]

[cite_start]**Phase 5: LLM Reporting and Production Hardening — Weeks 29-34** [cite: 789, 790]
* [cite_start]Deploy Ollama with Qwen 3.5 9B on-premise and build STR narrative generation prompt templates. [cite: 790]
* [cite_start]STR and CTR auto-population in FIU-IND XML format, FATF format, and internal PDF template. [cite: 791]
* [cite_start]Evidence package builder: one-click PDF export with graph screenshot, full transaction trail, and stats. [cite: 792]
* [cite_start]FIU-IND API integration with encrypted submission, tracking ID storage, and submission status monitoring. [cite: 793]
* [cite_start]Sustained load testing at 100K TPS for 4-hour windows with P99 latency validation below 500ms. [cite: 794]
* [cite_start]Security audit, penetration testing, VAPT, and regulatory compliance review before go-live. [cite: 795]

### [cite_start]10.1 Recommended Team Composition [cite: 796]

| Role | Headcount | Core Responsibility |
| :--- | :--- | :--- |
| **Data and Platform Engineers** | 2-3 | [cite_start]Kafka, Flink, Debezium pipelines, Cassandra, Redis infrastructure. [cite: 796] |
| **Graph Database Engineer** | 1-2 | [cite_start]Neo4j schema, GDS algorithm implementation, Cypher query optimisation. [cite: 797] |
| **ML Engineers** | 2 | [cite_start]GNN training, Isolation Forest, XGBoost ensemble, MLflow ops. [cite: 798] |
| **Backend Engineers** | 2-3 | [cite_start]FastAPI microservices, Node.js WebSocket gateway, case management API. [cite: 799] |
| **Frontend Engineers** | 2 | [cite_start]React graph explorer, Cytoscape.js rendering, alert dashboard. [cite: 800] |
| **DevOps and Platform** | 1-2 | [cite_start]Kubernetes, Helm, Airflow, monitoring, CI/CD pipelines. [cite: 801] |
| **Fraud Domain Expert** | 1 | [cite_start]AML rule definition, typology validation, FIU liaison, investigator training. [cite: 802] |
| **Security Engineer** | 1 | [cite_start]HashiCorp Vault, OPA policies, penetration testing, VAPT. [cite: 803] |

---

## [cite_start]11. Competitive Positioning and Innovation [cite: 804]

### [cite_start]11.1 UniGraph vs. Traditional AML Systems [cite: 805]

| Capability | Traditional AML Systems | UniGraph |
| :--- | :--- | :--- |
| **Detection Logic** | Static threshold rules — e.g., amount over Rs. [cite_start]10L triggers alert. [cite: 805, 806] | [cite_start]Graph topology and ML ensemble — detects structure, not just thresholds. [cite: 806] |
| **Multi-hop Analysis** | [cite_start]1-2 hops maximum due to SQL JOIN cost. [cite: 807] | Unlimited hop depth at O(1) per hop. [cite_start]Standard queries run 5-10 hops. [cite: 807, 808] |
| **Novel Pattern Detection** | [cite_start]Cannot detect patterns not in the rulebook. [cite: 808] | [cite_start]GNN detects structurally anomalous subgraphs never seen before. [cite: 809] |
| **Alert Latency** | [cite_start]Batch processing — hours to days. [cite: 809] | [cite_start]Under 500ms from transaction to investigator alert. [cite: 810] |
| **Investigator Interface** | [cite_start]Excel reports and SQL query outputs. [cite: 810] | [cite_start]Interactive visual graph explorer — see the crime, not read about it. [cite: 811] |
| **STR Generation** | [cite_start]Manual — 2-4 hours per report. [cite: 811] | [cite_start]AI-assisted — 5-minute review and approve workflow. [cite: 812] |
| **LLM Data Privacy** | [cite_start]Cloud AI APIs — data leaves the bank. [cite: 812] | [cite_start]On-premise Ollama — zero data leakage, full RBI compliance. [cite: 813] |
| **Explainability** | [cite_start]Black-box scores with no justification. [cite: 813] | [cite_start]SHAP feature importance with full graph path evidence package. [cite: 814] |

### [cite_start]11.2 Supporting Research and References [cite: 815]
* [cite_start]**KPMG — Bridging Innovation and Compliance in FCC (2025):** Confirms legacy rule-based systems are losing effectiveness and validates the ML/graph transition. [cite: 815]
* [cite_start]**IBA Draft Framework on Money Mule Accounts (April 2025):** Mandates AI/ML-driven dynamic frameworks — directly validates UniGraph's architecture. [cite: 816]
* [cite_start]**Neo4j — Detect and Investigate Financial Crime Patterns (Linkurious):** Technical validation of graph databases for AML investigation. [cite: 817]
* [cite_start]**Digitalisation World — Use Analytical Graph Databases to Streamline AML:** Confirms SQL is 'not very good at analysing relationships between data objects.' [cite: 818]
* [cite_start]**TigerGraph — Money Laundering Detection with AML Graph Analytics:** Industry case study on structuring and layering detection. [cite: 819]
* [cite_start]**ResearchGate — Temporal Graph Neural Network for Deep Fraud Detection (2024):** Academic validation of the TGNN approach for real-time financial fraud. [cite: 820]
* [cite_start]**Nvidia — Graph Analytics Glossary:** Technical overview of graph analytics applied to financial data. [cite: 821]

---

## [cite_start]12. Glossary of Key Terms [cite: 823]

[cite_start]This glossary is designed so that every team member can confidently answer judge questions and explain technical concepts during the hackathon presentation without memorising definitions beforehand. [cite: 823]

| Term | Definition |
| :--- | :--- |
| **AML** | Anti-Money Laundering. [cite_start]The set of laws and procedures designed to prevent criminals from disguising illegally obtained funds as legitimate income. [cite: 824] |
| **Betweenness Centrality** | A graph metric measuring how often a node appears on the shortest path between other nodes. [cite_start]High betweenness = bridge account = potential layering intermediary. [cite: 825, 826] |
| **CDC (Change Data Capture)** | [cite_start]A technique that tracks database changes in real-time by reading the Write Ahead Log, with zero impact on production database performance. [cite: 826, 827] |
| **Community Detection** | [cite_start]Graph algorithms (Louvain, Label Propagation) that find clusters of nodes densely connected to each other — used to detect fraud rings. [cite: 828] |
| **Cypher** | Neo4j's declarative graph query language. [cite_start]Like SQL for relational DBs, but designed for querying graph relationships. [cite: 829] |
| **Degree Centrality** | A graph metric counting how many direct connections (edges) a node has. [cite_start]A dormant account with zero edges suddenly having 40 is a degree spike. [cite: 830] |
| **Drools BRE** | Business Rule Management System. [cite_start]Evaluates human-readable, auditable AML rules at up to 1 million events per second. [cite: 831, 832] |
| **Embedding** | [cite_start]A mathematical vector representation of a node that captures its structural position in the graph, used as input features for ML models. [cite: 833] |
| **FIU-IND** | Financial Intelligence Unit India. [cite_start]The national agency receiving and processing financial intelligence on money laundering and terrorist financing. [cite: 834] |
| **GDS** | Graph Data Science. [cite_start]Neo4j's library of 65+ graph algorithms running on in memory projections for analytics without touching the live database. [cite: 835] |
| **GNN (Graph Neural Network)** | [cite_start]A neural network operating on graph-structured data, learning node representations by aggregating features from neighbouring nodes. [cite: 836] |
| **GraphSAGE** | Graph Sample and Aggregate. [cite_start]A GNN architecture that learns node embeddings by sampling and aggregating features from a fixed-size set of neighbours. [cite: 837] |
| **Isolation Forest** | An unsupervised ML algorithm for anomaly detection. [cite_start]Anomalous data points require fewer partitions to isolate in random feature space partitioning. [cite: 838] |
| **Johnson's Algorithm** | [cite_start]A graph algorithm for finding all simple cycles in a directed graph — the core algorithm used for round-tripping cycle detection. [cite: 839] |
| **KYC** | Know Your Customer. [cite_start]The regulatory process of verifying a customer's identity, occupation, income, and expected transaction behaviour before account opening. [cite: 840] |
| **Louvain Algorithm** | [cite_start]A community detection algorithm finding clusters of nodes densely connected internally and sparsely connected externally — detects fraud rings. [cite: 841] |
| **LLM** | Large Language Model. An AI model that can generate human-quality prose. [cite_start]UniGraph uses Qwen 3.5 9B locally via Ollama for STR narrative generation. [cite: 843, 844] |
| **MLflow** | [cite_start]An open-source platform for ML lifecycle management — experiment tracking, model versioning, A/B testing, and deployment with full rollback capability. [cite: 845] |
| **Money Mule** | [cite_start]An individual who transfers illegally obtained money on behalf of criminals, often unknowingly, acting as an intermediary to obscure the money trail. [cite: 846] |
| **Ollama** | [cite_start]An open-source framework for running large language models locally on premise, without sending data to any cloud service — essential for banking compliance. [cite: 847] |
| **PageRank** | A graph centrality algorithm identifying accounts with high influence. [cite_start]In a transaction graph, high PageRank indicates potential mule coordinator accounts. [cite: 848, 849] |
| **Round-Tripping** | [cite_start]A laundering technique where funds are sent through a chain of accounts and returned to the originating account, creating the appearance of legitimate revenue. [cite: 850] |
| **SHAP** | SHapley Additive exPlanations. [cite_start]A method quantifying the contribution of each input feature to an ML model prediction — makes XGBoost decisions auditable. [cite: 851] |
| **STR** | Suspicious Transaction Report. Formal document that banks must file with FIU-IND when detecting suspected money laundering. [cite_start]Must be filed within 7 days. [cite: 852, 853] |
| **Structuring (Smurfing)** | [cite_start]Deliberately splitting a large amount into multiple smaller transactions to stay below regulatory reporting thresholds and avoid detection. [cite: 853] |
| **TBML** | Trade-Based Money Laundering. [cite_start]Using international trade transactions and invoicing to move illicit money across borders. [cite: 854] |
| **UBO** | Ultimate Beneficial Owner. [cite_start]The natural person who ultimately owns or controls a company or account, even through intermediate legal entities. [cite: 855] |
| **WCC** | Weakly Connected Components. [cite_start]A graph algorithm identifying groups of nodes mutually reachable (ignoring direction) — used to isolate disconnected fraud sub-networks. [cite: 856] |
| **WebSocket** | [cite_start]A communication protocol providing a persistent two-way connection between client and server, used to push real-time alerts to the investigator dashboard instantly. [cite: 857] |
| **XGBoost** | Extreme Gradient Boosting. [cite_start]A high-accuracy, high-speed tree-based ML algorithm used as the ensemble scorer for its combination of performance and SHAP explainability. [cite: 858] |