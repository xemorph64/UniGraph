import type { Transaction } from "@/data/transactions";

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
}

export interface BackendAlert {
  id: string;
  transaction_id: string;
  account_id: string;
  risk_score: number;
  risk_level?: string;
  recommendation?: string;
  shap_top3?: string[];
  rule_flags?: string[];
  status?: string;
  created_at?: string;
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

const API_BASE = (import.meta.env.VITE_BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
const API_PREFIX = `${API_BASE}/api/v1`;

function toQuery(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`);
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

export function deriveFraudType(flags: string[]) {
  if (!flags.length) return "Anomaly";
  return prettifyFlag(flags[0]);
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
  };
}

export function toAlertCard(alert: BackendAlert, txn?: BackendTransaction): AlertCardLike {
  const flags = (alert.rule_flags || []).map(prettifyFlag);
  const type = deriveFraudType(alert.rule_flags || []);

  return {
    id: alert.id,
    fraudType: type,
    account: alert.account_id,
    amount: txn ? formatCurrency(txn.amount) : "N/A",
    riskScore: Math.round(alert.risk_score || 0),
    channel: txn?.channel || "-",
    timeDetected: formatTimestamp(alert.created_at),
    shapReason: (alert.shap_top3 || []).join(" + ") || "Pattern-based risk detection",
    description: alert.recommendation || `${type} signal triggered by risk engine`,
    recommendedAction: alert.recommendation || "Investigate alert",
    status: alert.status || "OPEN",
    transactionId: alert.transaction_id,
  };
}

export async function listTransactions(params?: {
  page?: number;
  pageSize?: number;
  channel?: string;
  minRiskScore?: number;
  accountId?: string;
}) {
  const query = toQuery({
    page: params?.page || 1,
    page_size: params?.pageSize || 50,
    channel: params?.channel,
    min_risk_score: params?.minRiskScore,
    account_id: params?.accountId,
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
}) {
  const query = toQuery({
    page: params?.page || 1,
    page_size: params?.pageSize || 50,
    status: params?.status,
    min_risk_score: params?.minRiskScore,
  });
  return fetchJson<ListResponse<BackendAlert>>(`/alerts?${query}`);
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
