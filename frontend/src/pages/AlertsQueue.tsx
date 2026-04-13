import { useState, useMemo, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Search, ArrowRight } from "lucide-react";
import RiskScoreBar, { getRiskColor } from "@/components/RiskScoreBar";
import {
  connectAlertsWebSocket,
  getTransaction,
  listAlerts,
  listTransactions,
  toAlertCard,
  type AlertCardLike,
} from "@/lib/unigraph-api";

type Priority = "CRITICAL" | "HIGH" | "MEDIUM";
type StatusType = "OPEN" | "UNDER REVIEW" | "STR FILED";

interface AlertItem {
  id: string;
  account: string;
  fraudType: string;
  amount: string;
  channel: string;
  date: string;
  description: string;
  priority: Priority;
  riskScore: number;
  status: StatusType;
  strDeadlineDays: number;
  scoringSource?: string;
  modelVersion?: string;
}

function formatScoringSource(value?: string) {
  if (value === "ml_blended") return "ML Blended";
  if (value === "rules_fallback") return "Rules Fallback";
  return "Unknown";
}

function scoringSourceClass(value?: string) {
  if (value === "ml_blended") return "bg-success/15 text-success border-success/30";
  if (value === "rules_fallback") return "bg-warning/20 text-warning border-warning/30";
  return "bg-muted text-muted-foreground border-border";
}

function getPriority(score: number): Priority {
  if (score >= 90) return "CRITICAL";
  if (score >= 80) return "HIGH";
  return "MEDIUM";
}

function mapBackendStatus(status?: string): StatusType {
  if (!status || status === "OPEN") return "OPEN";
  if (status === "INVESTIGATING" || status === "ESCALATED") return "UNDER REVIEW";
  if (status === "FILED" || status === "CLOSED") return "STR FILED";
  return "UNDER REVIEW";
}

function toAlertItem(
  card: AlertCardLike,
  index: number,
  scoringSource?: string,
  modelVersion?: string,
): AlertItem {
  return {
    id: card.id,
    account: card.account,
    fraudType: card.fraudType,
    amount: card.amount,
    channel: card.channel,
    date: card.timeDetected.split(" ")[0] || "-",
    description: card.description,
    priority: getPriority(card.riskScore),
    riskScore: card.riskScore,
    status: mapBackendStatus(card.status),
    strDeadlineDays: Math.max(1, 10 - index),
    scoringSource,
    modelVersion,
  };
}

const priorityBorder: Record<Priority, string> = {
  CRITICAL: "border-l-[3px] border-l-risk-critical",
  HIGH: "border-l-[3px] border-l-warning",
  MEDIUM: "border-l-[3px] border-l-info",
};

const priorityBadgeStyle: Record<Priority, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "hsl(0, 86%, 97%)", text: "hsl(0, 72%, 51%)", border: "hsl(0, 93%, 94%)" },
  HIGH: { bg: "hsl(48, 96%, 89%)", text: "hsl(32, 95%, 44%)", border: "hsl(48, 96%, 89%)" },
  MEDIUM: { bg: "hsl(214, 95%, 93%)", text: "hsl(217, 91%, 60%)", border: "hsl(213, 94%, 87%)" },
};

const statusColors: Record<StatusType, string> = {
  OPEN: "hsl(var(--info))",
  "UNDER REVIEW": "hsl(var(--warning))",
  "STR FILED": "hsl(var(--success))",
};

const fraudTypeColors: Record<string, string> = {
  "Rapid Layering": "hsl(0, 72%, 51%)",
  "Round-Tripping": "hsl(263, 70%, 50%)",
  Structuring: "hsl(188, 86%, 40%)",
  "Dormant Account Awakening": "hsl(32, 95%, 44%)",
  "Mule Account Network": "hsl(var(--danger))",
  Anomaly: "hsl(160, 84%, 29%)",
};

type TabKey = "all" | "CRITICAL" | "HIGH" | "MEDIUM";

const fraudTypes = [
  "All Types",
  "Rapid Layering",
  "Round-Tripping",
  "Structuring",
  "Dormant Account Awakening",
  "Mule Account Network",
  "Anomaly",
];

export default function AlertsQueue() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const txnPrefix = searchParams.get("txnPrefix")?.trim() || "";
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("all");
  const [sortBy, setSortBy] = useState("date");
  const [typeFilter, setTypeFilter] = useState("All Types");

  const loadAlerts = useCallback(async () => {
    try {
      const [alertResp, txnResp] = await Promise.all([
        listAlerts({
          page: 1,
          pageSize: 200,
          transactionIdPrefix: txnPrefix || undefined,
        }),
        listTransactions({
          page: 1,
          pageSize: 500,
          txnIdPrefix: txnPrefix || undefined,
        }),
      ]);

      const txnById = new Map(txnResp.items.map((txn) => [txn.id, txn]));
      const mapped = alertResp.items.map((alert, index) => {
        const txn = txnById.get(alert.transaction_id);
        const card = toAlertCard(alert, txn);
        return toAlertItem(card, index, txn?.scoring_source, txn?.model_version);
      });
      setAlerts(mapped);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [txnPrefix]);

  useEffect(() => {
    loadAlerts();
    const poller = setInterval(loadAlerts, 15000);
    return () => clearInterval(poller);
  }, [loadAlerts]);

  useEffect(() => {
    const disconnect = connectAlertsWebSocket(
      "alerts-queue-ui",
      async (incomingAlert) => {
        if (txnPrefix) {
          const transactionId = incomingAlert.transaction_id || "";
          if (!transactionId.startsWith(txnPrefix)) {
            return;
          }
        }
        try {
          const txn = incomingAlert.transaction_id ? await getTransaction(incomingAlert.transaction_id) : undefined;
          const item = toAlertItem(toAlertCard(incomingAlert, txn), 0, txn?.scoring_source, txn?.model_version);
          setAlerts((prev) => [item, ...prev.filter((a) => a.id !== item.id)]);
        } catch {
          const item = toAlertItem(toAlertCard(incomingAlert), 0);
          setAlerts((prev) => [item, ...prev.filter((a) => a.id !== item.id)]);
        }
      },
      setWsConnected,
    );

    return disconnect;
  }, [txnPrefix]);

  const counts = useMemo(() => ({
    all: alerts.length,
    CRITICAL: alerts.filter(a => a.priority === "CRITICAL").length,
    HIGH: alerts.filter(a => a.priority === "HIGH").length,
    MEDIUM: alerts.filter(a => a.priority === "MEDIUM").length,
  }), [alerts]);

  const filtered = useMemo(() => {
    let result = alerts.filter((a) => {
      if (activeTab !== "all" && a.priority !== activeTab) return false;
      if (typeFilter !== "All Types" && a.fraudType !== typeFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!a.id.toLowerCase().includes(q) && !a.account.toLowerCase().includes(q)) return false;
      }
      return true;
    });
    if (sortBy === "risk") result = [...result].sort((a, b) => b.riskScore - a.riskScore);
    if (sortBy === "date") result = [...result].sort((a, b) => b.id.localeCompare(a.id));
    return result;
  }, [search, activeTab, typeFilter, sortBy]);

  const criticalCount = counts.CRITICAL;
  const highCount = counts.HIGH;

  const tabs: { key: TabKey; label: string; dot?: string }[] = [
    { key: "all", label: `All (${counts.all})` },
    { key: "CRITICAL", label: `Critical (${counts.CRITICAL})`, dot: "bg-risk-critical" },
    { key: "HIGH", label: `High (${counts.HIGH})`, dot: "bg-warning" },
    { key: "MEDIUM", label: `Medium (${counts.MEDIUM})`, dot: "bg-info" },
  ];

  return (
    <div className="space-y-4">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-primary">Alerts & Cases</h1>
        <p className="text-xs text-muted-foreground mt-1">
          {counts.all} alerts require attention · {criticalCount} critical · {highCount} high · {wsConnected ? "live" : "polling"}
          {txnPrefix ? ` · scope ${txnPrefix}` : ""}
        </p>
        {error && <p className="text-xs text-danger mt-1">{error}</p>}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-card border border-border rounded-[10px] p-3 text-center">
          <div className="text-2xl font-bold text-foreground">{counts.all}</div>
          <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Total Active</div>
        </div>
        <div className="bg-card border border-border rounded-[10px] p-3 text-center">
          <div className="text-2xl font-bold" style={{ color: "hsl(0, 72%, 51%)" }}>{criticalCount}</div>
          <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">Critical</div>
        </div>
        <div className="bg-card border border-border rounded-[10px] p-3 text-center">
          <div className="text-2xl font-bold text-warning">{highCount}</div>
          <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">High</div>
        </div>
        <div className="bg-card border border-border rounded-[10px] p-3 text-center">
          <div className="text-2xl font-bold text-danger animate-pulse-dot">
            {alerts.filter(a => a.strDeadlineDays <= 7).length}
          </div>
          <div className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">STR Deadline {"<"}7 days</div>
        </div>
      </div>

      {/* Tabs + Filters */}
      <div className="space-y-3">
        <div className="border-b border-border flex gap-0 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-5 py-2.5 text-[13px] cursor-pointer flex items-center gap-1.5 border-b-2 whitespace-nowrap ${
                activeTab === t.key
                  ? "font-semibold text-primary border-primary"
                  : "font-normal text-muted-foreground border-transparent hover:text-foreground"
              }`}
            >
              {t.dot && <span className={`w-2 h-2 rounded-full ${t.dot}`} />}
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by Alert ID or Account Number"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-card border border-border rounded-md py-2 pl-9 pr-3 text-[13px] text-foreground outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-card border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer"
          >
            <option value="date">Sort by: Date ↓</option>
            <option value="risk">Sort by: Risk Score ↓</option>
          </select>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-card border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer"
          >
            {fraudTypes.map((ft) => (
              <option key={ft} value={ft}>{ft}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Alert Cards */}
      <div className="flex flex-col gap-2">
        {!loading && filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">No alerts match your filters</div>
        )}
        {filtered.map((a) => {
          const pStyle = priorityBadgeStyle[a.priority];
          return (
            <div
              key={a.id}
              className={`bg-card border border-border rounded-lg p-4 relative ${priorityBorder[a.priority]}`}
            >
              {/* Status badge */}
              <span
                className="absolute top-3 right-3 text-[10px] font-bold px-2 py-0.5 rounded"
                style={{
                  color: statusColors[a.status],
                  background: `${statusColors[a.status]}15`,
                  border: `1px solid ${statusColors[a.status]}30`,
                }}
              >
                {a.status}
              </span>

              {/* Row 1 */}
              <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                <span
                  className="text-[11px] font-semibold px-2 py-0.5 rounded"
                  style={{ background: pStyle.bg, color: pStyle.text, border: `1px solid ${pStyle.border}` }}
                >
                  {a.priority}
                </span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${scoringSourceClass(a.scoringSource)}`}>
                  {formatScoringSource(a.scoringSource)}
                </span>
                <span className="text-primary font-bold text-sm">{a.id}</span>
                <span className="ml-auto mr-20 text-[11px] font-semibold px-2 py-0.5 rounded" style={{
                  color: fraudTypeColors[a.fraudType] || "hsl(var(--foreground))",
                  background: `${fraudTypeColors[a.fraudType] || "hsl(var(--muted))"}12`,
                }}>
                  {a.fraudType}
                </span>
              </div>

              {/* Row 2 */}
              <div className="text-[13px] text-foreground mb-1.5 flex items-center gap-3 flex-wrap">
                <span className="font-mono">Account {a.account}</span>
                <span>·</span>
                <span className="font-semibold">{a.amount}</span>
                <span>·</span>
                <span className="bg-muted text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">{a.channel}</span>
                <span>·</span>
                <span className="text-muted-foreground text-xs">{a.date}</span>
                <span>·</span>
                <span className="text-xs flex items-center gap-1">
                  Risk Score: <RiskScoreBar score={a.riskScore} size="sm" showBar={false} />
                </span>
              </div>

              {/* Row 3 */}
              <div className="flex items-center justify-between gap-4">
                <div className="max-w-[60%]">
                  <span className="text-muted-foreground text-xs italic truncate block">{a.description}</span>
                  {a.modelVersion && (
                    <span className="text-[11px] text-muted-foreground truncate block" title={a.modelVersion}>
                      Model: {a.modelVersion}
                    </span>
                  )}
                </div>

                {/* STR Deadline */}
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded whitespace-nowrap ${a.strDeadlineDays <= 3 ? "animate-pulse-dot" : ""}`}
                  style={{
                    color: a.status === "STR FILED" ? "hsl(var(--success))" : a.strDeadlineDays <= 3 ? "hsl(var(--danger))" : "hsl(var(--warning))",
                    background: a.status === "STR FILED" ? "hsl(149, 80%, 90%)" : a.strDeadlineDays <= 3 ? "hsl(0, 86%, 97%)" : "hsl(48, 96%, 89%)",
                  }}
                >
                  {a.status === "STR FILED" ? "Filed ✓" : `${a.strDeadlineDays} days left`}
                </span>

                <button
                  onClick={() => navigate(`/graph?alert=${a.id}`)}
                  className="bg-primary text-primary-foreground rounded-md px-4 py-1.5 text-xs font-semibold cursor-pointer hover:bg-primary/90 flex items-center gap-1 shrink-0"
                >
                  Investigate <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
