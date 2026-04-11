import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, AlertTriangle, ShieldAlert, FileCheck, TrendingUp, Target, ArrowUpRight } from "lucide-react";
import { generateTransactions, type Transaction } from "@/data/transactions";
import { alertCards } from "@/data/alerts-data";
import RiskScoreBar, { getRiskColor } from "@/components/RiskScoreBar";
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Area, AreaChart, LabelList,
} from "recharts";

const kpiCards = [
  { label: "Total Transactions Today", value: "8,64,320", sub: "↑ 3.2% from yesterday", icon: Activity, borderColor: "hsl(var(--info))", iconBg: "hsl(214, 95%, 93%)", iconColor: "hsl(var(--info))" },
  { label: "Active Alerts", value: String(alertCards.length), sub: `${alertCards.filter(a => a.riskScore >= 90).length} critical priority`, icon: AlertTriangle, borderColor: "hsl(var(--danger))", iconBg: "hsl(0, 86%, 97%)", iconColor: "hsl(var(--danger))" },
  { label: "Open Cases", value: "23", sub: "5 escalated this week", icon: ShieldAlert, borderColor: "hsl(var(--warning))", iconBg: "hsl(48, 96%, 89%)", iconColor: "hsl(var(--warning))" },
  { label: "STR Filed Today", value: "3", sub: "2 pending FIU-IND", icon: FileCheck, borderColor: "hsl(var(--success))", iconBg: "hsl(149, 80%, 90%)", iconColor: "hsl(var(--success))" },
  { label: "Avg Risk Score", value: "74.2", sub: "↑ from 68.1 last week", icon: TrendingUp, borderColor: "hsl(263, 70%, 50%)", iconBg: "hsl(263, 70%, 96%)", iconColor: "hsl(263, 70%, 50%)" },
  { label: "Detection Rate", value: "94.3%", sub: "False positive: 8.3%", icon: Target, borderColor: "hsl(188, 86%, 40%)", iconBg: "hsl(188, 86%, 95%)", iconColor: "hsl(188, 86%, 40%)" },
];

const fraudBarData = [
  { name: "Rapid Layering", count: 13 },
  { name: "Round-Tripping", count: 9 },
  { name: "Structuring", count: 11 },
  { name: "Dormant Activation", count: 6 },
  { name: "Profile Mismatch", count: 8 },
  { name: "Mule Account", count: 7 },
];

const alertVolumeData = Array.from({ length: 30 }, (_, i) => ({
  day: `D${i + 1}`,
  alerts: Math.floor(15 + Math.random() * 40 + Math.sin(i / 5) * 10),
}));

const recentAlerts = alertCards.slice(0, 5);

const fraudTypeColors: Record<string, string> = {
  "Rapid Layering": "hsl(0, 72%, 51%)",
  "Round-Tripping": "hsl(263, 70%, 50%)",
  "Structuring/Smurfing": "hsl(188, 86%, 40%)",
  "Dormant Activation": "hsl(32, 95%, 44%)",
  "Profile Mismatch": "hsl(160, 84%, 29%)",
  "Mule Account": "hsl(var(--danger))",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<Transaction[]>(() => generateTransactions(15));
  const [newRowId, setNewRowId] = useState<string | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setTransactions((prev) => {
        const newTxn = generateTransactions(1)[0];
        newTxn.txnId = `TXN-${Date.now().toString().slice(-6)}`;
        setNewRowId(newTxn.txnId);
        setTimeout(() => setNewRowId(null), 1000);
        return [newTxn, ...prev.slice(0, 14)];
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-5">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-primary">Dashboard Overview</h1>
        <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-1">
          Real-time AML monitoring · Updated live
          <span className="w-2 h-2 rounded-full bg-success animate-pulse-dot" />
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {kpiCards.map((s) => (
          <div
            key={s.label}
            className="bg-card border border-border rounded-[10px] p-4 shadow-none"
            style={{ borderTop: `4px solid ${s.borderColor}` }}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-muted-foreground text-[11px] font-semibold tracking-wide uppercase">{s.label}</div>
                <div className="text-foreground mt-1 text-2xl font-bold">{s.value}</div>
                <div className="text-muted-foreground mt-1 text-xs">{s.sub}</div>
              </div>
              <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: s.iconBg }}>
                <s.icon className="w-[18px] h-[18px]" style={{ color: s.iconColor }} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid: Feed + Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 items-start">
        {/* Live Transaction Feed */}
        <div className="lg:col-span-3 bg-card border border-border rounded-[10px] overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-border">
            <span className="text-foreground font-semibold text-sm">Live Transaction Feed</span>
            <span className="w-2 h-2 rounded-full bg-success animate-pulse-dot" />
            <span className="bg-danger text-white text-[9px] font-bold px-2 py-0.5 rounded-full ml-1">LIVE</span>
          </div>
          <div className="max-h-[520px] overflow-y-auto scrollbar-thin">
            <table className="w-full" style={{ borderCollapse: "collapse", tableLayout: "fixed" }}>
              <thead>
                <tr className="bg-table-header text-table-header-foreground text-[11px] font-semibold tracking-wide uppercase">
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "14%" }}>TXN ID</th>
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "12%" }}>From</th>
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "12%" }}>To</th>
                  <th className="text-right p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "14%" }}>Amount</th>
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "10%" }}>Channel</th>
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "18%" }}>Time</th>
                  <th className="text-left p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "10%" }}>Status</th>
                  <th className="text-center p-2.5 sticky top-0 z-10 bg-table-header" style={{ width: "10%" }}>Risk</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t, i) => (
                  <tr
                    key={t.txnId + i}
                    className={`border-b border-border/50 hover:bg-info/5 cursor-pointer ${newRowId === t.txnId ? "animate-flash-row" : ""}`}
                    style={{ background: i % 2 === 1 ? "hsl(var(--table-stripe))" : undefined }}
                    onClick={() => navigate("/transactions")}
                  >
                    <td className="p-2.5 text-[13px] font-mono font-medium text-primary truncate">{t.txnId}</td>
                    <td className="p-2.5 text-[13px] font-mono text-foreground truncate">{t.source}</td>
                    <td className="p-2.5 text-[13px] font-mono text-foreground truncate">{t.destination}</td>
                    <td className="p-2.5 text-[13px] text-right font-semibold text-foreground">{t.amount}</td>
                    <td className="p-2.5">
                      <span className="bg-muted text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">{t.channel}</span>
                    </td>
                    <td className="p-2.5 text-[12px] text-muted-foreground truncate">{t.timestamp}</td>
                    <td className="p-2.5 text-[12px] font-medium" style={{
                      color: t.status === "Flagged" ? "hsl(var(--danger))" : t.status === "Cleared" ? "hsl(var(--success))" : "hsl(var(--warning))",
                      fontWeight: t.status === "Flagged" ? 600 : 400,
                    }}>{t.status}</td>
                    <td className="p-2.5">
                      <RiskScoreBar score={t.riskScore} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Charts Column */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Fraud Bar Chart */}
          <div className="bg-card border border-border rounded-[10px] p-5">
            <div className="mb-3">
              <div className="text-foreground font-semibold text-sm">Fraud Detections by Type</div>
              <div className="text-muted-foreground text-xs mt-0.5">This week's breakdown</div>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart layout="vertical" data={fraudBarData} margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
                <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                <XAxis type="number" domain={[0, 16]} ticks={[0, 4, 8, 12, 16]} tick={{ fontSize: 11, fill: "hsl(215, 16%, 47%)" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fill: "hsl(222, 47%, 11%)", fontWeight: 500 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={18} fill="hsl(var(--info))">
                  <LabelList dataKey="count" position="right" style={{ fontSize: 11, fill: "hsl(222, 47%, 11%)", fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Alert Volume Line Chart */}
          <div className="bg-card border border-border rounded-[10px] p-5">
            <div className="mb-3">
              <div className="text-foreground font-semibold text-sm">Alert Volume — Last 30 Days</div>
              <div className="text-muted-foreground text-xs mt-0.5">Daily alert trend</div>
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={alertVolumeData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 10, fill: "hsl(215, 16%, 47%)" }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fontSize: 10, fill: "hsl(215, 16%, 47%)" }} axisLine={false} tickLine={false} width={28} domain={[0, 60]} ticks={[0, 15, 30, 45, 60]} />
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid hsl(var(--border))", borderRadius: 6, fontSize: 12 }} />
                <defs>
                  <linearGradient id="alertFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--danger))" stopOpacity={0.15} />
                    <stop offset="100%" stopColor="hsl(var(--danger))" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <Area type="monotone" dataKey="alerts" stroke="hsl(var(--danger))" strokeWidth={2} fill="url(#alertFill)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent High-Risk Alerts */}
      <div className="bg-card border border-border rounded-[10px] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
          <span className="text-foreground font-semibold text-sm">Recent High-Risk Alerts</span>
          <button onClick={() => navigate("/alerts")} className="text-xs text-primary hover:underline font-medium cursor-pointer">
            View All →
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-table-header text-table-header-foreground text-[11px] font-semibold tracking-wide uppercase">
                <th className="text-left p-3">Alert ID</th>
                <th className="text-left p-3">Account</th>
                <th className="text-left p-3">Fraud Type</th>
                <th className="text-right p-3">Amount</th>
                <th className="text-center p-3">Risk Score</th>
                <th className="text-left p-3">Time</th>
                <th className="text-right p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {recentAlerts.map((a, i) => (
                <tr
                  key={a.id}
                  className="border-b last:border-0 hover:bg-info/5 cursor-pointer"
                  style={{ background: i % 2 === 1 ? "hsl(var(--table-stripe))" : undefined }}
                >
                  <td className="p-3 font-mono font-semibold text-primary text-xs">{a.id}</td>
                  <td className="p-3 font-mono text-xs">{a.account}</td>
                  <td className="p-3 text-xs">
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold" style={{
                      color: fraudTypeColors[a.fraudType] || "hsl(var(--foreground))",
                      background: `${fraudTypeColors[a.fraudType] || "hsl(var(--muted))"}15`,
                    }}>
                      {a.fraudType}
                    </span>
                  </td>
                  <td className="p-3 text-xs text-right font-semibold">{a.amount}</td>
                  <td className="p-3">
                    <div className="flex justify-center">
                      <RiskScoreBar score={a.riskScore} size="sm" />
                    </div>
                  </td>
                  <td className="p-3 text-xs text-muted-foreground">{a.timeDetected.split(" ")[1]}</td>
                  <td className="p-3 text-right">
                    <button
                      className="text-xs bg-primary text-primary-foreground px-3 py-1.5 rounded font-semibold hover:bg-primary/90 cursor-pointer inline-flex items-center gap-1"
                      onClick={(e) => { e.stopPropagation(); navigate(`/graph?alert=${a.id}`); }}
                    >
                      Investigate <ArrowUpRight className="w-3 h-3" />
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
