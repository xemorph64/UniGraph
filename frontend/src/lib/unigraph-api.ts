import type { Transaction } from "@/data/transactions";
import { toShapSummaryLines } from "@/lib/shap-explain";

export interface BackendTransaction {
  id: string;
  from_account: string;
  to_account: string;
  amount: number;
  channel: string;
  timestamp: string;
  risk_score?: number;
  is_flagged?: boolean;
  rule_violations?: string[];
  primary_fraud_type?: string;
  gnn_fraud_probability?: number;
  if_anomaly_score?: number;
  xgboost_risk_score?: number;
  model_version?: string;
  scoring_source?: string;
}

export interface BackendAlert {
  id: string;
  transaction_id?: string;
  account_id?: string;
  risk_score?: number;
  ensemble_score?: number;
  risk_level?: string;
  recommendation?: string;
  shap_top3?: string[];
  rule_flags?: string[];
  primary_fraud_type?: string;
  fraud_type?: string;
  status?: string;
  created_at?: string;
  alert_timestamp?: string;
}

export interface AlertCardLike {
  id: string;
  fraudType: string;
  account: string;
  amount: string;
  riskScore: number;
  channel: string;
  timeDetected: string;
  shapReason: string;
  description: string;
  recommendedAction: string;
  status: string;
  transactionId: string;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvestigationResponse {
  alert: BackendAlert;
  transaction?: BackendTransaction;
  graph: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
  investigation_note: string;
}

export interface STRReport {
  id: string;
  alert_id: string;
  account_id: string;
  risk_score: number;
  narrative: string;
  status: string;
  reference_id?: string | null;
  created_at?: string;
  submitted_at?: string | null;
}

export interface STRGenerateResponse {
  str_id: string;
  narrative: string;
  status: string;
  alert_id: string;
  account_id: string;
  risk_score: number;
}

export interface STRSubmitResponse {
  str_id: string;
  status: string;
  reference_id: string;
  provider_response?: Record<string, unknown>;
}

export interface IngestTransactionRequest {
  txnId?: string;
  fromAccount: string;
  toAccount: string;
  amount: number;
  channel?: string;
  customerId?: string;
  description?: string;
  deviceId?: string;
  isDormant?: boolean;
  deviceAccountCount?: number;
  velocity1h?: number;
  velocity24h?: number;
}

export interface IngestTransactionResponse {
  txn_id: string;
  from_account: string;
  to_account: string;
  amount: number;
  channel: string;
  timestamp: string;
  risk_score: number;
  risk_level: string;
  recommendation: string;
  rule_violations: string[];
  primary_fraud_type?: string | null;
  is_flagged: boolean;
  alert_id?: string | null;
  gnn_fraud_probability?: number;
  if_anomaly_score?: number;
  xgboost_risk_score?: number;
  model_version?: string;
  scoring_source?: string;
}

export interface BackendHealthResponse {
  status: string;
  version: string;
  neo4j: string;
  fraud_scoring?: {
    ml_service_reachable?: boolean;
    ml_service_url?: string;
    ml_model_version?: string | null;
    fallback_mode_available?: boolean;
    ml_error?: string;
  };
  graph_stats?: {
    total_accounts?: number;
    total_transactions?: number;
    total_alerts?: number;
    flagged_accounts?: number;
  };
  demo_mode?: boolean;
}

export interface GraphAnalyticsStatusResponse {
  status: string;
  gds: {
    total_accounts: number;
    with_pagerank: number;
    with_community: number;
    with_betweenness: number;
    max_pagerank: number;
    distinct_communities: number;
    top_accounts: Array<{
      account_id: string;
      pagerank: number;
      community_id: number;
      betweenness_centrality: number;
      risk_score: number;
    }>;
  };
  patterns?: Record<string, unknown>;
  algorithms: string[];
}

export interface MlHealthResponse {
  status: string;
  model_version?: string;
  gnn_loaded?: boolean;
  if_loaded?: boolean;
  xgb_loaded?: boolean;
  fallback_ready?: boolean;
}

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
const API_PREFIX = `${API_BASE}/api/v1`;
const ML_BASE = (import.meta.env.VITE_ML_SERVICE_URL || "http://localhost:8002").replace(/\/$/, "");

function toQuery(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return {} as T;
  }

  return (await response.json()) as T;
}

async function fetchJson<T>(path: string): Promise<T> {
  return requestJson<T>(path);
}

async function fetchAbsoluteJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }
  return (await response.json()) as T;
}

function formatCurrency(amount?: number) {
  if (typeof amount !== "number" || Number.isNaN(amount)) {
    return "N/A";
  }
  return `INR ${Math.round(amount).toLocaleString("en-IN")}`;
}

function formatTimestamp(timestamp?: string) {
  if (!timestamp) return "-";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return timestamp;

  const day = String(parsed.getDate()).padStart(2, "0");
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const year = parsed.getFullYear();
  const hour = String(parsed.getHours()).padStart(2, "0");
  const minute = String(parsed.getMinutes()).padStart(2, "0");
  return `${day}/${month}/${year} ${hour}:${minute}`;
}

function normalizeChannel(channel?: string): Transaction["channel"] {
  const normalized = (channel || "IMPS").toUpperCase();
  if (normalized === "CARD") return "Card";
  if (normalized === "CASH") return "CASH";
  if (normalized === "UPI") return "UPI";
  if (normalized === "RTGS") return "RTGS";
  if (normalized === "NEFT") return "NEFT";
  return "IMPS";
}

export function riskStatus(score: number) {
  if (score >= 80) return "Flagged";
  if (score >= 60) return "Pending";
  return "Cleared";
}

function prettifyFlag(flag: string) {
  return flag
    .toLowerCase()
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

const FRAUD_TYPE_PRIORITY = [
  "MULE_NETWORK",
  "DORMANT_AWAKENING",
  "RAPID_LAYERING",
  "ROUND_TRIPPING",
  "STRUCTURING",
];

const FRAUD_TYPE_LABELS: Record<string, string> = {
  MULE_NETWORK: "Mule Account Network",
  DORMANT_AWAKENING: "Dormant Account Awakening",
  RAPID_LAYERING: "Rapid Layering",
  ROUND_TRIPPING: "Round-Tripping",
  STRUCTURING: "Structuring",
};

function normalizeRuleToken(value?: string) {
  if (!value) return "";
  return value
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function formatFraudType(value?: string) {
  if (!value) return "Anomaly";
  const token = normalizeRuleToken(value);
  if (token && FRAUD_TYPE_LABELS[token]) {
    return FRAUD_TYPE_LABELS[token];
  }
  return prettifyFlag(token || value);
}

export function deriveFraudType(flags: string[], primaryFraudType?: string) {
  const primaryToken = normalizeRuleToken(primaryFraudType);
  if (primaryToken) {
    return formatFraudType(primaryToken);
  }

  const normalizedFlags = flags
    .map((flag) => normalizeRuleToken(flag))
    .filter((flag) => Boolean(flag));

  if (!normalizedFlags.length) return "Anomaly";

  for (const candidate of FRAUD_TYPE_PRIORITY) {
    if (normalizedFlags.includes(candidate)) {
      return formatFraudType(candidate);
    }
  }

  return formatFraudType(normalizedFlags[0]);
}

export function toUiTransaction(txn: BackendTransaction): Transaction {
  const score = Math.round(txn.risk_score || 0);
  return {
    txnId: txn.id,
    source: txn.from_account,
    destination: txn.to_account,
    amount: formatCurrency(txn.amount),
    amountNum: typeof txn.amount === "number" ? txn.amount : 0,
    channel: normalizeChannel(txn.channel),
    timestamp: formatTimestamp(txn.timestamp),
    riskScore: score,
    status: riskStatus(score),
    flags: (txn.rule_violations || []).map(prettifyFlag),
    branch: "-",
    scoringSource: txn.scoring_source,
    modelVersion: txn.model_version,
  };
}

export function toAlertCard(alert: BackendAlert, txn?: BackendTransaction): AlertCardLike {
  const flags = (alert.rule_flags || []).map(prettifyFlag);
  const type = alert.fraud_type || alert.primary_fraud_type || deriveFraudType(alert.rule_flags || [], alert.primary_fraud_type);
  const shapSummary = toShapSummaryLines(alert.shap_top3, 2).join(" + ");

  return {
    id: alert.id,
    fraudType: type,
    account: alert.account_id || "-",
    amount: txn ? formatCurrency(txn.amount) : "N/A",
    riskScore: Math.round(alert.risk_score || alert.ensemble_score || 0),
    channel: txn?.channel || "-",
    timeDetected: formatTimestamp(alert.created_at || alert.alert_timestamp),
    shapReason: shapSummary || "Pattern-based risk detection",
    description: alert.recommendation || `${type} signal triggered by risk engine`,
    recommendedAction: alert.recommendation || "Investigate alert",
    status: alert.status || "OPEN",
    transactionId: alert.transaction_id || "",
  };
}

export async function listTransactions(params?: {
  page?: number;
  pageSize?: number;
  channel?: string;
  minRiskScore?: number;
  accountId?: string;
  txnIdPrefix?: string;
}) {
  const query = toQuery({
    page: params?.page || 1,
    page_size: params?.pageSize || 50,
    channel: params?.channel,
    min_risk_score: params?.minRiskScore,
    account_id: params?.accountId,
    txn_id_prefix: params?.txnIdPrefix,
  });
  return fetchJson<ListResponse<BackendTransaction>>(`/transactions?${query}`);
}

export async function getTransaction(txnId: string) {
  return fetchJson<BackendTransaction>(`/transactions/${encodeURIComponent(txnId)}`);
}

export async function listAlerts(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  minRiskScore?: number;
  transactionIdPrefix?: string;
}) {
  const query = toQuery({
    page: params?.page || 1,
    page_size: params?.pageSize || 50,
    status: params?.status,
    min_risk_score: params?.minRiskScore,
    transaction_id_prefix: params?.transactionIdPrefix,
  });
  return fetchJson<ListResponse<BackendAlert>>(`/alerts?${query}`);
}

export async function getAlert(alertId: string) {
  return fetchJson<BackendAlert>(`/alerts/${encodeURIComponent(alertId)}`);
}

export async function investigateAlert(alertId: string, hops = 2) {
  const query = toQuery({ hops });
  return fetchJson<InvestigationResponse>(`/alerts/${encodeURIComponent(alertId)}/investigate?${query}`);
}

export async function listStrReports(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  accountId?: string;
}) {
  const query = toQuery({
    page: params?.page || 1,
    page_size: params?.pageSize || 50,
    status: params?.status,
    account_id: params?.accountId,
  });
  return fetchJson<ListResponse<STRReport>>(`/reports/str?${query}`);
}

export async function generateStrReport(alertId: string, caseNotes = "") {
  return requestJson<STRGenerateResponse>("/reports/str/generate", {
    method: "POST",
    body: JSON.stringify({
      alert_id: alertId,
      case_notes: caseNotes,
    }),
  });
}

export async function submitStrReport(params: {
  strId: string;
  editedNarrative: string;
  digitalSignature: string;
}) {
  return requestJson<STRSubmitResponse>(`/reports/str/${encodeURIComponent(params.strId)}/submit`, {
    method: "POST",
    body: JSON.stringify({
      str_id: params.strId,
      edited_narrative: params.editedNarrative,
      digital_signature: params.digitalSignature,
    }),
  });
}

export async function ingestTransaction(payload: IngestTransactionRequest) {
  return requestJson<IngestTransactionResponse>("/transactions/ingest", {
    method: "POST",
    body: JSON.stringify({
      txn_id: payload.txnId,
      from_account: payload.fromAccount,
      to_account: payload.toAccount,
      amount: payload.amount,
      channel: payload.channel || "IMPS",
      customer_id: payload.customerId,
      description: payload.description || "Pipeline ingest",
      device_id: payload.deviceId,
      is_dormant: payload.isDormant || false,
      device_account_count: payload.deviceAccountCount || 1,
      velocity_1h: payload.velocity1h || 0,
      velocity_24h: payload.velocity24h || 0,
    }),
  });
}

export async function getBackendHealth() {
  return fetchAbsoluteJson<BackendHealthResponse>(`${API_BASE}/health`);
}

export async function getGraphAnalyticsStatus() {
  return fetchJson<GraphAnalyticsStatusResponse>("/graph-analytics/status");
}

export async function getMlHealth() {
  return fetchAbsoluteJson<MlHealthResponse>(`${ML_BASE}/api/v1/ml/health`);
}

export function connectAlertsWebSocket(
  investigatorId: string,
  onAlert: (alert: BackendAlert) => void,
  onState?: (connected: boolean) => void,
) {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/api/v1/ws/alerts/${encodeURIComponent(investigatorId)}`);

  ws.onopen = () => onState?.(true);
  ws.onclose = () => onState?.(false);
  ws.onerror = () => onState?.(false);
  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload?.type === "ALERT_FIRED" && payload.alert?.id) {
        onAlert(payload.alert as BackendAlert);
      }
    } catch {
      // Ignore malformed websocket payloads.
    }
  };

  return () => {
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
  };
}
