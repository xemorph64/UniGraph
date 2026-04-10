import { Search, Bell, Settings } from "lucide-react";
import { useEffect, useState } from "react";

export default function Header() {
  const [health, setHealth] = useState<{ status: string } | null>(null);

  useEffect(() => {
    fetch("/health")
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => setHealth({ status: "offline" }));
  }, []);

  return (
    <header className="w-full sticky top-0 z-40 bg-surface-dim border-b border-outline-variant/15 px-8 h-16 flex justify-between items-center antialiased tracking-tight">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 bg-primary-container px-3 py-1 rounded-full border border-primary/20">
          <span className={health?.status === "online" ? "w-2 h-2 rounded-full bg-primary animate-pulse" : "w-2 h-2 rounded-full bg-error"}></span>
          <span className="text-[10px] font-bold text-primary tracking-widest uppercase">
            Health: {health?.status || "Connecting..."}
          </span>
        </div>
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant w-4 h-4" />
          <input 
            className="bg-surface-container-highest/50 border-none rounded-xl pl-10 pr-4 py-1.5 text-xs w-64 focus:ring-1 focus:ring-primary/50 placeholder:text-on-surface-variant/50 outline-none" 
            placeholder="Global Entity Search..." 
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4">
          <button className="p-2 text-on-surface-variant hover:bg-surface-container-highest/50 rounded-lg transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-surface-dim"></span>
          </button>
          <button className="p-2 text-on-surface-variant hover:bg-surface-container-highest/50 rounded-lg transition-colors">
            <Settings className="w-5 h-5" />
          </button>
        </div>
        <div className="h-8 w-[1px] bg-outline-variant/20"></div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs font-bold text-on-surface">Investigator Prime</p>
            <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">Sentinel Node 04</p>
          </div>
          <img 
            alt="Investigator Profile" 
            className="w-10 h-10 rounded-xl object-cover ring-2 ring-primary/20" 
            src="https://picsum.photos/seed/investigator/100/100"
            referrerPolicy="no-referrer"
          />
        </div>
      </div>
    </header>
  );
}
