# UniGRAPH SQL Transaction Dataset Structure

## 1. Scope
This document defines the dataset structure for storing all transaction types in SQL, including UPI, IMPS, NEFT, RTGS, CASH, and SWIFT.
It is a structure specification only: row definition, columns, data types, keys, and indexing guidance.

## 2. Row Definition (Which Rows)
One row represents one transaction event.

| Row category | transaction_event_type | Meaning | Include in reporting |
|---|---|---|---|
| Financial movement | POSTED | Successful posted transaction | Yes |
| Failed attempt | FAILED | Attempted but failed transaction | Optional, for fraud analytics |
| Reversal | REVERSAL | Reversal of a previous posted transaction | Yes |
| Chargeback/dispute | CHARGEBACK | Customer or network dispute flow | Yes |
| Adjustment/correction | ADJUSTMENT | Manual or system correction entry | Yes |

Rules:
- Keep one event per row.
- Use reference_txn_id to link REVERSAL, CHARGEBACK, or ADJUSTMENT rows to the original row.
- Do not overwrite posted rows; create a new lifecycle row.

## 3. Core Table (Columns Required for All Channels)
Table name: transactions

| Column | SQL type | Null | Key/Index | Description |
|---|---|---|---|---|
| txn_id | VARCHAR(64) | No | Primary Key | Unique transaction identifier |
| transaction_event_type | VARCHAR(20) | No | Index | POSTED, FAILED, REVERSAL, CHARGEBACK, ADJUSTMENT |
| reference_txn_id | VARCHAR(64) | Yes | Index | Parent transaction for reversal/dispute/correction |
| from_account | VARCHAR(32) | No | Index | Debited account identifier |
| to_account | VARCHAR(32) | Yes | Index | Credited account identifier (may be null for some cash events) |
| customer_id | VARCHAR(32) | No | Index | Customer identifier |
| amount | DECIMAL(18,2) | No | Index | Transaction amount |
| currency | CHAR(3) | No |  | ISO currency code (default INR) |
| channel | VARCHAR(16) | No | Index | UPI, IMPS, NEFT, RTGS, CASH, SWIFT |
| txn_status | VARCHAR(20) | No | Index | SUCCESS, FAILED, PENDING, REVERSED, CHARGEBACK |
| txn_timestamp | TIMESTAMP | No | Index | Event timestamp in UTC |
| value_date | DATE | Yes | Index | Settlement/value date |
| narration | VARCHAR(255) | Yes |  | Free-text narration or purpose |
| source_system | VARCHAR(40) | No |  | Origin system name |
| ingest_ts | TIMESTAMP | Yes | Index | Pipeline ingest time |
| pipeline_version | VARCHAR(20) | Yes |  | Enrichment/version trace |
| created_at | TIMESTAMP | No |  | Row creation time |
| updated_at | TIMESTAMP | Yes |  | Last update time |

## 4. Fraud and Enrichment Columns (Still in Core or Side Table)
These can stay in transactions or be moved to a companion table transaction_risk_features at high scale.

| Column | SQL type | Null | Description |
|---|---|---|---|
| risk_score | DECIMAL(5,2) | Yes | Combined fraud risk score (0-100) |
| ml_score | DECIMAL(5,2) | Yes | ML model score (0-100) |
| is_flagged | BOOLEAN | No | Whether transaction is flagged |
| alert_id | VARCHAR(64) | Yes | Linked alert identifier |
| rule_violations_json | JSON | Yes | Violated rules list/details |
| is_fraud | BOOLEAN | Yes | Label for training or investigation |
| fraud_type | VARCHAR(40) | Yes | LAYERING, STRUCTURING, ROUND_TRIP, DORMANT, MULE_NETWORK, TBML |
| counterparty_risk_score | DECIMAL(5,2) | Yes | Counterparty risk feature |

## 5. Device, Network, and Geo Columns

| Column | SQL type | Null | Description |
|---|---|---|---|
| device_fingerprint | VARCHAR(128) | Yes | Device identity hash |
| ip_address | VARCHAR(64) | Yes | IP hash or tokenized address |
| geo_lat | DECIMAL(9,6) | Yes | Latitude |
| geo_lon | DECIMAL(9,6) | Yes | Longitude |
| location_json | JSON | Yes | Original location object if needed |
| geo_distance_from_home_km | DECIMAL(10,3) | Yes | Distance anomaly feature |
| is_international | BOOLEAN | Yes | International indicator |
| channel_switch_count | INT | Yes | Channel switching behavior feature |
| device_account_count | INT | Yes | Number of accounts tied to same device |

## 6. Channel-Specific Columns
Recommended model: one extension table transaction_channel_details keyed by txn_id.

Table name: transaction_channel_details
Primary key: txn_id
Foreign key: txn_id references transactions(txn_id)

| Column | SQL type | UPI | IMPS | NEFT | RTGS | CASH | SWIFT | Description |
|---|---|---|---|---|---|---|---|---|
| vpa | VARCHAR(128) | Required | No | No | No | No | No | UPI virtual payment address |
| upi_app | VARCHAR(50) | Optional | No | No | No | No | No | UPI app/provider |
| rrn | VARCHAR(30) | Optional | Required | Optional | Optional | No | No | Retrieval reference number |
| utr_number | VARCHAR(30) | Optional | Optional | Required | Required | No | Optional | Bank transfer reference |
| payer_ifsc | CHAR(11) | No | Optional | Required | Required | No | No | Payer bank IFSC |
| payee_ifsc | CHAR(11) | No | Optional | Required | Required | No | No | Payee bank IFSC |
| settlement_batch_id | VARCHAR(40) | No | Optional | Required | Required | Optional | Optional | Clearing/settlement batch |
| settlement_status | VARCHAR(20) | Optional | Optional | Required | Required | Optional | Optional | PENDING, SETTLED, REJECTED |
| cash_branch_id | VARCHAR(20) | No | No | No | No | Required | No | Branch for cash transaction |
| teller_id | VARCHAR(20) | No | No | No | No | Optional | No | Teller/counter reference |
| denomination_summary_json | JSON | No | No | No | No | Optional | No | Cash denomination breakdown |
| bic_code | CHAR(11) | No | No | No | No | No | Required | SWIFT BIC |
| iban | VARCHAR(34) | No | No | No | No | No | Optional | International account identifier |
| invoice_reference | VARCHAR(64) | No | No | Optional | Optional | No | Required | Trade/invoice reference |
| remittance_country | CHAR(2) | No | No | No | No | No | Optional | ISO country code |
| correspondent_bank | VARCHAR(100) | No | No | No | No | No | Optional | Correspondent bank details |

## 7. Keys, Constraints, and Indexes
Minimum constraints:
- Primary key on transactions.txn_id.
- Foreign key from transaction_channel_details.txn_id to transactions.txn_id.
- Optional unique key on channel-specific identifiers where applicable (for example, utr_number by channel and date).

Recommended indexes:
- idx_transactions_account_time on from_account, txn_timestamp DESC.
- idx_transactions_customer_time on customer_id, txn_timestamp DESC.
- idx_transactions_channel_time on channel, txn_timestamp DESC.
- idx_transactions_status_time on txn_status, txn_timestamp DESC.
- idx_transactions_risk on is_flagged, risk_score DESC.
- idx_transactions_reference on reference_txn_id.

## 8. Suggested SQL Dataset Output View
Create an analytics view that joins core and channel details:
- v_transactions_dataset = transactions LEFT JOIN transaction_channel_details on txn_id.
- This gives one wide row for BI/reporting while preserving normalized storage.

## 9. Future Channels (Optional)
If CARD, WALLET, NETBANKING, or AEPS are added later:
- Keep core columns unchanged.
- Add new optional columns in transaction_channel_details.
- Update the channel applicability matrix only.

## 10. Naming Compatibility Note
Current pipeline examples use from_account and to_account.
If your SQL standard prefers from_account_id and to_account_id, keep aliases in views to avoid breaking ingestion and API contracts.
