import React, { useState, useEffect } from "react";
import { 
  Filter, 
  TrendingUp, 
  Zap, 
  AlertCircle, 
  ChevronRight, 
  ChevronLeft,
  Expand,
  Shrink,
  Brain,
  PauseCircle,
  ShieldAlert,
  Gavel,
  Bell
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/src/lib/utils";

interface Alert {
  id: string;
  transaction_id: string;
  account_id: string;
  risk_score: number;
  risk_level: string;
  recommendation: string;
  shap_top3: string[];
  rule_flags: string[];
  status: string;
  created_at?: string;
  assigned_to?: string;
}

interface AlertRowProps {
  alert: Alert;
  isExpanded: boolean;
  onToggle: () => void;
}

function getSeverityColor(riskLevel: string) {
  if (riskLevel === "CRITICAL") return "bg-tertiary-container text-on-tertiary-container";
  if (riskLevel === "HIGH") return "bg-orange-950/40 text-orange-400 border-orange-500/20";
  return "bg-yellow-950/40 text-yellow-400";
}

function getSeverityProgress(riskLevel: string) {
  if (riskLevel === "CRITICAL") return "bg-error";
  if (riskLevel === "HIGH") return "bg-orange-400";
  return "bg-yellow-400";
}

const AlertRow: React.FC<AlertRowProps> = ({ alert, isExpanded, onToggle }) => {
  return (
    <>
      <tr 
        onClick={onToggle}
        className={cn(
          "transition-all cursor-pointer group",
          isExpanded ? "bg-surface-container border-l-4 border-error shadow-[0_0_20px_0px_rgba(255,71,87,0.1)]" : "hover:bg-surface-container-highest/30"
        )}
      >
        <td className="px-6 py-4 text-sm font-bold text-primary">{alert.id}</td>
        <td className="px-6 py-4 text-sm font-medium">{alert.account_id}</td>
        <td className="px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
              <div className={cn("h-full", alert.risk_score > 80 ? "bg-error" : "bg-primary")} style={{ width: `${alert.risk_score}%` }}></div>
            </div>
            <span className={cn("text-xs font-bold", alert.risk_score > 80 ? "text-error" : "text-on-surface")}>{alert.risk_score}</span>
          </div>
        </td>
        <td className="px-6 py-4">
          <span className={cn("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter", getSeverityColor(alert.risk_level))}>{alert.risk_level}</span>
        </td>
        <td className="px-6 py-4">
          <span className={cn("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tighter", alert.status === "OPEN" ? "bg-primary-container text-primary" : "bg-tertiary-container text-on-tertiary-container")}>{alert.status}</span>
        </td>
        <td className="px-6 py-4">{isExpanded ? <Shrink className="w-4 h-4 text-primary" /> : <ChevronRight className="w-4 h-4 text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity" />}</td>
      </tr>
      <AnimatePresence>
        {isExpanded && (
          <motion.tr initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="bg-surface-container">
            <td className="px-10 pb-8 pt-2" colSpan={6}>
              <div className="grid grid-cols-12 gap-8">
                <div className="col-span-7 bg-surface-container-low p-6 rounded-xl border border-outline-variant/10">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-sm font-black uppercase tracking-widest text-primary flex items-center gap-2"><Brain className="w-4 h-4" />Risk Analysis</h3>
                    <span className="text-[10px] text-on-surface-variant font-medium">Rule-Based Scoring</span>
                  </div>
                  <div className="space-y-4">
                    {(alert.shap_top3 || alert.rule_flags || []).slice(0, 5).map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-surface-container-highest rounded-lg">
                        <span className="text-xs text-on-surface-variant">{item}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-6 text-xs text-on-surface-variant leading-relaxed bg-surface-container-highest/30 p-3 rounded-lg border-l-2 border-primary">
                    <strong>Recommendation:</strong> {alert.recommendation}
                  </p>
                </div>
                <div className="col-span-5 space-y-6">
                  <div className="bg-surface-container-low p-6 rounded-xl border border-outline-variant/10">
                    <h3 className="text-sm font-black uppercase tracking-widest text-on-surface mb-4">Alert Details</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between border-b border-outline-variant/5 pb-2">
                        <span className="text-xs text-on-surface-variant">Alert ID</span>
                        <span className="text-xs font-bold text-primary font-mono">{alert.id}</span>
                      </div>
                      <div className="flex justify-between border-b border-outline-variant/5 pb-2">
                        <span className="text-xs text-on-surface-variant">Transaction</span>
                        <span className="text-xs font-bold text-on-surface font-mono">{alert.transaction_id}</span>
                      </div>
                      <div className="flex justify-between border-b border-outline-variant/5 pb-2">
                        <span className="text-xs text-on-surface-variant">Account</span>
                        <span className="text-xs font-bold text-on-surface font-mono">{alert.account_id}</span>
                      </div>
                      <div className="flex justify-between pb-2">
                        <span className="text-xs text-on-surface-variant">Rule Flags</span>
                        <span className="text-xs font-bold text-error">{alert.rule_flags?.join(", ") || "N/A"}</span>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <button className="py-3 px-4 border border-outline-variant text-on-surface text-xs font-black uppercase tracking-wider rounded-xl hover:bg-surface-container-highest transition-colors flex items-center justify-center gap-2">
                      <PauseCircle className="w-4 h-4" />Hold
                    </button>
                    <button className="py-3 px-4 border border-error/50 text-error text-xs font-black uppercase tracking-wider rounded-xl hover:bg-error/10 transition-colors flex items-center justify-center gap-2">
                      <ShieldAlert className="w-4 h-4" />Block
                    </button>
                    <button className="col-span-2 py-4 bg-primary text-on-primary text-xs font-black uppercase tracking-widest rounded-xl hover:shadow-[0_0_15px_0px_rgba(0,217,255,0.4)] transition-all flex items-center justify-center gap-2 mt-2">
                      <Gavel className="w-4 h-4" />Generate STR Report
                    </button>
                  </div>
                </div>
              </div>
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
  );
};

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("OPEN");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/v1/alerts/?status=${statusFilter}&page_size=50`)
      .then(res => res.json())
      .then(data => {
        setAlerts(data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [statusFilter]);

  const totalOpen = alerts.filter(a => a.status === "OPEN").length;
  const avgRisk = alerts.length > 0 
    ? Math.round(alerts.reduce((sum, a) => sum + a.risk_score, 0) / alerts.length)
    : 0;
  const criticalCount = alerts.filter(a => a.risk_level === "CRITICAL").length;

  return (
    <div className="p-8 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-end mb-10">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Alerts Command Center</h1>
            <p className="text-on-surface-variant text-sm max-w-lg">Monitoring real-time graph anomalies and transactional fraud indicators across the UniGRAPH network.</p>
          </div>
          <div className="flex gap-4 items-center">
            <div className="flex bg-surface-container-low p-1 rounded-lg">
              {["OPEN", "RESOLVED", "ESCALATED"].map((tab) => (
                <button 
                  key={tab}
                  onClick={() => setStatusFilter(tab)}
                  className={cn(
                    "px-4 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-all",
                    statusFilter === tab ? "bg-primary text-on-primary" : "text-on-surface-variant hover:text-on-surface"
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
            <button className="bg-surface-container-highest px-4 py-2.5 rounded-lg border border-outline-variant/10 text-on-surface-variant flex items-center gap-2 text-sm">
              <Filter className="w-4 h-4" />
              Filters
            </button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6 mb-8">
          <div className="col-span-3 bento-card p-6 rounded-xl border border-outline-variant/5 glass-gradient">
            <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-4">Total Open Alerts</p>
            <p className="text-4xl font-black text-on-surface tracking-tighter">{totalOpen}</p>
            <div className="mt-4 flex items-center gap-2 text-error text-xs font-semibold">
              <TrendingUp className="w-3 h-3" />
              From Graph Database
            </div>
          </div>
          <div className="col-span-3 bento-card p-6 rounded-xl border border-outline-variant/5">
            <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-4">Avg Risk Score</p>
            <p className="text-4xl font-black text-primary tracking-tighter">{avgRisk}</p>
            <div className="mt-4 flex items-center gap-2 text-primary text-xs font-semibold">
              <Zap className="w-3 h-3" />
              Active Monitoring
            </div>
          </div>
          <div className="col-span-6 bento-card p-6 rounded-xl border border-outline-variant/5 bg-[#3a0007]/20">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-[10px] uppercase tracking-widest text-tertiary font-bold mb-4">Critical Threats</p>
                <p className="text-4xl font-black text-on-tertiary-container tracking-tighter">{criticalCount}</p>
              </div>
              <div className="h-16 w-32 bg-error/10 rounded-lg flex items-center justify-center">
                <ShieldAlert className="text-error w-10 h-10" />
              </div>
            </div>
            <p className="text-xs text-on-surface-variant mt-4">Immediate intervention required for high-velocity account bursts.</p>
          </div>
        </div>

        <div className="bg-surface-container-low rounded-xl overflow-hidden border border-outline-variant/5">
          {loading ? (
            <div className="p-12 text-center text-on-surface-variant">Loading alerts...</div>
          ) : alerts.length === 0 ? (
            <div className="p-12 text-center text-on-surface-variant">No alerts found</div>
          ) : (
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="bg-surface-container-high/50">
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-on-surface-variant">Alert ID</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-on-surface-variant">Account</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-on-surface-variant">Risk Score</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-on-surface-variant">Risk Level</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase tracking-widest text-on-surface-variant">Status</th>
                  <th className="px-6 py-4 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/10">
                {alerts.map((alert) => (
                  <AlertRow 
                    key={alert.id} 
                    alert={alert} 
                    isExpanded={expandedId === alert.id}
                    onToggle={() => setExpandedId(expandedId === alert.id ? null : alert.id)}
                  />
                ))}
              </tbody>
            </table>
          )}
          <div className="px-6 py-4 flex items-center justify-between bg-surface-container-high/20 border-t border-outline-variant/10">
            <p className="text-xs text-on-surface-variant">Showing <span className="text-on-surface font-bold">{alerts.length}</span> alerts</p>
          </div>
        </div>
      </div>
    </div>
  );
}