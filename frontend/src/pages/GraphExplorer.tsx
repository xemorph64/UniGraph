import { useSearchParams, useNavigate } from "react-router-dom";
import { useState, useCallback } from "react";
import { getFraudTypeForAlert } from "@/data/fraud-graphs";
import { alertCards } from "@/data/alerts-data";
import SimpleGraph from "@/components/SimpleGraph";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import { FileText, Download, ArrowLeft, Info, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { toast } from "sonner";

const fraudDescriptions: Record<string, string> = {
  "Rapid Layering": "₹20L was split from the source account into 4 intermediate mule accounts within 12 minutes via UPI and NEFT, then consolidated into a single destination account via RTGS.",
  "Round-Tripping": "₹50L was cycled through 5 shell company accounts in a closed loop within 6 hours. All companies share the same UBO and device fingerprint.",
  "Structuring/Smurfing": "6 different depositors made cash deposits of just under ₹10L each into the same beneficiary account across different branches on the same day.",
  "Dormant Activation": "A dormant account (inactive 3 years) received ₹1.5Cr via RTGS and immediately transferred it offshore via SWIFT. Access was from an unknown device.",
  "Profile Mismatch": "A student savings account received ₹15L from 3 corporate accounts via repeated UPI micro-transactions. The student's KYC shows minimal income.",
  "Mule Account": "4 mule accounts (young individuals with basic KYC) received funds from separate sources and consolidated them into a hub account, which then transferred ₹45L overseas via SWIFT.",
};

const shapData: Record<string, { feature: string; direction: "up" | "down"; value: number; detail: string }[]> = {
  "Rapid Layering": [
    { feature: "Receiver account age", direction: "up", value: 18.4, detail: "45 days" },
    { feature: "Unique senders in 24hr", direction: "up", value: 14.2, detail: "18 senders" },
    { feature: "Same community cluster", direction: "up", value: 11.7, detail: "Graph connected" },
    { feature: "Device risk score", direction: "down", value: 6.3, detail: "Score: 8" },
    { feature: "Account KYC verified", direction: "down", value: 4.1, detail: "Verified" },
  ],
  "Round-Tripping": [
    { feature: "Cycle detection", direction: "up", value: 22.1, detail: "3-hop cycle" },
    { feature: "Same UBO", direction: "up", value: 16.8, detail: "Shared owner" },
    { feature: "Net flow ≈ 0", direction: "up", value: 12.5, detail: "₹4L leakage" },
    { feature: "Historical relationship", direction: "down", value: 5.2, detail: "Known partners" },
    { feature: "Business justification", direction: "down", value: 3.8, detail: "Invoice present" },
  ],
  "Structuring/Smurfing": [
    { feature: "Sub-threshold pattern", direction: "up", value: 20.3, detail: "All <₹10L" },
    { feature: "Fan-in ratio", direction: "up", value: 15.6, detail: "6:1 ratio" },
    { feature: "Same-day timing", direction: "up", value: 13.1, detail: "Within 4 hrs" },
    { feature: "Branch diversity", direction: "down", value: 4.7, detail: "5 branches" },
    { feature: "KYC walk-in", direction: "down", value: 3.9, detail: "Walk-in deposit" },
  ],
  "Dormant Activation": [
    { feature: "Dormancy period", direction: "up", value: 24.5, detail: "3+ years" },
    { feature: "Spike magnitude", direction: "up", value: 19.2, detail: "5600% spike" },
    { feature: "Immediate outflow", direction: "up", value: 14.8, detail: "<6 hrs" },
    { feature: "Unknown device", direction: "up", value: 8.1, detail: "New device" },
    { feature: "Account standing", direction: "down", value: 5.4, detail: "Good history" },
  ],
  "Profile Mismatch": [
    { feature: "Income ratio", direction: "up", value: 21.7, detail: "3167% anomaly" },
    { feature: "Transaction volume", direction: "up", value: 16.3, detail: "50 txn/day" },
    { feature: "Source diversity", direction: "up", value: 12.9, detail: "3 corps" },
    { feature: "KYC verified", direction: "down", value: 6.8, detail: "Student KYC" },
    { feature: "Account age", direction: "down", value: 4.2, detail: "2 years" },
  ],
  "Mule Account": [
    { feature: "Account age", direction: "up", value: 19.8, detail: "6 weeks" },
    { feature: "Forwarding speed", direction: "up", value: 17.4, detail: "<2 hrs" },
    { feature: "Overseas destination", direction: "up", value: 14.1, detail: "SWIFT exit" },
    { feature: "Fan-in pattern", direction: "up", value: 10.3, detail: "23:1 ratio" },
    { feature: "Trade documentation", direction: "down", value: 5.6, detail: "None" },
  ],
};

const accountRoles: Record<string, { accounts: { id: string; role: string; color: string; riskScore: number }[] }> = {
  "Rapid Layering": {
    accounts: [
      { id: "ACC001", role: "Source", color: "hsl(0, 72%, 51%)", riskScore: 96 },
      { id: "ACC002", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 88 },
      { id: "ACC003", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 85 },
      { id: "ACC004", role: "Mule", color: "hsl(32, 95%, 44%)", riskScore: 90 },
      { id: "ACC005", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 78 },
      { id: "ACC009", role: "Destination", color: "hsl(263, 70%, 50%)", riskScore: 95 },
    ],
  },
  "Round-Tripping": {
    accounts: [
      { id: "COMP-A", role: "Source", color: "hsl(0, 72%, 51%)", riskScore: 92 },
      { id: "COMP-B", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 88 },
      { id: "COMP-C", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 86 },
      { id: "UBO-001", role: "Mule", color: "hsl(32, 95%, 44%)", riskScore: 95 },
    ],
  },
  "Structuring/Smurfing": {
    accounts: [
      { id: "DEP-01", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 80 },
      { id: "DEP-02", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 78 },
      { id: "DEP-03", role: "Mule", color: "hsl(32, 95%, 44%)", riskScore: 85 },
      { id: "ACC-X", role: "Destination", color: "hsl(263, 70%, 50%)", riskScore: 95 },
    ],
  },
  "Dormant Activation": {
    accounts: [
      { id: "EXT-SRC", role: "Source", color: "hsl(0, 72%, 51%)", riskScore: 60 },
      { id: "DORM-01", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 96 },
      { id: "OFF-01", role: "Destination", color: "hsl(263, 70%, 50%)", riskScore: 90 },
    ],
  },
  "Profile Mismatch": {
    accounts: [
      { id: "CORP-01", role: "Source", color: "hsl(0, 72%, 51%)", riskScore: 40 },
      { id: "STUDENT", role: "Suspicious", color: "hsl(25, 95%, 53%)", riskScore: 94 },
      { id: "HAWALA", role: "Destination", color: "hsl(263, 70%, 50%)", riskScore: 88 },
    ],
  },
  "Mule Account": {
    accounts: [
      { id: "SRC-01", role: "Source", color: "hsl(0, 72%, 51%)", riskScore: 30 },
      { id: "MULE-01", role: "Mule", color: "hsl(32, 95%, 44%)", riskScore: 85 },
      { id: "MULE-02", role: "Mule", color: "hsl(32, 95%, 44%)", riskScore: 82 },
      { id: "OVERSEAS", role: "Destination", color: "hsl(263, 70%, 50%)", riskScore: 88 },
    ],
  },
};

const shapBullets: Record<string, string[]> = {
  "Rapid Layering": [
    "The account received a large sum and immediately split it into multiple smaller transfers — a classic layering pattern.",
    "3 out of 4 destination accounts share the same device fingerprint, suggesting coordinated mule operation.",
    "Transaction velocity exceeded 890% of the 90-day baseline, far above normal thresholds.",
  ],
  "Round-Tripping": [
    "Funds completed a full cycle A→B→C→A with minimal leakage, indicating artificial inflation of revenue.",
    "All three companies share the same Ultimate Beneficial Owner and registered address.",
    "The entire cycle completed within 6 hours, inconsistent with legitimate business flows.",
  ],
  "Structuring/Smurfing": [
    "Multiple depositors each deposited just below the ₹10L reporting threshold, suggesting deliberate avoidance.",
    "All deposits converged into a single beneficiary account on the same day across multiple branches.",
    "Two depositors share the same mobile device fingerprint, linking them as potential coordinators.",
  ],
  "Dormant Activation": [
    "An account dormant for 3+ years suddenly received a ₹1.5Cr transfer and immediately sent it offshore.",
    "Access was from an unknown device never previously associated with this account.",
    "The KYC documentation is stale and has not been updated since account opening.",
  ],
  "Profile Mismatch": [
    "A student with minimal declared income received over ₹15L from corporate accounts in daily micro-transactions.",
    "The income-to-transaction ratio is 3167% — far exceeding any reasonable explanation.",
    "The receiving pattern (50 × ₹10K UPI per day) is inconsistent with personal use or student activity.",
  ],
  "Mule Account": [
    "Multiple newly opened accounts with basic KYC received funds and immediately forwarded them to a hub account.",
    "The hub account then consolidated all funds and transferred ₹45L overseas via SWIFT.",
    "All mule accounts were opened within the same 2-week window at the same branch.",
  ],
};

export default function GraphExplorer() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const alertId = params.get("alert") || "ALT-2024-0847";

  const alertCard = alertCards.find((a) => a.id === alertId);
  const defaultFraudType = getFraudTypeForAlert(alertId);
  const [activeFraudType, setActiveFraudType] = useState(defaultFraudType);

  const [generatingSTR, setGeneratingSTR] = useState(false);
  const [generatingExport, setGeneratingExport] = useState(false);

  const handleGenerateSTR = useCallback(() => {
    setGeneratingSTR(true);
    setTimeout(() => {
      setGeneratingSTR(false);
      navigate(`/str-generator?alert=${alertId}`);
      toast.success("Navigating to STR Generator with case pre-filled");
    }, 1500);
  }, [alertId, navigate]);

  const handleExport = useCallback(() => {
    setGeneratingExport(true);
    setTimeout(() => {
      setGeneratingExport(false);
      toast.success("Evidence package exported successfully");
    }, 1500);
  }, []);

  const riskScore = alertCard?.riskScore || 94;
  const description = fraudDescriptions[activeFraudType] || `Alert ${alertId} flagged for ${activeFraudType} pattern.`;
  const shap = shapData[activeFraudType] || shapData["Rapid Layering"];
  const accounts = accountRoles[activeFraudType]?.accounts || [];
  const bullets = shapBullets[activeFraudType] || [];
  const maxShapValue = Math.max(...shap.map(s => s.value));

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl font-bold text-primary">Graph Investigation</h1>
        <span className="bg-primary text-primary-foreground text-xs font-bold px-2.5 py-1 rounded">{alertId}</span>
        <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{
          color: getRiskColor(riskScore),
          background: `${getRiskColor(riskScore)}15`,
        }}>
          {activeFraudType}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-10 gap-4">
        {/* LEFT PANEL */}
        <div className="lg:col-span-3 space-y-3">
          {/* Case Summary */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Case Summary</div>
            <div className="text-xl font-bold text-primary mb-2">{alertId}</div>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[11px] font-bold px-2 py-0.5 rounded" style={{
                background: `${getRiskColor(riskScore)}15`,
                color: getRiskColor(riskScore),
              }}>
                {getRiskLabel(riskScore)}
              </span>
              <span className="text-xs text-muted-foreground">{activeFraudType}</span>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground w-20">Risk Score</span>
                <RiskScoreBar score={riskScore} size="md" />
              </div>
              <div className="flex justify-between"><span className="text-muted-foreground">Amount</span><span className="font-semibold">{alertCard?.amount || "₹20,00,000"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Channel</span><span className="bg-muted text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">{alertCard?.channel || "UPI"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Detected</span><span>{alertCard?.timeDetected || "08/03/2026"}</span></div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-info/10 text-info">OPEN</span>
              </div>
            </div>
            <button onClick={() => navigate("/alerts")} className="text-xs text-primary hover:underline mt-3 flex items-center gap-1 cursor-pointer">
              <ArrowLeft className="w-3 h-3" /> Back to Alerts
            </button>
          </div>

          {/* Accounts Involved */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-3">Accounts Involved</div>
            <div className="space-y-2">
              {accounts.map((acc) => (
                <div key={acc.id} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded hover:bg-muted/50 cursor-pointer">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: acc.color }} />
                  <span className="font-mono font-medium text-foreground">{acc.id}</span>
                  <span className="text-muted-foreground">{acc.role}</span>
                  <span className="ml-auto">
                    <RiskScoreBar score={acc.riskScore} size="sm" showBar={false} />
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* SHAP Explanation */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="flex items-center gap-1.5 mb-3">
              <span className="text-xs font-semibold text-foreground uppercase tracking-wide">Why was this flagged?</span>
              <Info className="w-3.5 h-3.5 text-muted-foreground" />
            </div>
            <div className="space-y-2.5">
              {shap.map((s) => (
                <div key={s.feature} className="space-y-0.5">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-foreground font-medium">{s.feature}: {s.detail}</span>
                    <span className={`font-semibold ${s.direction === "up" ? "text-danger" : "text-success"}`}>
                      {s.direction === "up" ? "↑" : "↓"} {s.direction === "up" ? "+" : "-"}{s.value} pts
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(s.value / maxShapValue) * 100}%`,
                        background: s.direction === "up" ? "hsl(var(--danger))" : "hsl(var(--success))",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 space-y-1.5">
              {bullets.map((b, i) => (
                <p key={i} className="text-[11px] text-muted-foreground leading-relaxed">• {b}</p>
              ))}
            </div>
          </div>

          {/* What Happened */}
          <div className="bg-card border border-border rounded-[10px] p-4">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-2">What Happened</div>
            <p className="text-[11px] text-muted-foreground leading-relaxed italic">{description}</p>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="lg:col-span-7 flex flex-col gap-3">
          <SimpleGraph activeFraudType={activeFraudType} onFraudTypeChange={setActiveFraudType} />

          {/* Action Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handleGenerateSTR}
              disabled={generatingSTR}
              className="h-11 bg-primary text-primary-foreground rounded-lg text-sm font-bold flex items-center justify-center gap-2 cursor-pointer hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <FileText className="w-4 h-4" />
              {generatingSTR ? "Compiling..." : "Generate STR Report"}
            </button>
            <button
              onClick={handleExport}
              disabled={generatingExport}
              className="h-11 border border-border bg-card text-foreground rounded-lg text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer hover:bg-muted disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              {generatingExport ? "Exporting..." : "Export Evidence Package"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
