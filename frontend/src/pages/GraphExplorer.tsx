import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Download, FileText, Info } from "lucide-react";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import LiveGraph from "@/components/LiveGraph";
import { investigateAlert, type InvestigationResponse } from "@/lib/unigraph-api";
import { toast } from "sonner";

function prettifyFlag(flag: string): string {
  return flag
    .toLowerCase()
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function formatDate(value?: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatAmount(amount?: number): string {
  if (typeof amount !== "number" || Number.isNaN(amount)) return "N/A";
  return `INR ${Math.round(amount).toLocaleString("en-IN")}`;
}

export default function GraphExplorer() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const alertId = params.get("alert") || "";

  const [payload, setPayload] = useState<InvestigationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInvestigation = useCallback(async () => {
    if (!alertId) {
      setError("Missing alert id in URL");
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const data = await investigateAlert(alertId, 2);
      if ((data as unknown as { error?: string }).error) {
        throw new Error((data as unknown as { error: string }).error);
      }
      setPayload(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load investigation data");
    } finally {
      setLoading(false);
    }
  }, [alertId]);

  useEffect(() => {
    loadInvestigation();
  }, [loadInvestigation]);

  const model = useMemo(() => {
    if (!payload) return null;

    const alert = payload.alert;
    const transaction = payload.transaction;
    const riskScore = Math.round(alert.risk_score || 0);
    const ruleFlags = alert.rule_flags || [];
    const fraudType = ruleFlags.length ? prettifyFlag(ruleFlags[0]) : "Anomaly";

    const accounts = (payload.graph?.nodes || [])
      .map((node) => {
        const nodeId = String(node.id || "");
        if (!nodeId) return null;
        const labels = Array.isArray(node.labels) ? node.labels : [];
        return {
          id: nodeId,
          labels,
          riskScore: Math.round(Number(node.risk_score || 0)),
        };
      })
      .filter((node): node is NonNullable<typeof node> => Boolean(node));

    const reasons = (alert.shap_top3 || []).filter(Boolean);

    return {
      alert,
      transaction,
      riskScore,
      fraudType,
      accounts,
      reasons,
    };
  }, [payload]);

  const handleGenerateSTR = useCallback(() => {
    if (!alertId) return;
    navigate(`/str-generator?alert=${encodeURIComponent(alertId)}`);
  }, [alertId, navigate]);

  const handleExport = useCallback(() => {
    if (!payload) return;

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `investigation-${alertId || "alert"}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Evidence package exported");
  }, [payload, alertId]);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading live investigation data...</div>;
  }

  if (error || !model || !payload) {
    return (
      <div className="space-y-3">
        <h1 className="text-xl font-bold text-primary">Graph Investigation</h1>
        <p className="text-sm text-danger">{error || "Investigation payload unavailable"}</p>
        <button onClick={() => navigate("/alerts")} className="text-xs text-primary hover:underline flex items-center gap-1 cursor-pointer">
          <ArrowLeft className="w-3 h-3" /> Back to Alerts
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-primary">Graph Investigation</h1>
        <span className="bg-primary text-primary-foreground text-xs font-bold px-2.5 py-1 rounded">{model.alert.id}</span>
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded"
          style={{
            color: getRiskColor(model.riskScore),
            background: `${getRiskColor(model.riskScore)}15`,
          }}
        >
          {model.fraudType}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-10 gap-4">
        <div className="lg:col-span-3 space-y-3">
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Case Summary</div>
            <div className="text-xl font-bold text-primary mb-2">{model.alert.id}</div>
            <div className="flex items-center gap-2 mb-3">
              <span
                className="text-[11px] font-bold px-2 py-0.5 rounded"
                style={{
                  background: `${getRiskColor(model.riskScore)}15`,
                  color: getRiskColor(model.riskScore),
                }}
              >
                {getRiskLabel(model.riskScore)}
              </span>
              <span className="text-xs text-muted-foreground">{model.fraudType}</span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground w-20">Risk Score</span>
                <RiskScoreBar score={model.riskScore} size="md" />
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Amount</span>
                <span className="font-semibold">{formatAmount(model.transaction?.amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Channel</span>
                <span className="bg-muted text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">{model.transaction?.channel || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Detected</span>
                <span>{formatDate(model.alert.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-info/10 text-info">{model.alert.status || "OPEN"}</span>
              </div>
            </div>
            <button onClick={() => navigate("/alerts")} className="text-xs text-primary hover:underline mt-3 flex items-center gap-1 cursor-pointer">
              <ArrowLeft className="w-3 h-3" /> Back to Alerts
            </button>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Accounts Involved</div>
            <div className="space-y-2 max-h-[260px] overflow-y-auto">
              {model.accounts.map((acc) => (
                <div key={acc.id} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded hover:bg-muted/50">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: acc.id === model.alert.account_id ? "#2563EB" : "#334155" }} />
                  <span className="font-mono font-medium text-foreground">{acc.id}</span>
                  <span className="text-muted-foreground">{acc.labels.join(", ") || "Account"}</span>
                  <span className="ml-auto">
                    <RiskScoreBar score={acc.riskScore} size="sm" showBar={false} />
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <span className="text-xs font-semibold text-foreground uppercase tracking-wide">Why was this flagged?</span>
              <Info className="w-3.5 h-3.5 text-muted-foreground" />
            </div>
            <div className="space-y-1.5">
              {(model.reasons.length ? model.reasons : ["No SHAP reasons returned by backend"]).map((reason, index) => (
                <p key={`${reason}-${index}`} className="text-[11px] text-muted-foreground leading-relaxed">• {reason}</p>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-2">Investigator Note</div>
            <p className="text-[11px] text-muted-foreground leading-relaxed italic whitespace-pre-wrap">{payload.investigation_note || "No generated note available."}</p>
          </div>
        </div>

        <div className="lg:col-span-7 flex flex-col gap-3">
          <LiveGraph
            nodes={payload.graph?.nodes || []}
            edges={payload.graph?.edges || []}
            focusAccountId={model.alert.account_id}
          />

          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handleGenerateSTR}
              className="h-11 bg-primary text-primary-foreground rounded-lg text-sm font-bold flex items-center justify-center gap-2 cursor-pointer hover:bg-primary/90"
            >
              <FileText className="w-4 h-4" />
              Generate STR Report
            </button>
            <button
              onClick={handleExport}
              className="h-11 border border-border bg-card text-foreground rounded-lg text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer hover:bg-muted"
            >
              <Download className="w-4 h-4" />
              Export Evidence Package
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
