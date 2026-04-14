import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, AlertTriangle, Database, RefreshCw } from "lucide-react";
import {
  deriveFraudType,
  getBackendHealth,
  listAlerts,
  listTransactions,
  streamDataset,
  type BackendAlert,
  type DatasetKey,
} from "@/lib/unigraph-api";

function formatWhen(value?: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function TestCasesPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState("unknown");
  const [transactionCount, setTransactionCount] = useState(0);
  const [alerts, setAlerts] = useState<BackendAlert[]>([]);
  const [switchingDataset, setSwitchingDataset] = useState<DatasetKey | null>(null);
  const [switchSuccessMessage, setSwitchSuccessMessage] = useState<string | null>(null);
  const [switchErrorMessage, setSwitchErrorMessage] = useState<string | null>(null);

  const datasetSourceLabel = useMemo(() => {
    if (transactionCount === 100) return "dataset_100_interconnected_txns.sql";
    if (transactionCount === 200) return "dataset_200_interconnected_txns.sql";
    if (transactionCount === 0) return "No dataset loaded";
    return "Unknown/Custom dataset";
  }, [transactionCount]);

  const loadData = useCallback(async () => {
    try {
      const [health, txnResp, alertResp] = await Promise.all([
        getBackendHealth(),
        listTransactions({ page: 1, pageSize: 1 }),
        listAlerts({ page: 1, pageSize: 20 }),
      ]);

      setBackendStatus(health.status || "unknown");
      setTransactionCount(txnResp.total || txnResp.items.length);
      setAlerts(alertResp.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load pipeline status");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDatasetSwitch = useCallback(
    async (dataset: DatasetKey) => {
      setSwitchingDataset(dataset);
      setSwitchErrorMessage(null);
      setSwitchSuccessMessage(null);

      try {
        const response = await streamDataset(dataset);
        setSwitchSuccessMessage(
          `${response.message} (${response.totals.ingest_success} successful ingests).`,
        );
        await loadData();
      } catch (err) {
        setSwitchErrorMessage(
          err instanceof Error ? err.message : "Failed to switch dataset",
        );
      } finally {
        setSwitchingDataset(null);
      }
    },
    [loadData],
  );

  useEffect(() => {
    void loadData();
    const poller = setInterval(() => {
      void loadData();
    }, 15000);
    return () => clearInterval(poller);
  }, [loadData]);

  const stats = useMemo(
    () => [
      {
        label: "Dataset Source",
        value: datasetSourceLabel,
        sub: "Derived from live transaction count",
        icon: Database,
        tone: "text-info",
      },
      {
        label: "Transactions In Graph",
        value: String(transactionCount),
        sub: "From backend /transactions API",
        icon: Activity,
        tone: "text-primary",
      },
      {
        label: "Active Alerts",
        value: String(alerts.length),
        sub: "From backend /alerts API",
        icon: AlertTriangle,
        tone: "text-danger",
      },
      {
        label: "Backend Health",
        value: backendStatus.toUpperCase(),
        sub: "Live service status",
        icon: RefreshCw,
        tone: backendStatus === "healthy" ? "text-success" : "text-warning",
      },
    ],
    [datasetSourceLabel, transactionCount, alerts.length, backendStatus],
  );

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-primary">Pipeline Status (Real Data Only)</h1>
        <p className="text-xs text-muted-foreground mt-1">
          This page shows live backend outputs sourced from selected dataset ingestion.
        </p>
        {error && <p className="text-xs text-danger mt-1">{error}</p>}
        {switchSuccessMessage && (
          <p className="text-xs text-success mt-1">{switchSuccessMessage}</p>
        )}
        {switchErrorMessage && <p className="text-xs text-danger mt-1">{switchErrorMessage}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {stats.map((card) => (
          <div key={card.label} className="bg-card border border-border rounded-[10px] p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] text-muted-foreground uppercase tracking-wide font-semibold">{card.label}</div>
                <div className={`text-lg font-bold mt-1 ${card.tone}`}>{card.value}</div>
                <div className="text-[11px] text-muted-foreground mt-1">{card.sub}</div>
              </div>
              <card.icon className={`w-5 h-5 ${card.tone}`} />
            </div>
          </div>
        ))}
      </div>

      <div className="bg-card border border-border rounded-[10px] p-4">
        <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-2">Actions</div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => void handleDatasetSwitch("100")}
            disabled={Boolean(switchingDataset)}
            className="text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer disabled:cursor-not-allowed disabled:opacity-70"
          >
            {switchingDataset === "100" ? "Loading 100-row Dataset..." : "Load 100-row Dataset"}
          </button>
          <button
            onClick={() => void handleDatasetSwitch("200")}
            disabled={Boolean(switchingDataset)}
            className="text-xs px-3 py-2 rounded-md border border-border bg-card text-foreground hover:bg-muted cursor-pointer disabled:cursor-not-allowed disabled:opacity-70"
          >
            {switchingDataset === "200" ? "Loading 200-row Dataset..." : "Load 200-row Dataset"}
          </button>
          <button
            onClick={() => navigate("/alerts")}
            className="text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 cursor-pointer"
          >
            Open Alerts Queue
          </button>
          <button
            onClick={() => navigate("/transactions")}
            className="text-xs px-3 py-2 rounded-md border border-border bg-card text-foreground hover:bg-muted cursor-pointer"
          >
            Open Transaction Monitor
          </button>
          {alerts[0]?.id && (
            <button
              onClick={() => navigate(`/graph?alert=${encodeURIComponent(alerts[0].id)}`)}
              className="text-xs px-3 py-2 rounded-md border border-border bg-card text-foreground hover:bg-muted cursor-pointer"
            >
              Open Latest Graph Investigation
            </button>
          )}
        </div>
      </div>

      <div className="bg-card border border-border rounded-[10px] overflow-hidden">
        <div className="px-4 py-3 border-b border-border text-sm font-semibold text-foreground">Latest Backend Alerts</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-table-header text-table-header-foreground uppercase tracking-wide text-[11px] font-semibold">
                <th className="text-left p-2.5">Alert ID</th>
                <th className="text-left p-2.5">Account</th>
                <th className="text-left p-2.5">Fraud Type</th>
                <th className="text-center p-2.5">Risk</th>
                <th className="text-left p-2.5">Created</th>
                <th className="text-right p-2.5">Action</th>
              </tr>
            </thead>
            <tbody>
              {!loading && alerts.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-4 text-center text-muted-foreground text-sm">
                    No backend alerts available yet.
                  </td>
                </tr>
              )}
              {alerts.map((alert, idx) => (
                <tr key={`${alert.id}-${idx}`} className="border-b last:border-0 hover:bg-info/5">
                  <td className="p-2.5 font-mono text-primary font-semibold">{alert.id}</td>
                  <td className="p-2.5 font-mono">{alert.account_id}</td>
                  <td className="p-2.5">{deriveFraudType(alert.rule_flags || [], alert.primary_fraud_type)}</td>
                  <td className="p-2.5 text-center font-semibold">{Math.round(alert.risk_score || 0)}</td>
                  <td className="p-2.5 text-muted-foreground">{formatWhen(alert.created_at)}</td>
                  <td className="p-2.5 text-right">
                    <button
                      onClick={() => navigate(`/graph?alert=${encodeURIComponent(alert.id)}`)}
                      className="text-xs text-primary hover:underline cursor-pointer"
                    >
                      Investigate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
