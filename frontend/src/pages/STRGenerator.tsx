import { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { alertCards } from "@/data/alerts-data";
import { FileText, Download, Send, Save, Copy, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const reportTypes = ["STR", "CTR", "CBWTR", "NTR"];

const narrativeTemplates: Record<string, string> = {
  "Rapid Layering": `On 08/03/2026, account XXXX4421 received ₹20,00,000 via a single NEFT transfer from an unrelated third-party source. Within 12 minutes, the funds were distributed across 4 accounts (XXXX7781, XXXX7782, XXXX7783, XXXX7784) in a pattern consistent with Rapid Layering typology under FATF ML-LAY-003. The velocity of 920% above the account's 90-day baseline, combined with all destination accounts being opened within the last 60 days with minimal KYC documentation, and 3 of 4 sharing the same device fingerprint, warrants immediate reporting under PMLA Section 12. The total exposure of ₹20,00,000 was fully dissipated within 2 hours of receipt, leaving no recoverable balance in any intermediate account.`,
  "Round-Tripping": `Between 01/03/2026 and 08/03/2026, a circular fund flow was detected involving Company A (XXXX1001), Company B, and Company C. ₹50,00,000 was transferred A→B via NEFT, then ₹48,00,000 B→C, and ₹46,00,000 C→A, completing a closed loop. All three entities share the same Ultimate Beneficial Owner and device fingerprint. The net fund leakage of ₹4,00,000 represents service fees. This pattern is consistent with FATF Typology ML-RT-002 (Round-Tripping for Revenue Inflation) and warrants reporting under PMLA Section 12.`,
  "Structuring/Smurfing": `On 08/03/2026, six different individuals made cash deposits of ₹49,000 each across 10 different branches, all converging into beneficiary account XXXX9999. Each deposit was deliberately structured below the ₹10,00,000 Currency Transaction Report threshold. Two depositors share the same mobile device fingerprint, suggesting coordinated activity. This pattern is consistent with FATF Typology ML-STR-001 (Structuring/Smurfing) and warrants immediate CTR and STR filing.`,
  "Dormant Activation": `Account XXXX2021, dormant since 2021 (3+ years), was reactivated on 08/03/2026 when it received ₹1,50,00,000 via RTGS from an external source. Within 6 hours, the entire amount was wired offshore via SWIFT to a foreign account. Access was from an unknown device never previously associated with this account, and KYC documentation is stale. This pattern warrants immediate reporting under PMLA Section 12.`,
  "Profile Mismatch": `Between 01/03/2026 and 08/03/2026, account XXXX1919 (registered to a 19-year-old student with zero declared income) received 50 business payments of ₹10,000 each per day from 3 corporate accounts across three states. The income-to-transaction ratio of 3167% far exceeds any reasonable explanation for a student savings account. This activity warrants enhanced due diligence and STR filing.`,
  "Mule Account": `Account XXXX5511, opened just 6 weeks ago with basic KYC, has been forwarding ₹5-8L overseas on a weekly basis with a turnaround time of under 2 hours. The account holder profile shows no business activity or trade documentation. This pattern is consistent with classic mule account recruitment and warrants immediate reporting and account freezing.`,
};

const historicalSTRs = [
  { ref: "STR-UBI-2024-0041", alertId: "ALT-2024-0790", date: "01/03/2026", status: "Accepted ✓" as const },
  { ref: "STR-UBI-2024-0040", alertId: "ALT-2024-0782", date: "28/02/2026", status: "Pending ⏳" as const },
  { ref: "STR-UBI-2024-0039", alertId: "ALT-2024-0775", date: "25/02/2026", status: "Accepted ✓" as const },
  { ref: "STR-UBI-2024-0038", alertId: "ALT-2024-0768", date: "22/02/2026", status: "Rejected ✗" as const },
  { ref: "STR-UBI-2024-0037", alertId: "ALT-2024-0755", date: "18/02/2026", status: "Accepted ✓" as const },
];

export default function STRGenerator() {
  const [params] = useSearchParams();
  const alertParam = params.get("alert") || "ALT-2024-0847";

  const [selectedAlert, setSelectedAlert] = useState(alertParam);
  const [reportType, setReportType] = useState("STR");
  const [submitting, setSubmitting] = useState(false);

  const alert = useMemo(() => alertCards.find(a => a.id === selectedAlert) || alertCards[0], [selectedAlert]);

  const getNarrative = (fraudType: string) => {
    return narrativeTemplates[fraudType] || narrativeTemplates["Rapid Layering"];
  };

  const [narrative, setNarrative] = useState(getNarrative(alert.fraudType));

  const handleAlertChange = (id: string) => {
    setSelectedAlert(id);
    const a = alertCards.find(x => x.id === id) || alertCards[0];
    setNarrative(getNarrative(a.fraudType));
  };

  const handleSubmit = () => {
    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      toast.success("STR submitted to FIU-IND via FINnet 2.0 successfully");
    }, 1500);
  };

  const statusColor = (s: string) => {
    if (s.includes("Accepted")) return "hsl(var(--success))";
    if (s.includes("Pending")) return "hsl(var(--warning))";
    return "hsl(var(--danger))";
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-primary">STR Generator</h1>
        <p className="text-xs text-muted-foreground mt-1">Auto-generate FIU-IND compliant Suspicious Transaction Reports</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-9 gap-4 items-start">
        {/* LEFT — Form */}
        <div className="lg:col-span-4 space-y-4">
          {/* Case Selection */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Case Selection</div>
            <select
              value={selectedAlert}
              onChange={(e) => handleAlertChange(e.target.value)}
              className="w-full bg-background border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer"
            >
              {alertCards.map(a => (
                <option key={a.id} value={a.id}>{a.id} — {a.fraudType} — {a.amount}</option>
              ))}
            </select>
          </div>

          {/* Reporting Entity */}
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
                <input value="STR-UBI-2026-00042" readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
              </div>
            </div>
          </div>

          {/* Transaction Details */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Suspicious Transaction Details</div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-muted-foreground">Account Number</label>
                <input value={alert.account} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Transaction Date</label>
                <input value={alert.timeDetected} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Amount (₹)</label>
                <input value={alert.amount} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-semibold text-foreground" />
              </div>
              <div>
                <label className="text-muted-foreground">Channel</label>
                <input value={alert.channel} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
              <div className="col-span-2">
                <label className="text-muted-foreground">Nature of Suspicion</label>
                <input value={alert.fraudType} readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
              </div>
            </div>
          </div>

          {/* Narrative */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-semibold text-foreground uppercase tracking-wide">AI-Generated Narrative (Qwen LLM)</div>
              <button
                onClick={() => { setNarrative(getNarrative(alert.fraudType)); toast.success("Narrative regenerated"); }}
                className="text-[10px] text-primary hover:underline flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" /> Regenerate
              </button>
            </div>
            <textarea
              value={narrative}
              onChange={(e) => setNarrative(e.target.value)}
              className="w-full bg-background border border-border rounded-md p-3 text-xs leading-relaxed text-foreground min-h-[160px] outline-none resize-y focus:ring-1 focus:ring-primary"
            />
            <div className="text-[10px] text-muted-foreground mt-1 text-right">{narrative.length} characters</div>
          </div>

          {/* Report Type */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Report Type</div>
            <div className="flex gap-2">
              {reportTypes.map(rt => (
                <button
                  key={rt}
                  onClick={() => setReportType(rt)}
                  className={`flex-1 py-2 text-xs font-semibold rounded-md cursor-pointer ${reportType === rt ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"}`}
                >
                  {rt}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full h-11 bg-primary text-primary-foreground rounded-lg text-sm font-bold flex items-center justify-center gap-2 cursor-pointer hover:bg-primary/90 disabled:opacity-60"
          >
            <Send className="w-4 h-4" />
            {submitting ? "Submitting..." : "Submit to FIU-IND via FINnet 2.0"}
          </button>
          <p className="text-[10px] text-muted-foreground text-center">Draft saved automatically · Last saved 2 min ago</p>
        </div>

        {/* RIGHT — Preview */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-card border border-border rounded-[10px] overflow-hidden">
            <div className="border-b border-border px-5 py-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-foreground">Live Preview</span>
              <div className="flex gap-2">
                <button onClick={() => toast.success("XML downloaded")} className="text-[11px] border border-border rounded px-3 py-1.5 bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer">
                  <Download className="w-3 h-3" /> Download XML
                </button>
                <button onClick={() => toast.success("PDF downloaded")} className="text-[11px] border border-border rounded px-3 py-1.5 bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer">
                  <FileText className="w-3 h-3" /> Download PDF
                </button>
                <button onClick={() => { navigator.clipboard.writeText(narrative); toast.success("Copied to clipboard"); }} className="text-[11px] border border-border rounded px-2 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer">
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
            <div className="p-5 max-h-[600px] overflow-y-auto scrollbar-thin">
              <div className="bg-muted/30 border border-border rounded-lg p-6 text-xs space-y-4">
                <div className="text-center border-b border-border pb-4">
                  <div className="text-sm font-bold text-primary tracking-wide">SUSPICIOUS TRANSACTION REPORT</div>
                  <div className="text-[10px] text-muted-foreground mt-1">Financial Intelligence Unit — India (FIU-IND)</div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div><span className="text-muted-foreground">STR Reference:</span> <span className="font-mono font-medium">STR-UBI-2026-00042</span></div>
                  <div><span className="text-muted-foreground">Date:</span> 08/03/2026</div>
                   <div><span className="text-muted-foreground">Reporting Entity:</span> Unified Banking Intelligence</div>
                  <div><span className="text-muted-foreground">Branch:</span> Mumbai Main</div>
                  <div><span className="text-muted-foreground">Officer:</span> Ajay Kumar</div>
                  <div><span className="text-muted-foreground">Report Type:</span> {reportType}</div>
                  <div><span className="text-muted-foreground">Case Reference:</span> <span className="font-mono">{alert.id}</span></div>
                  <div><span className="text-muted-foreground">Fraud Type:</span> {alert.fraudType}</div>
                </div>

                <div className="border-t border-border pt-3">
                  <div className="font-semibold text-foreground mb-2">Subject Account Details</div>
                  <div className="grid grid-cols-2 gap-2">
                    <div><span className="text-muted-foreground">Account:</span> <span className="font-mono">{alert.account}</span></div>
                    <div><span className="text-muted-foreground">Amount:</span> <span className="font-semibold">{alert.amount}</span></div>
                    <div><span className="text-muted-foreground">Channel:</span> {alert.channel}</div>
                    <div><span className="text-muted-foreground">KYC Status:</span> {alert.kycStatus}</div>
                  </div>
                </div>

                <div className="border-t border-border pt-3">
                  <div className="font-semibold text-foreground mb-2">Grounds for Suspicion</div>
                  <p className="text-muted-foreground leading-relaxed">{narrative}</p>
                </div>

                <div className="border-t border-border pt-3 text-[10px] text-muted-foreground">
                  <p>This report is filed in compliance with PMLA 2002, Section 12 & 13. Format: FIU-IND FINnet 2.0 XML.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Filed Reports History */}
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
                {historicalSTRs.map((s, i) => (
                  <tr key={s.ref} className="border-b last:border-0" style={{ background: i % 2 === 1 ? "hsl(var(--table-stripe))" : undefined }}>
                    <td className="p-2.5 font-mono font-medium text-primary">{s.ref}</td>
                    <td className="p-2.5 font-mono">{s.alertId}</td>
                    <td className="p-2.5 text-muted-foreground">{s.date}</td>
                    <td className="p-2.5">
                      <span className="font-semibold" style={{ color: statusColor(s.status) }}>{s.status}</span>
                    </td>
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
