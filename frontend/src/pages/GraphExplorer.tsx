import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Download, FileText, Info } from "lucide-react";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import LiveGraph from "@/components/LiveGraph";
import { investigateAlert, listAlerts, type InvestigationResponse } from "@/lib/unigraph-api";
import { formatImpactPoints, parseShapReasons } from "@/lib/shap-explain";
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
  const alertId = params.get("alert")?.trim() || "";
  const txnPrefix = params.get("txnPrefix")?.trim() || "";
  const [resolvedAlertId, setResolvedAlertId] = useState(alertId);

  const [payload, setPayload] = useState<InvestigationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const alertsPath = txnPrefix
    ? `/alerts?txnPrefix=${encodeURIComponent(txnPrefix)}`
    : "/alerts";

  const loadInvestigation = useCallback(async () => {
    setLoading(true);
    try {
      let targetAlertId = alertId;
      if (!targetAlertId) {
        const alertResp = await listAlerts({
          page: 1,
          pageSize: 1,
          transactionIdPrefix: txnPrefix || undefined,
        });
        targetAlertId = alertResp.items[0]?.id || "";

        if (!targetAlertId) {
          setPayload(null);
          setResolvedAlertId("");
          setError(
            txnPrefix
              ? `No alerts found for scope ${txnPrefix}.`
              : "No alerts available for investigation.",
          );
          return;
        }

        const nextParams = new URLSearchParams();
        nextParams.set("alert", targetAlertId);
        if (txnPrefix) {
          nextParams.set("txnPrefix", txnPrefix);
        }
        navigate(`/graph?${nextParams.toString()}`, { replace: true });
      }

      const data = await investigateAlert(targetAlertId, 2);
      if ((data as unknown as { error?: string }).error) {
        throw new Error((data as unknown as { error: string }).error);
      }
      setResolvedAlertId(targetAlertId);
      setPayload(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load investigation data");
    } finally {
      setLoading(false);
    }
  }, [alertId, navigate, txnPrefix]);

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

    const shapReasons = parseShapReasons(alert.shap_top3);
    const maxShapImpact = Math.max(
      1,
      ...shapReasons.map((reason) => (reason.impact === null ? 0 : Math.abs(reason.impact))),
    );
    const totalShapImpact = shapReasons.reduce((sum, reason) => sum + (reason.impact || 0), 0);

    return {
      alert,
      transaction,
      riskScore,
      fraudType,
      accounts,
      shapReasons,
      maxShapImpact,
      totalShapImpact,
    };
  }, [payload]);

  const handleGenerateSTR = useCallback(() => {
    if (!resolvedAlertId) return;
    const nextParams = new URLSearchParams();
    nextParams.set("alert", resolvedAlertId);
    if (txnPrefix) {
      nextParams.set("txnPrefix", txnPrefix);
    }
    navigate(`/str-generator?${nextParams.toString()}`);
  }, [navigate, resolvedAlertId, txnPrefix]);

  const handleExport = useCallback(() => {
    if (!payload) return;

    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `investigation-${resolvedAlertId || "alert"}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Evidence package exported");
  }, [payload, resolvedAlertId]);

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading live investigation data...</div>;
  }

  if (error || !model || !payload) {
    return (
      <div className="space-y-3">
        <h1 className="text-xl font-bold text-primary">Graph Investigation</h1>
        <p className="text-sm text-danger">{error || "Investigation payload unavailable"}</p>
        <button onClick={() => navigate(alertsPath)} className="text-xs text-primary hover:underline flex items-center gap-1 cursor-pointer">
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
            <button onClick={() => navigate(alertsPath)} className="text-xs text-primary hover:underline mt-3 flex items-center gap-1 cursor-pointer">
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
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-semibold text-foreground uppercase tracking-wide">SHAP Explanation</span>
                <Info className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
              {model.shapReasons.some((reason) => reason.impact !== null) && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-foreground font-semibold">
                  Total {formatImpactPoints(model.totalShapImpact)}
                </span>
              )}
            </div>
            <p className="text-[10px] text-muted-foreground mb-3">Top model drivers behind this alert score.</p>
            <div className="space-y-2">
              {(model.shapReasons.length
                ? model.shapReasons
                : [{ raw: "", driver: "No SHAP explanation returned by backend", impact: null, direction: "neutral" as const }]).map(
                (reason, index) => (
                  <div key={`${reason.raw || reason.driver}-${index}`} className="rounded-md border border-border/60 bg-muted/20 p-2.5">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[11px] text-foreground leading-relaxed">
                        <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-muted text-[10px] font-semibold mr-1.5">
                          {index + 1}
                        </span>
                        {reason.driver}
                      </p>
                      {reason.impact !== null && (
                        <span
                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${reason.direction === "increase" ? "bg-rose-100 text-rose-700" : "bg-sky-100 text-sky-700"}`}
                        >
                          {formatImpactPoints(reason.impact)}
                        </span>
                      )}
                    </div>

                    {reason.impact !== null && (
                      <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full ${reason.direction === "increase" ? "bg-rose-500" : "bg-sky-500"}`}
                          style={{ width: `${Math.max(12, (Math.abs(reason.impact) / model.maxShapImpact) * 100)}%` }}
                        />
                      </div>
                    )}

                    {reason.detail && <p className="mt-1 text-[10px] text-muted-foreground">{reason.detail}</p>}
                  </div>
                ),
              )}
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
