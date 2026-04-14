import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Copy, Download, FileText, RefreshCw, Send } from "lucide-react";
import { toast } from "sonner";
import {
  generateStrReport,
  listAlerts,
  listStrReports,
  listTransactions,
  submitStrReport,
  toAlertCard,
  type AlertCardLike,
  type STRReport,
} from "@/lib/unigraph-api";

const reportTypes = ["STR", "CTR", "CBWTR", "NTR"];

function statusColor(status: string): string {
  const normalized = status.toUpperCase();
  if (normalized.includes("SUBMITTED") || normalized.includes("APPROVED")) return "hsl(var(--success))";
  if (normalized.includes("DRAFT") || normalized.includes("PENDING") || normalized.includes("QUEUED")) return "hsl(var(--warning))";
  return "hsl(var(--danger))";
}

function formatDate(value?: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("en-IN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export default function STRGenerator() {
  const [params] = useSearchParams();
  const alertParam = params.get("alert") || "";
  const txnPrefix = params.get("txnPrefix")?.trim() || "";

  const [alerts, setAlerts] = useState<AlertCardLike[]>([]);
  const [selectedAlert, setSelectedAlert] = useState("");
  const [history, setHistory] = useState<STRReport[]>([]);
  const [reportType, setReportType] = useState("STR");
  const [narrative, setNarrative] = useState("");
  const [strId, setStrId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeAlert = useMemo(
    () => alerts.find((alert) => alert.id === selectedAlert) || alerts[0],
    [alerts, selectedAlert],
  );

  const loadHistory = useCallback(async () => {
    try {
      const response = await listStrReports({ page: 1, pageSize: 100 });
      setHistory(response.items);
    } catch {
      // History is secondary data for this view.
    }
  }, []);

  const generateDraft = useCallback(
    async (alertId: string) => {
      if (!alertId) return;

      setGenerating(true);
      try {
        const response = await generateStrReport(alertId, "Generated from live investigator workflow");
        setNarrative(response.narrative || "");
        setStrId(response.str_id);
        toast.success(`Draft generated: ${response.str_id}`);
        await loadHistory();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to generate STR draft";
        toast.error(message);
      } finally {
        setGenerating(false);
      }
    },
    [loadHistory],
  );

  const loadLiveData = useCallback(async () => {
    setLoading(true);
    try {
      const [alertResp, txnResp] = await Promise.all([
        listAlerts({ page: 1, pageSize: 200, transactionIdPrefix: txnPrefix || undefined }),
        listTransactions({ page: 1, pageSize: 500, txnIdPrefix: txnPrefix || undefined }),
      ]);

      const txnById = new Map(txnResp.items.map((txn) => [txn.id, txn]));
      const mappedAlerts = alertResp.items.map((alert) => toAlertCard(alert, txnById.get(alert.transaction_id)));
      setAlerts(mappedAlerts);

      if (!mappedAlerts.length) {
        setSelectedAlert("");
        setNarrative("");
        setStrId("");
        setError("No live alerts found. Ingest a flagged transaction before generating STR.");
      } else {
        const preferredAlertId = mappedAlerts.some((alert) => alert.id === alertParam)
          ? alertParam
          : mappedAlerts[0].id;

        setSelectedAlert(preferredAlertId);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load live alerts");
    } finally {
      setLoading(false);
    }
  }, [alertParam, txnPrefix]);

  useEffect(() => {
    void loadLiveData();
    void loadHistory();
  }, [loadLiveData, loadHistory]);

  useEffect(() => {
    if (!selectedAlert) return;
    void generateDraft(selectedAlert);
  }, [selectedAlert, generateDraft]);

  const handleAlertChange = (id: string) => {
    setSelectedAlert(id);
    setNarrative("");
    setStrId("");
  };

  const handleSubmit = async () => {
    if (!strId || !narrative.trim()) {
      toast.error("Generate a draft before submitting");
      return;
    }

    setSubmitting(true);
    try {
      const response = await submitStrReport({
        strId,
        editedNarrative: narrative,
        digitalSignature: "investigator-digital-signature",
      });
      toast.success(`Submitted with reference ${response.reference_id}`);
      await loadHistory();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to submit STR");
    } finally {
      setSubmitting(false);
    }
  };

  const downloadBlob = useCallback((fileName: string, content: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, []);

  const handleDownloadXml = useCallback(() => {
    const xml = [
      "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
      "<strReport>",
      `  <reportType>${escapeXml(reportType)}</reportType>`,
      `  <strReference>${escapeXml(strId || "PENDING")}</strReference>`,
      `  <alertId>${escapeXml(activeAlert?.id || "")}</alertId>`,
      `  <accountId>${escapeXml(activeAlert?.account || "")}</accountId>`,
      `  <fraudType>${escapeXml(activeAlert?.fraudType || "")}</fraudType>`,
      `  <channel>${escapeXml(activeAlert?.channel || "")}</channel>`,
      `  <amount>${escapeXml(activeAlert?.amount || "")}</amount>`,
      `  <generatedAt>${escapeXml(new Date().toISOString())}</generatedAt>`,
      "  <narrative>",
      escapeXml(narrative || "No narrative available"),
      "  </narrative>",
      "</strReport>",
    ].join("\n");

    const reportToken = (strId || activeAlert?.id || "draft").replace(/[^a-zA-Z0-9_-]/g, "_");
    downloadBlob(`str-${reportToken}.xml`, xml, "application/xml;charset=utf-8");
    toast.success("XML exported");
  }, [activeAlert, downloadBlob, narrative, reportType, strId]);

  const handleDownloadPdf = useCallback(() => {
    const printWindow = window.open("", "_blank", "noopener,noreferrer,width=980,height=760");
    if (!printWindow) {
      toast.error("Enable pop-ups to export PDF");
      return;
    }

    const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>STR ${escapeHtml(strId || activeAlert?.id || "Draft")}</title>
    <style>
      body { font-family: Georgia, serif; margin: 28px; color: #111827; }
      h1 { margin: 0 0 8px; font-size: 20px; }
      .meta { margin-bottom: 16px; font-size: 12px; color: #374151; }
      .meta div { margin: 3px 0; }
      .section-title { margin: 18px 0 8px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
      .narrative { white-space: pre-wrap; line-height: 1.45; font-size: 13px; }
      @media print { body { margin: 16mm; } }
    </style>
  </head>
  <body>
    <h1>Suspicious Transaction Report</h1>
    <div class="meta">
      <div><strong>Report Type:</strong> ${escapeHtml(reportType)}</div>
      <div><strong>STR Reference:</strong> ${escapeHtml(strId || "Pending")}</div>
      <div><strong>Alert ID:</strong> ${escapeHtml(activeAlert?.id || "-")}</div>
      <div><strong>Account:</strong> ${escapeHtml(activeAlert?.account || "-")}</div>
      <div><strong>Amount:</strong> ${escapeHtml(activeAlert?.amount || "-")}</div>
      <div><strong>Channel:</strong> ${escapeHtml(activeAlert?.channel || "-")}</div>
      <div><strong>Generated At:</strong> ${escapeHtml(formatDate(new Date().toISOString()))}</div>
    </div>
    <div class="section-title">Grounds for Suspicion</div>
    <div class="narrative">${escapeHtml(narrative || "No narrative available")}</div>
  </body>
</html>`;

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
    toast.success("Print dialog opened. Choose Save as PDF");
  }, [activeAlert, narrative, reportType, strId]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-primary">STR Generator</h1>
        <p className="text-xs text-muted-foreground mt-1">
          Generate and submit FIU-IND aligned STRs from live alert data
          {txnPrefix ? ` · scope ${txnPrefix}` : ""}
        </p>
        {error && <p className="text-xs text-danger mt-1">{error}</p>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-9 gap-4 items-start">
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Case Selection</div>
            <select
              value={selectedAlert}
              onChange={(event) => handleAlertChange(event.target.value)}
              className="w-full bg-background border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer"
              disabled={loading || !alerts.length}
            >
              {!alerts.length && <option value="">No live alerts available</option>}
              {alerts.map((alert) => (
                <option key={alert.id} value={alert.id}>
                  {alert.id} - {alert.fraudType} - {alert.amount}
                </option>
              ))}
            </select>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Reporting Entity</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-muted-foreground">Bank Name</label>
                <input value="Unified Banking Intelligence" readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Branch Code</label>
                <input defaultValue="UBIN0531421" className="w-full bg-background border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Reporting Officer</label>
                <input value="Ajay Kumar" readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">STR Reference</label>
                <input value={strId || "Generate draft"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Suspicious Transaction Details</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-muted-foreground">Account Number</label>
                <input value={activeAlert?.account || "-"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Detected At</label>
                <input value={activeAlert?.timeDetected || "-"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Amount</label>
                <input value={activeAlert?.amount || "-"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-semibold text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Channel</label>
                <input value={activeAlert?.channel || "-"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div className="col-span-2">
                <label className="text-muted-foreground">Nature of Suspicion</label>
                <input value={activeAlert?.fraudType || "-"} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-foreground uppercase tracking-wide">LLM Narrative</div>
              <button
                onClick={() => selectedAlert && void generateDraft(selectedAlert)}
                disabled={generating || !selectedAlert}
                className="text-[10px] text-primary hover:underline flex items-center gap-1 cursor-pointer disabled:opacity-60"
              >
                <RefreshCw className="w-3 h-3" /> {generating ? "Generating..." : "Regenerate"}
              </button>
            </div>
            <textarea
              value={narrative}
              onChange={(event) => setNarrative(event.target.value)}
              className="w-full bg-background border border-border rounded-md p-3 text-xs leading-relaxed text-foreground min-h-[160px] outline-none resize-y focus:ring-1 focus:ring-primary"
              placeholder="Generate draft to populate narrative"
            />
            <div className="text-[10px] text-muted-foreground mt-1 text-right">{narrative.length} characters</div>
          </div>

          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Report Type</div>
            <div className="flex gap-2">
              {reportTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => setReportType(type)}
                  className={`flex-1 py-2 text-xs font-semibold rounded-md cursor-pointer ${reportType === type ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"}`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => void handleSubmit()}
            disabled={submitting || generating || !strId}
            className="w-full h-11 bg-primary text-primary-foreground rounded-lg text-sm font-bold flex items-center justify-center gap-2 cursor-pointer hover:bg-primary/90 disabled:opacity-60"
          >
            <Send className="w-4 h-4" />
            {submitting ? "Submitting..." : "Submit to FIU-IND"}
          </button>
          <p className="text-[10px] text-muted-foreground text-center">Submission requires generated draft and digital signature payload</p>
        </div>

        <div className="lg:col-span-5 space-y-4">
          <div className="bg-card border border-border rounded-[10px] overflow-hidden">
            <div className="border-b border-border px-5 py-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">Live Preview</span>
              <div className="flex gap-2">
                <button
                  onClick={handleDownloadXml}
                  className="text-[11px] border border-border rounded px-3 py-1.5 bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer">
                  <Download className="w-3 h-3" /> Download XML
                </button>
                <button
                  onClick={handleDownloadPdf}
                  className="text-[11px] border border-border rounded px-3 py-1.5 bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer">
                  <FileText className="w-3 h-3" /> Print / Save PDF
                </button>
                <button
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(narrative);
                      toast.success("Copied to clipboard");
                    } catch {
                      toast.error("Clipboard access blocked");
                    }
                  }}
                  className="text-[11px] border border-border rounded px-2 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
            <div className="p-5 max-h-[600px] overflow-y-auto scrollbar-thin">
              <div className="bg-muted/30 border border-border rounded-lg p-6 text-xs space-y-4">
                <div className="text-center border-b border-border pb-4">
                  <div className="text-sm font-bold text-primary tracking-wide">SUSPICIOUS TRANSACTION REPORT</div>
                  <div className="text-[10px] text-muted-foreground mt-1">Financial Intelligence Unit - India (FIU-IND)</div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div><span className="text-muted-foreground">STR Reference:</span> <span className="font-mono font-medium">{strId || "Pending"}</span></div>
                  <div><span className="text-muted-foreground">Date:</span> {formatDate(new Date().toISOString())}</div>
                  <div><span className="text-muted-foreground">Reporting Entity:</span> Unified Banking Intelligence</div>
                  <div><span className="text-muted-foreground">Officer:</span> Ajay Kumar</div>
                  <div><span className="text-muted-foreground">Case Reference:</span> <span className="font-mono">{activeAlert?.id || "-"}</span></div>
                  <div><span className="text-muted-foreground">Fraud Type:</span> {activeAlert?.fraudType || "-"}</div>
                </div>

                <div className="border-t border-border pt-3">
                  <div className="font-semibold text-foreground mb-2">Subject Account Details</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div><span className="text-muted-foreground">Account:</span> <span className="font-mono">{activeAlert?.account || "-"}</span></div>
                    <div><span className="text-muted-foreground">Amount:</span> <span className="font-semibold">{activeAlert?.amount || "-"}</span></div>
                    <div><span className="text-muted-foreground">Channel:</span> {activeAlert?.channel || "-"}</div>
                    <div><span className="text-muted-foreground">Risk Score:</span> {activeAlert?.riskScore ?? "-"}</div>
                  </div>
                </div>

                <div className="border-t border-border pt-3">
                  <div className="font-semibold text-foreground mb-2">Grounds for Suspicion</div>
                  <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">{narrative || "Generate draft to view live narrative"}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-[10px] overflow-hidden">
            <div className="px-5 py-3 border-b border-border">
              <span className="text-sm font-semibold text-foreground">Filed Reports History</span>
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-table-header text-table-header-foreground text-[11px] font-semibold tracking-wide uppercase">
                  <th className="text-left p-2.5">STR Reference</th>
                  <th className="text-left p-2.5">Alert ID</th>
                  <th className="text-left p-2.5">Submitted</th>
                  <th className="text-left p-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {!history.length && (
                  <tr>
                    <td className="p-3 text-muted-foreground" colSpan={4}>No STR history found</td>
                  </tr>
                )}
                {history.map((item, index) => (
                  <tr key={item.id || `${item.alert_id}-${index}`} className="border-b last:border-0" style={{ background: index % 2 === 1 ? "hsl(var(--table-stripe))" : undefined }}>
                    <td className="p-2.5 font-mono font-medium text-primary">{item.id}</td>
                    <td className="p-2.5 font-mono">{item.alert_id || "-"}</td>
                    <td className="p-2.5 text-muted-foreground">{formatDate(item.submitted_at || item.created_at)}</td>
                    <td className="p-2.5"><span className="font-semibold" style={{ color: statusColor(item.status || "DRAFT") }}>{item.status || "DRAFT"}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
