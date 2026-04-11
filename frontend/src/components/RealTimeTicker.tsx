import { useEffect, useState } from 'react';
import { Zap, ArrowRight, AlertTriangle } from 'lucide-react';
import { cn } from "@/src/lib/utils";

interface LiveTransaction {
  txn_id: string;
  from_account: string;
  to_account: string;
  amount: number;
  channel: string;
  risk_level: string;
  timestamp: string;
}

interface RealTimeTickerProps {
  baseUrl?: string;
}

export default function RealTimeTicker({ baseUrl = '' }: RealTimeTickerProps) {
  const [transactions, setTransactions] = useState<LiveTransaction[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [stats, setStats] = useState({ total: 0, flagged: 0, cleared: 0 });

  useEffect(() => {
    // Poll for recent transactions
    const pollTransactions = async () => {
      try {
        const response = await fetch(`${baseUrl}/api/v1/transactions/recent?limit=20`);
        if (response.ok) {
          const data = await response.json();
          setTransactions(data.transactions || []);
          
          const txns = data.transactions || [];
          setStats({
            total: txns.length,
            flagged: txns.filter((t: LiveTransaction) => t.risk_level === 'HIGH' || t.risk_level === 'CRITICAL').length,
            cleared: txns.filter((t: LiveTransaction) => t.risk_level === 'LOW').length,
          });
          setIsConnected(true);
        }
      } catch {
        setIsConnected(false);
      }
    };

    pollTransactions();
    const interval = setInterval(pollTransactions, 3000);
    return () => clearInterval(interval);
  }, [baseUrl]);

  const formatAmount = (amount: number) => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    return `₹${amount.toLocaleString()}`;
  };

  return (
    <div className="bg-surface-container-low rounded-xl border border-outline-variant/10 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-surface-container border-b border-outline-variant/10">
        <div className="flex items-center gap-2">
          <Zap className={cn("w-4 h-4", isConnected ? "text-green-400 animate-pulse" : "text-error")} />
          <span className="text-xs font-bold uppercase tracking-wider text-on-surface">Live Transaction Stream</span>
        </div>
        <div className="flex items-center gap-4 text-[10px]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-error"></span>
            <span className="text-on-surface-variant">Flagged: {stats.flagged}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-400"></span>
            <span className="text-on-surface-variant">Cleared: {stats.cleared}</span>
          </span>
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {transactions.length === 0 ? (
          <div className="p-8 text-center text-on-surface-variant text-sm">
            Waiting for transactions...
          </div>
        ) : (
          <div className="divide-y divide-outline-variant/5">
            {transactions.map((txn) => (
              <div 
                key={txn.txn_id} 
                className={cn(
                  "flex items-center justify-between px-4 py-2 hover:bg-surface-container/50 transition-colors",
                  txn.risk_level === 'CRITICAL' || txn.risk_level === 'HIGH' ? "bg-error/5" : ""
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-1.5 h-8 rounded-full",
                    txn.risk_level === 'CRITICAL' ? "bg-error" :
                    txn.risk_level === 'HIGH' ? "bg-orange-400" :
                    "bg-green-400"
                  )} />
                  <div>
                    <p className="text-xs font-bold text-primary font-mono">{txn.txn_id}</p>
                    <p className="text-[10px] text-on-surface-variant">{txn.from_account}</p>
                  </div>
                </div>
                
                <ArrowRight className="w-3 h-3 text-on-surface-variant" />
                
                <div className="text-right">
                  <p className="text-xs font-bold text-on-surface">{formatAmount(txn.amount)}</p>
                  <p className="text-[10px] text-on-surface-variant">{txn.channel}</p>
                </div>
                
                <div className={cn(
                  "px-2 py-1 rounded text-[10px] font-bold uppercase",
                  txn.risk_level === 'CRITICAL' ? "bg-error/20 text-error" :
                  txn.risk_level === 'HIGH' ? "bg-orange-400/20 text-orange-400" :
                  "bg-green-400/20 text-green-400"
                )}>
                  {txn.risk_level === 'LOW' ? 'CLEAR' : txn.risk_level}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}