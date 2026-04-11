import { LayoutDashboard, AlertTriangle, GitGraph, Monitor, FileText, Bot, Settings } from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { alertCards } from "@/data/alerts-data";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const alertCount = alertCards.length;

const mainItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Alerts & Cases", url: "/alerts", icon: AlertTriangle, badge: alertCount },
  { title: "Graph Explorer", url: "/graph", icon: GitGraph },
  { title: "Transaction Monitor", url: "/transactions", icon: Monitor },
  { title: "STR Generator", url: "/str-generator", icon: FileText },
  { title: "Investigator Copilot", url: "/copilot", icon: Bot },
];

export function AppSidebar() {
  const { state, toggleSidebar } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  const isActive = (url: string) => url === "/" ? location.pathname === "/" : location.pathname.startsWith(url);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-0">
        {collapsed ? (
          <div className="flex flex-col items-center gap-2 py-3 border-b border-white/10">
            <button
              onClick={toggleSidebar}
              className="w-7 h-7 rounded-md flex items-center justify-center text-white/60 hover:text-white bg-white/10 border border-white/15 cursor-pointer text-sm"
            >
              ☰
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-between px-4 py-4 pb-3 border-b border-white/10">
            <div>
              <div className="text-white font-extrabold text-[18px] tracking-wide leading-tight">UniGRAPH</div>
               <div className="text-white/50 text-[12px] tracking-[2px] uppercase font-medium">Unified Banking Intelligence</div>
            </div>
            <button
              onClick={toggleSidebar}
              className="w-7 h-7 rounded-md flex items-center justify-center text-white/60 hover:text-white bg-white/10 border border-white/15 cursor-pointer text-sm shrink-0"
            >
              ☰
            </button>
          </div>
        )}
      </SidebarHeader>

      <SidebarContent className="pt-2">
        <SidebarGroup>
          {!collapsed && (
            <SidebarGroupLabel className="text-white/40 text-[13px] tracking-[2px] uppercase font-medium">
              Navigation
            </SidebarGroupLabel>
          )}
          <SidebarGroupContent>
            <SidebarMenu>
              {mainItems.map((item) => {
                const active = isActive(item.url);
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton asChild>
                      {collapsed ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <NavLink
                              to={item.url}
                              end={item.url === "/"}
                              className={`flex items-center justify-center rounded-md mx-1 py-2.5 ${active ? "bg-info text-white" : "text-white/60 hover:bg-white/10 hover:text-white"}`}
                              style={active ? { borderLeft: "3px solid hsl(var(--danger))" } : undefined}
                            >
                              <item.icon className="h-4 w-4 shrink-0" />
                            </NavLink>
                          </TooltipTrigger>
                          <TooltipContent side="right">{item.title}</TooltipContent>
                        </Tooltip>
                      ) : (
                        <NavLink
                          to={item.url}
                          end={item.url === "/"}
                          className={`flex items-center gap-2.5 rounded-md mx-1 px-4 py-2.5 text-[16px] font-medium ${active ? "bg-info text-white font-semibold" : "text-white/60 hover:bg-white/10 hover:text-white"}`}
                          style={active ? { borderLeft: "3px solid hsl(var(--danger))" } : undefined}
                        >
                          <item.icon className="h-4 w-4 shrink-0" />
                          <span className="flex items-center gap-2">
                            {item.title}
                            {item.badge && (
                              <span className="bg-danger text-white text-[12px] font-bold px-1.5 py-0.5 rounded-sm leading-none">
                                {item.badge}
                              </span>
                            )}
                          </span>
                        </NavLink>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Settings at bottom of content */}
        <SidebarGroup className="mt-auto">
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  {collapsed ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <NavLink
                          to="/settings"
                          className={`flex items-center justify-center rounded-md mx-1 py-2.5 ${isActive("/settings") ? "bg-info text-white" : "text-white/60 hover:bg-white/10 hover:text-white"}`}
                        >
                          <Settings className="h-4 w-4" />
                        </NavLink>
                      </TooltipTrigger>
                      <TooltipContent side="right">Settings</TooltipContent>
                    </Tooltip>
                  ) : (
                    <NavLink
                      to="/settings"
                      className={`flex items-center gap-2.5 rounded-md mx-1 px-4 py-2.5 text-[13px] font-medium ${isActive("/settings") ? "bg-info text-white font-semibold" : "text-white/60 hover:bg-white/10 hover:text-white"}`}
                    >
                      <Settings className="h-4 w-4 shrink-0" />
                      Settings
                    </NavLink>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {!collapsed && (
        <SidebarFooter className="pb-3">
          <div className="bg-black/15 rounded-lg mx-1 flex items-center gap-2.5 px-3 py-2.5">
            <div className="w-8 h-8 rounded-full bg-info flex items-center justify-center text-white text-[14px] font-bold shrink-0">
              AK
            </div>
            <div className="min-w-0">
              <div className="text-white text-[14px] font-semibold truncate">Ajay Kumar</div>
              <div className="text-white/50 text-[13px] flex items-center gap-1">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-success" />
                AML Investigator
              </div>
            </div>
          </div>
        </SidebarFooter>
      )}
    </Sidebar>
  );
}
