import { 
  TrendingUp, 
  AlertCircle, 
  Network, 
  FileText, 
  Eye, 
  ChevronRight,
  Zap,
  ArrowUpRight
} from "lucide-react";
import { BarChart, Bar, XAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/src/lib/utils";

interface HealthData {
  status: string;
  graph_stats: {
    accounts: number;
    transactions: number;
    alerts: number;
    open_alerts: number;
  };
  demo_mode: boolean;
}

interface Alert {
  id: string;
  account_id: string;
  risk_score: number;
  risk_level: string;
  rule_flags: string[];
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    Promise.all([
      fetch("/health").then(r => r.json()),
      fetch("/api/v1/alerts?page_size=5").then(r => r.json())
    ]).then(([healthData, alertsData]) => {
      setHealth(healthData);
      setAlerts(alertsData.items || []);
    }).catch(console.error);
  }, []);

  const kpiData = [
    { label: "Total Alerts", value: health?.graph_stats?.alerts?.toString() || "0", sub: "From graph database", icon: AlertCircle, color: "text-primary", subIcon: TrendingUp },
    { label: "High Risk Txns", value: health?.graph_stats?.transactions?.toString() || "0", sub: "Requires triage", icon: Zap, color: "text-error", subIcon: AlertCircle },
    { label: "Fraud Networks", value: "3", sub: "Active clusters", icon: Network, color: "text-primary", subIcon: Network },
    { label: "STR Pending", value: "0", sub: "Ready for review", icon: FileText, color: "text-on-surface", subIcon: TrendingUp },
  ];

  const criticalAlerts = alerts.filter(a => a.risk_level === "CRITICAL" || a.risk_level === "HIGH").slice(0, 4);

  const chartData = [
    { name: "Mon", value: 40, color: "#00d9ff33" },
    { name: "Tue", value: 65, color: "#00d9ff66" },
    { name: "Wed", value: 85, color: "#ef3b4d66" },
    { name: "Thu", value: 50, color: "#00d9ff4d" },
    { name: "Fri", value: 30, color: "#00d9ff33" },
  ];

  return (
    <div className="p-8 space-y-8 max-w-[1600px] mx-auto w-full">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiData.map((kpi, i) => (
          <motion.div 
            key={kpi.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-surface-container p-6 rounded-xl relative overflow-hidden group glass-gradient border border-outline-variant/5"
          >
            <div className="relative z-10">
              <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-[0.1em] mb-1">{kpi.label}</p>
              <h3 className={cn("text-4xl font-extrabold tracking-tighter", kpi.color)}>{kpi.value}</h3>
              <div className={cn("mt-4 flex items-center gap-2 text-[10px]", kpi.color === "text-error" ? "text-error/70" : "text-primary/70")}>
                <kpi.subIcon className="w-3 h-3" />
                <span>{kpi.sub}</span>
              </div>
            </div>
            <kpi.icon className={cn("absolute -bottom-4 -right-4 w-24 h-24 opacity-5 group-hover:opacity-10 transition-opacity", kpi.color)} />
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12 lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-lg font-bold tracking-tight text-on-surface flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary rounded-full"></span>
              Real-Time Alert Feed
            </h2>
            <div className="flex gap-2">
              <button onClick={() => navigate('/alerts')} className="px-3 py-1 text-[10px] font-bold bg-surface-container-highest text-on-surface-variant rounded-full uppercase tracking-widest hover:text-primary transition-colors">View All</button>
            </div>
          </div>
          
          <div className="bg-surface-container-low rounded-xl overflow-hidden border border-outline-variant/10 shadow-2xl">
            <table className="w-full text-left border-collapse">
              <thead className="bg-surface-container">
                <tr>
                  <th className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em]">Severity</th>
                  <th className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em]">Alert ID</th>
                  <th className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em]">Rule Flags</th>
                  <th className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em]">Risk Score</th>
                  <th className="px-6 py-4 text-[10px] font-black text-on-surface-variant uppercase tracking-[0.2em]">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/5">
                {criticalAlerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-surface-container/50 transition-colors group">
                    <td className="px-6 py-4">
                      <span className={cn("inline-flex items-center px-3 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase border", 
                        alert.risk_level === "CRITICAL" ? "bg-tertiary-container text-on-tertiary-container" :
                        alert.risk_level === "HIGH" ? "bg-orange-950/40 text-orange-400 border-orange-500/20" :
                        "bg-yellow-950/40 text-yellow-400 border-yellow-500/20")}>
                        {alert.risk_level}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-sm text-primary group-hover:underline cursor-pointer">{alert.id}</td>
                    <td className="px-6 py-4 text-sm text-on-surface/80">{alert.rule_flags?.join(", ") || "N/A"}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
                          <div className={cn("h-full", alert.risk_score > 80 ? "bg-error" : "bg-primary")} style={{ width: `${alert.risk_score}%` }}></div>
                        </div>
                        <span className={cn("text-xs font-bold", alert.risk_score > 80 ? "text-error" : "text-on-surface")}>{alert.risk_score}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <button onClick={() => navigate('/alerts')} className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors">
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-6 py-4 bg-surface-container-low text-center">
              <button onClick={() => navigate('/alerts')} className="text-[10px] font-black text-primary uppercase tracking-[0.2em] hover:tracking-[0.3em] transition-all">View All Activity</button>
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 space-y-8">
          <div className="space-y-4">
            <h2 className="text-lg font-bold tracking-tight text-on-surface flex items-center gap-2">
              <span className="w-1.5 h-6 bg-primary rounded-full"></span>
              Quick Operations
            </h2>
            <div className="grid grid-cols-1 gap-4">
              {[
                { label: "View Alerts", sub: "Review fraud alerts", icon: AlertCircle, route: "/alerts" },
                { label: "Generate STR", sub: "Create report", icon: FileText, route: "/str-reports" },
                { label: "Graph Explorer", sub: "View networks", icon: Network, route: "/graph-explorer" },
              ].map((op) => (
                <button key={op.label} onClick={() => navigate(op.route)} className="group flex items-center justify-between p-4 bg-surface-container rounded-xl border border-outline-variant/5 hover:bg-surface-container-highest transition-all duration-300">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-primary/10 text-primary rounded-xl group-hover:bg-primary group-hover:text-on-primary transition-colors">
                      <op.icon className="w-5 h-5" />
                    </div>
                    <div className="text-left">
                      <p className="font-bold text-sm">{op.label}</p>
                      <p className="text-[10px] text-on-surface-variant uppercase">{op.sub}</p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-primary group-hover:translate-x-1 transition-transform" />
                </button>
              ))}
            </div>
          </div>

          <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/5 glass-gradient">
            <div className="flex justify-between items-start mb-6">
              <div>
                <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Network Density</p>
                <h4 className="text-xl font-bold">Threat Clusters</h4>
              </div>
              <span className="text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded uppercase font-bold tracking-tighter">Live Scan</span>
            </div>
            <div className="h-32 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#122031', border: 'none', borderRadius: '8px', fontSize: '10px' }}
                    cursor={{ fill: 'transparent' }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color.replace('66', 'ff').replace('33', '88')} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-6 flex justify-between text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">
              {chartData.map(d => <span key={d.name}>{d.name}</span>)}
            </div>
          </div>
        </div>
      </div>

      <div className="col-span-12">
        <div className="bg-surface-container-low rounded-2xl p-8 relative overflow-hidden border border-outline-variant/10 min-h-[400px] flex items-center justify-center">
          <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #00D9FF 1px, transparent 0)', backgroundSize: '40px 40px' }}></div>
          <div className="relative text-center max-w-lg z-10">
            <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-primary/20">
              <Network className="w-10 h-10 text-primary animate-pulse" />
            </div>
            <h3 className="text-2xl font-bold tracking-tight mb-2">Graph Intelligence Engine</h3>
            <p className="text-on-surface-variant text-sm mb-8 leading-relaxed">
              The UniGRAPH system is currently processing {health?.graph_stats?.accounts || 0} account nodes and {health?.graph_stats?.transactions || 0} transactions. Switch to the Graph Explorer to visualize multi-hop money laundering paths.
            </p>
            <button onClick={() => navigate('/graph-explorer')} className="bg-surface-container-highest border border-primary/30 text-primary px-8 py-3 rounded-xl font-bold text-xs uppercase tracking-[0.2em] hover:bg-primary hover:text-on-primary transition-all">Launch Graph Explorer</button>
          </div>
        </div>
      </div>

      <footer className="mt-auto border-t border-outline-variant/10 py-4 px-8 flex justify-between items-center text-[10px] text-on-surface-variant font-medium tracking-widest uppercase">
        <div className="flex gap-8">
          <p>Database: <span className="text-primary">Connected</span></p>
          <p>Accounts: <span className="text-primary">{health?.graph_stats?.accounts || 0}</span></p>
          <p>Transactions: <span className="text-primary">{health?.graph_stats?.transactions || 0}</span></p>
        </div>
        <div className="flex gap-4">
          <span className="opacity-50">UniGRAPH v1.0.0</span>
          <span className="opacity-50">© 2024 Union Bank of India</span>
        </div>
      </footer>
    </div>
  );
}