import { NavLink } from "react-router-dom";
import { 
  LayoutDashboard, 
  Share2, 
  AlertTriangle, 
  FileText, 
  Plus, 
  HelpCircle, 
  LogOut,
  Shield
} from "lucide-react";
import { cn } from "@/src/lib/utils";

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
  { icon: Share2, label: "Graph Explorer", path: "/graph-explorer" },
  { icon: AlertTriangle, label: "Alerts", path: "/alerts" },
  { icon: FileText, label: "STR Reports", path: "/str-reports" },
];

export default function Sidebar() {
  return (
    <aside className="h-screen w-64 fixed left-0 top-0 overflow-y-auto bg-surface-container-low flex flex-col py-8 z-50 border-r border-outline-variant/10">
      <div className="px-6 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary rounded flex items-center justify-center">
            <Shield className="text-on-primary w-5 h-5" />
          </div>
          <div>
            <h1 className="text-primary font-black text-xl tracking-tighter">UniGRAPH</h1>
            <p className="text-[0.625rem] text-on-surface-variant uppercase tracking-[0.2em] font-bold">Vigilant Sentinel</p>
          </div>
        </div>
      </div>

      <nav className="flex-grow space-y-1 px-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-medium tracking-wide uppercase text-sm group",
              isActive 
                ? "text-primary bg-surface-container-high border-l-2 border-primary" 
                : "text-on-surface-variant hover:bg-surface-container-high hover:text-white"
            )}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-6 mt-8">
        <button className="w-full bg-primary text-on-primary py-3 rounded-xl font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2 active:scale-95 transition-transform">
          <Plus className="w-4 h-4" />
          New Investigation
        </button>
      </div>

      <div className="mt-auto px-6 space-y-1 pt-4 border-t border-outline-variant/10">
        <a className="flex items-center gap-3 py-3 text-on-surface-variant hover:text-white transition-all font-medium tracking-wide uppercase text-sm" href="#">
          <HelpCircle className="w-5 h-5" />
          Support
        </a>
        <a className="flex items-center gap-3 py-3 text-on-surface-variant hover:text-white transition-all font-medium tracking-wide uppercase text-sm" href="#">
          <LogOut className="w-5 h-5" />
          Logout
        </a>
      </div>
    </aside>
  );
}
