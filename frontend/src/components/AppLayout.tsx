import { useState, useRef, useEffect, useCallback } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { connectAlertsWebSocket, listAlerts, listTransactions, type BackendAlert } from "@/lib/unigraph-api";

const breadcrumbMap: Record<string, string> = {
  "/": "Dashboard Overview",
  "/alerts": "Alerts & Cases",
  "/graph": "Graph Explorer",
  "/copilot": "Investigator Copilot",
  "/transactions": "Transaction Monitor",
  "/str-generator": "STR Generator",
  "/pipeline-status": "Pipeline Status",
  "/settings": "Settings & Profile",
};

interface HeaderNotification {
  alertId: string;
  text: string;
  time: string;
}

function prettifyFlag(flag: string): string {
  return flag
    .toLowerCase()
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function formatAlertTime(value?: string): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

function toHeaderNotification(alert: BackendAlert): HeaderNotification {
  const topFlag = alert.rule_flags?.[0] ? prettifyFlag(alert.rule_flags[0]) : "Anomaly";
  const risk = Number.isFinite(alert.risk_score) ? `risk ${Math.round(alert.risk_score)}` : "risk -";
  return {
    alertId: alert.id,
    text: `${alert.id}: ${topFlag} detected (${risk})`,
    time: formatAlertTime(alert.created_at),
  };
}

function AppContent() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentYear = new Date().getFullYear();

  const pageName = breadcrumbMap[location.pathname] || "Dashboard";
  const [notifOpen, setNotifOpen] = useState(false);
  const [transactionCount, setTransactionCount] = useState<number | null>(null);
  const [alertCount, setAlertCount] = useState<number | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [recentNotifications, setRecentNotifications] = useState<HeaderNotification[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const loadHeaderData = useCallback(async () => {
    try {
      const [txnResp, alertResp] = await Promise.all([
        listTransactions({ page: 1, pageSize: 1 }),
        listAlerts({ page: 1, pageSize: 5 }),
      ]);
      setTransactionCount(txnResp.total ?? txnResp.items.length);
      setAlertCount(alertResp.total ?? alertResp.items.length);
      setRecentNotifications(alertResp.items.map(toHeaderNotification));
    } catch {
      // Keep the current UI state when backend polling fails.
    }
  }, []);

  useEffect(() => {
    void loadHeaderData();
    const poller = setInterval(() => {
      void loadHeaderData();
    }, 15000);
    return () => clearInterval(poller);
  }, [loadHeaderData]);

  useEffect(() => {
    const disconnect = connectAlertsWebSocket(
      "layout-header-ui",
      (incomingAlert) => {
        setRecentNotifications((prev) => {
          const next = [toHeaderNotification(incomingAlert), ...prev.filter((item) => item.alertId !== incomingAlert.id)];
          return next.slice(0, 5);
        });
        setAlertCount((prev) => (prev ?? 0) + 1);
      },
      setWsConnected,
    );

    return disconnect;
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setNotifOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between bg-navbar px-4 shrink-0 h-[60px] border-b-[3px] border-danger">
        {/* LEFT — Branding */}
        <div className="flex items-center gap-2">
            <div>
              <div className="text-navbar-foreground font-extrabold text-[21px] leading-tight tracking-wide">UniGRAPH</div>
              <div className="text-[12px] tracking-[2px] font-medium uppercase" style={{ color: "#93C5FD" }}>
                Unified Banking Intelligence
              </div>
            </div>
           <div className="w-px h-[30px] bg-white/20 mx-3" />
        </div>

        {/* CENTER — Live stat chips */}
        <div className="hidden md:flex items-center gap-2">
          {[
            { dot: wsConnected ? "bg-success" : "bg-warning", label: wsConnected ? "Live stream connected" : "Polling mode" },
            { dot: "bg-info", label: `${(transactionCount ?? 0).toLocaleString("en-IN")} transactions` },
            { dot: "bg-danger", label: `${alertCount ?? 0} active alerts` },
          ].map((chip) => (
            <div key={chip.label} className="flex items-center gap-1.5 rounded-full px-3 py-1 bg-white/10 text-white text-[14px]">
              <span className={`inline-block w-2 h-2 rounded-full ${chip.dot}`} />
              {chip.label}
            </div>
          ))}
        </div>

        {/* RIGHT — Bell + Theme + User */}
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <div className="relative" ref={dropdownRef}>
            <button onClick={() => setNotifOpen(!notifOpen)} className="relative cursor-pointer">
              <Bell className="h-5 w-5 text-navbar-foreground/80" />
              {(alertCount ?? 0) > 0 && (
                <span className="absolute -top-2 -right-2 flex items-center justify-center text-navbar-foreground bg-danger rounded-full px-1.5 text-[12px] font-bold min-w-[16px]">
                  {alertCount}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="absolute right-0 top-10 w-80 bg-card border border-border rounded-lg shadow-lg z-50">
                <div className="flex items-center justify-between p-3 border-b">
                  <span className="text-sm font-semibold text-foreground">Notifications</span>
                  <button onClick={() => setRecentNotifications([])} className="text-xs text-primary hover:underline">
                    Mark all read
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {recentNotifications.length === 0 ? (
                    <div className="px-3 py-3 text-xs text-muted-foreground">No recent backend alerts.</div>
                  ) : (
                    recentNotifications.map((n) => (
                      <div
                        key={n.alertId}
                        className="px-3 py-2 border-b last:border-0 hover:bg-muted/50 cursor-pointer"
                        onClick={() => {
                          setNotifOpen(false);
                          navigate(`/graph?alert=${encodeURIComponent(n.alertId)}`);
                        }}
                      >
                        <p className="text-[13px] text-foreground">{n.text}</p>
                        <p className="text-[13px] text-muted-foreground mt-0.5">{n.time}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          <div className="w-px h-6 bg-white/20" />

          <div className="flex items-center gap-2 cursor-pointer">
              <div className="w-[34px] h-[34px] rounded-full bg-info flex items-center justify-center text-navbar-foreground text-[13px] font-bold">
              AK
            </div>
            <div className="hidden md:block">
              <div className="text-navbar-foreground text-[14px] font-semibold">Ajay Kumar</div>
              <div className="text-[13px]" style={{ color: "#93C5FD" }}>AML Investigator</div>
            </div>
          </div>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="px-6 pt-4 pb-0">
        <div className="text-[13px] text-muted-foreground">
          <span className="hover:text-primary cursor-pointer" onClick={() => navigate("/")}>Home</span>
          <span className="mx-1.5">›</span>
          <span className="text-foreground font-medium">{pageName}</span>
        </div>
      </div>

      <main className="flex-1 overflow-auto p-6 bg-background">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t bg-card/95 shrink-0">
        <div className="h-14 px-6 flex items-center justify-between gap-4">
          <div className="text-[12px] md:text-[13px] text-muted-foreground">
            <span className="font-semibold text-foreground">UniGRAPH</span>
            <span className="mx-2 text-border">|</span>
            <span>Copyright {currentYear} UniGRAPH. All rights reserved.</span>
          </div>
          <div className="hidden md:flex items-center gap-3 text-[12px] text-muted-foreground">
            <span>Financial Intelligence Platform</span>
            <span className="h-1 w-1 rounded-full bg-border" />
            <span>Compliance & Investigation Suite</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function AppLayout() {
  return (
    <SidebarProvider style={{ "--sidebar-width": "220px", "--sidebar-width-icon": "64px" } as React.CSSProperties}>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <AppContent />
      </div>
    </SidebarProvider>
  );
}
