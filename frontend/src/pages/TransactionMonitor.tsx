import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Download, Flag, Check, Info } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { generateTransactions, type Transaction } from "@/data/transactions";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import { toast } from "sonner";

const CHANNELS = ["All", "UPI", "NEFT", "RTGS", "IMPS", "CASH", "Card"];
const STATUSES = ["All", "Flagged", "Cleared", "Pending"];
const DATE_RANGES = ["Today", "This Week", "This Month"];

const shapReasons: { feature: string; direction: "up" | "down"; value: number }[] = [
  { feature: "Transaction velocity", direction: "up", value: 14.2 },
  { feature: "Amount deviation", direction: "up", value: 11.8 },
  { feature: "Account age", direction: "down", value: 5.3 },
];

export default function TransactionMonitor() {
  const navigate = useNavigate();
  const allTransactions = useMemo(() => generateTransactions(50), []);
  const [channelFilter, setChannelFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [dateRange, setDateRange] = useState("Today");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(15);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [exportLoading, setExportLoading] = useState(false);
  const [bulkFlagLoading, setBulkFlagLoading] = useState(false);

  const filtered = useMemo(() => {
    return allTransactions.filter((t) => {
      if (channelFilter !== "All" && t.channel !== channelFilter) return false;
      if (statusFilter !== "All" && t.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!t.txnId.toLowerCase().includes(q) && !t.source.toLowerCase().includes(q) && !t.destination.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [allTransactions, channelFilter, statusFilter, search]);

  const paged = filtered.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(filtered.length / perPage);

  const flaggedCount = filtered.filter(t => t.status === "Flagged").length;
  const clearedCount = filtered.filter(t => t.status === "Cleared").length;
  const pendingCount = filtered.filter(t => t.status === "Pending").length;

  const toggleRow = (id: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedRows.size === paged.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(paged.map(t => t.txnId)));
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-primary">Transaction Monitor</h1>
        <p className="text-xs text-muted-foreground mt-1">Real-time transaction surveillance · 8,64,320 transactions today</p>
      </div>

      {/* Filter Bar */}
      <div className="bg-card border border-border rounded-[10px] p-4 space-y-3">
        <div className="flex flex-wrap gap-2">
          {CHANNELS.map((ch) => (
            <button
              key={ch}
              onClick={() => { setChannelFilter(ch); setPage(0); }}
              className={`text-xs h-8 px-3 rounded-md cursor-pointer font-medium ${channelFilter === ch ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"}`}
            >
              {ch}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              placeholder="Search TXN ID / Account..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="w-full bg-background border border-border rounded-md py-2 pl-9 pr-3 text-sm text-foreground outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex gap-1">
            {DATE_RANGES.map(dr => (
              <button
                key={dr}
                onClick={() => setDateRange(dr)}
                className={`text-xs px-3 py-2 rounded-md cursor-pointer ${dateRange === dr ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
              >
                {dr}
              </button>
            ))}
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            className="bg-card border border-border rounded-md py-2 px-3 text-xs text-foreground outline-none cursor-pointer"
          >
            {STATUSES.map(s => <option key={s} value={s}>{s === "All" ? "All Status" : s}</option>)}
          </select>
          <button
            disabled={exportLoading}
            onClick={() => { setExportLoading(true); setTimeout(() => { setExportLoading(false); toast.success("Transactions exported as CSV"); }, 1500); }}
            className="text-xs h-9 px-3 border border-border rounded-md bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer disabled:opacity-50"
          >
            <Download className="w-3 h-3" /> {exportLoading ? "Exporting..." : "Export CSV"}
          </button>
          <button
            disabled={bulkFlagLoading}
            onClick={() => { setBulkFlagLoading(true); setTimeout(() => { setBulkFlagLoading(false); toast.success(`${selectedRows.size} transactions flagged`); }, 1500); }}
            className="text-xs h-9 px-3 border border-border rounded-md bg-card text-foreground hover:bg-muted flex items-center gap-1 cursor-pointer disabled:opacity-50"
          >
            <Flag className="w-3 h-3" /> {bulkFlagLoading ? "Flagging..." : "Bulk Flag"}
          </button>
        </div>
      </div>

      {/* Stats Mini Row */}
      <div className="flex flex-wrap gap-3 text-xs">
        <span className="bg-card border border-border rounded-md px-3 py-1.5">Total: <strong>{filtered.length}</strong></span>
        <span className="bg-card border border-border rounded-md px-3 py-1.5 text-danger">Flagged: <strong>{flaggedCount}</strong></span>
        <span className="bg-card border border-border rounded-md px-3 py-1.5 text-success">Cleared: <strong>{clearedCount}</strong></span>
        <span className="bg-card border border-border rounded-md px-3 py-1.5 text-warning">Pending: <strong>{pendingCount}</strong></span>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-[10px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-table-header text-table-header-foreground text-[11px] font-semibold tracking-wide uppercase">
                <th className="p-2.5 w-10">
                  <input type="checkbox" checked={selectedRows.size === paged.length && paged.length > 0} onChange={toggleAll} className="cursor-pointer" />
                </th>
                <th className="text-left p-2.5">TXN ID</th>
                <th className="text-left p-2.5">Date & Time</th>
                <th className="text-left p-2.5">From</th>
                <th className="text-left p-2.5">To</th>
                <th className="text-right p-2.5">Amount (₹)</th>
                <th className="text-left p-2.5">Channel</th>
                <th className="text-center p-2.5">Risk Score</th>
                <th className="text-left p-2.5">Flags</th>
                <th className="text-left p-2.5">Status</th>
                <th className="text-center p-2.5">Action</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((t, i) => (
                <tr
                  key={t.txnId + i}
                  className="border-b last:border-0 hover:bg-info/5 cursor-pointer"
                  style={{ background: i % 2 === 1 ? "hsl(var(--table-stripe))" : undefined }}
                  onClick={() => setSelected(t)}
                >
                  <td className="p-2.5" onClick={e => e.stopPropagation()}>
                    <input type="checkbox" checked={selectedRows.has(t.txnId)} onChange={() => toggleRow(t.txnId)} className="cursor-pointer" />
                  </td>
                  <td className="p-2.5 font-mono font-medium text-primary">{t.txnId}</td>
                  <td className="p-2.5 text-muted-foreground">{t.timestamp}</td>
                  <td className="p-2.5 font-mono">{t.source}</td>
                  <td className="p-2.5 font-mono">{t.destination}</td>
                  <td className="p-2.5 text-right font-semibold">{t.amount}</td>
                  <td className="p-2.5"><span className="bg-muted text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">{t.channel}</span></td>
                  <td className="p-2.5">
                    <div className="flex justify-center"><RiskScoreBar score={t.riskScore} size="sm" /></div>
                  </td>
                  <td className="p-2.5">
                    <div className="flex flex-wrap gap-0.5">
                      {t.flags.map((f) => (
                        <span key={f} className="text-[9px] px-1.5 py-0.5 bg-muted rounded text-muted-foreground">{f}</span>
                      ))}
                    </div>
                  </td>
                  <td className="p-2.5 font-medium" style={{
                    color: t.status === "Flagged" ? "hsl(var(--danger))" : t.status === "Cleared" ? "hsl(var(--success))" : "hsl(var(--warning))",
                  }}>{t.status}</td>
                  <td className="p-2.5 text-center">
                    <button className="text-xs text-primary hover:underline cursor-pointer" onClick={(e) => { e.stopPropagation(); setSelected(t); }}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-3 border-t">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Showing {page * perPage + 1}–{Math.min((page + 1) * perPage, filtered.length)} of {filtered.length}</span>
            <select
              value={perPage}
              onChange={(e) => { setPerPage(Number(e.target.value)); setPage(0); }}
              className="text-xs border border-border rounded px-2 py-1 bg-card cursor-pointer"
            >
              {[15, 25, 50].map(n => <option key={n} value={n}>{n} per page</option>)}
            </select>
          </div>
          <div className="flex gap-1">
            <button
              disabled={page === 0}
              onClick={() => setPage(page - 1)}
              className="text-xs px-2 py-1 rounded border border-border bg-card hover:bg-muted cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`text-xs w-7 h-7 rounded border cursor-pointer ${page === i ? "bg-primary text-primary-foreground border-primary" : "border-border bg-card hover:bg-muted"}`}
              >
                {i + 1}
              </button>
            ))}
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage(page + 1)}
              className="text-xs px-2 py-1 rounded border border-border bg-card hover:bg-muted cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Detail Sheet */}
      <Sheet open={!!selected} onOpenChange={() => setSelected(null)}>
        <SheetContent className="w-[420px] overflow-y-auto">
          {selected && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selected.txnId}
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{
                    color: selected.status === "Flagged" ? "hsl(var(--danger))" : selected.status === "Cleared" ? "hsl(var(--success))" : "hsl(var(--warning))",
                    background: selected.status === "Flagged" ? "hsl(0, 86%, 97%)" : selected.status === "Cleared" ? "hsl(149, 80%, 90%)" : "hsl(48, 96%, 89%)",
                  }}>
                    {selected.status}
                  </span>
                </SheetTitle>
              </SheetHeader>
              <div className="mt-4 space-y-4 text-sm">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="text-muted-foreground">From</div><div className="font-mono">{selected.source}</div>
                  <div className="text-muted-foreground">To</div><div className="font-mono">{selected.destination}</div>
                  <div className="text-muted-foreground">Amount</div><div className="font-bold">{selected.amount}</div>
                  <div className="text-muted-foreground">Channel</div><div>{selected.channel}</div>
                  <div className="text-muted-foreground">Branch</div><div>{selected.branch}</div>
                  <div className="text-muted-foreground">Time</div><div>{selected.timestamp}</div>
                </div>

                {/* Risk Score */}
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs font-semibold mb-2">Risk Score</div>
                  <div className="flex items-center gap-3">
                    <span className="text-3xl font-bold" style={{ color: getRiskColor(selected.riskScore) }}>{selected.riskScore}</span>
                    <div className="flex-1">
                      <div className="w-full h-2 rounded-full bg-border overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${selected.riskScore}%`, background: getRiskColor(selected.riskScore) }} />
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-1">{getRiskLabel(selected.riskScore)}</div>
                    </div>
                  </div>
                </div>

                {/* Flags */}
                {selected.flags.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold mb-2">Flags</div>
                    <div className="flex flex-wrap gap-1.5">
                      {selected.flags.map((f) => (
                        <span key={f} className="text-[10px] px-2 py-1 bg-muted rounded text-muted-foreground">{f}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* SHAP Mini Panel */}
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="flex items-center gap-1 mb-2">
                    <Info className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs font-semibold">Why flagged (SHAP)</span>
                  </div>
                  <div className="space-y-1.5">
                    {shapReasons.map(s => (
                      <div key={s.feature} className="flex items-center justify-between text-[11px]">
                        <span className="text-foreground">{s.feature}</span>
                        <span className={s.direction === "up" ? "text-danger font-semibold" : "text-success font-semibold"}>
                          {s.direction === "up" ? "↑" : "↓"} {s.direction === "up" ? "+" : "-"}{s.value} pts
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  className="w-full h-10 bg-primary text-primary-foreground rounded-md text-sm font-semibold cursor-pointer hover:bg-primary/90"
                  onClick={() => { setSelected(null); toast.success("Added to active investigation"); }}
                >
                  Add to Investigation
                </button>
                <button
                  className="w-full h-10 border border-border bg-card text-foreground rounded-md text-sm font-medium cursor-pointer hover:bg-muted"
                  onClick={() => { setSelected(null); toast.success("Transaction marked as cleared"); }}
                >
                  <Check className="w-4 h-4 inline mr-1" /> Mark Cleared
                </button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
