import { useState, useRef, useEffect } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

const breadcrumbMap: Record<string, string> = {
  "/": "Dashboard Overview",
  "/alerts": "Alerts & Cases",
  "/graph": "Graph Explorer",
  "/copilot": "Investigator Copilot",
  "/transactions": "Transaction Monitor",
  "/str-generator": "STR Generator",
  "/test-cases": "Test Cases",
  "/settings": "Settings & Profile",
};

const recentNotifications = [
  { id: 1, text: "ALT-2024-0847: Rapid Layering detected — ₹20L", time: "10:12 IST" },
  { id: 2, text: "ALT-2024-0848: Round-Tripping flagged — ₹50L", time: "09:45 IST" },
  { id: 3, text: "ALT-2024-0849: Structuring alert — ₹4.9L", time: "08:30 IST" },
  { id: 4, text: "ALT-2024-0850: Dormant account activated — ₹1.5Cr", time: "07:00 IST" },
  { id: 5, text: "STR-UBI-2024-0041 accepted by FIU-IND", time: "Yesterday" },
];

function AppContent() {
  const location = useLocation();
  const navigate = useNavigate();

  const pageName = breadcrumbMap[location.pathname] || "Dashboard";
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifCount, setNotifCount] = useState(47);
  const dropdownRef = useRef<HTMLDivElement>(null);

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
            { dot: "bg-success", label: "System Online" },
            { dot: "bg-warning", label: "8,64,320 txn today" },
            { dot: "bg-danger", label: "47 Active Alerts" },
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
              {notifCount > 0 && (
                <span className="absolute -top-2 -right-2 flex items-center justify-center text-navbar-foreground bg-danger rounded-full px-1.5 text-[12px] font-bold min-w-[16px]">
                  {notifCount}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="absolute right-0 top-10 w-80 bg-card border border-border rounded-lg shadow-lg z-50">
                <div className="flex items-center justify-between p-3 border-b">
                  <span className="text-sm font-semibold text-foreground">Notifications</span>
                  <button onClick={() => setNotifCount(0)} className="text-xs text-primary hover:underline">
                    Mark all read
                  </button>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {recentNotifications.map((n) => (
                    <div
                      key={n.id}
                      className="px-3 py-2 border-b last:border-0 hover:bg-muted/50 cursor-pointer"
                      onClick={() => { setNotifOpen(false); navigate("/alerts"); }}
                    >
                      <p className="text-[13px] text-foreground">{n.text}</p>
                      <p className="text-[13px] text-muted-foreground mt-0.5">{n.time}</p>
                    </div>
                  ))}
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
      <footer className="h-10 border-t bg-card flex items-center justify-center shrink-0">
        <span className="text-[14px] text-muted-foreground">
           UniGRAPH © 2026 · Unified Banking Intelligence · Powered by FinGraph AI · Built for IDEA 2.0 Hackathon
        </span>
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
