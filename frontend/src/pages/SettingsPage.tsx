import { useCallback, useEffect, useMemo, useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Bell, Save, Server, Shield, User } from "lucide-react";
import { toast } from "sonner";
import {
  getBackendHealth,
  getGraphAnalyticsStatus,
  getMlHealth,
  listAlerts,
  type BackendHealthResponse,
  type GraphAnalyticsStatusResponse,
  type MlHealthResponse,
} from "@/lib/unigraph-api";

interface LocalSettings {
  velocityThreshold: number[];
  dormancyPeriod: number[];
  structuringAmount: string;
  muleAge: string;
  minHops: number[];
  modules: Record<string, boolean>;
  notifications: Record<string, boolean>;
}

const SETTINGS_STORAGE_KEY = "unigraph-local-settings";

const defaultLocalSettings: LocalSettings = {
  velocityThreshold: [500],
  dormancyPeriod: [12],
  structuringAmount: "10,00,000",
  muleAge: "45",
  minHops: [3],
  modules: {
    layering: true,
    roundTrip: true,
    structuring: true,
    dormant: true,
    profile: true,
    mule: true,
  },
  notifications: {
    email: true,
    sms: false,
    inApp: true,
    strReminder: true,
  },
};

function safeLoadSettings(): LocalSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) return defaultLocalSettings;
    const parsed = JSON.parse(raw) as LocalSettings;
    return {
      ...defaultLocalSettings,
      ...parsed,
      modules: { ...defaultLocalSettings.modules, ...(parsed.modules || {}) },
      notifications: { ...defaultLocalSettings.notifications, ...(parsed.notifications || {}) },
    };
  } catch {
    return defaultLocalSettings;
  }
}

function liveStatusLabel(isHealthy: boolean, healthyLabel = "Online", unhealthyLabel = "Offline"): string {
  return isHealthy ? healthyLabel : unhealthyLabel;
}

export default function SettingsPage() {
  const [settingsState, setSettingsState] = useState<LocalSettings>(defaultLocalSettings);
  const [saving, setSaving] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [backendHealth, setBackendHealth] = useState<BackendHealthResponse | null>(null);
  const [graphStatus, setGraphStatus] = useState<GraphAnalyticsStatusResponse | null>(null);
  const [mlHealth, setMlHealth] = useState<MlHealthResponse | null>(null);
  const [alertCount, setAlertCount] = useState(0);

  const refreshLiveStatus = useCallback(async () => {
    setStatusLoading(true);
    try {
      const [backend, graph, ml, alerts] = await Promise.all([
        getBackendHealth(),
        getGraphAnalyticsStatus(),
        getMlHealth(),
        listAlerts({ page: 1, pageSize: 1 }),
      ]);

      setBackendHealth(backend);
      setGraphStatus(graph);
      setMlHealth(ml);
      setAlertCount(alerts.total || alerts.items.length);
      setStatusError(null);
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : "Unable to fetch live status");
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    setSettingsState(safeLoadSettings());
    void refreshLiveStatus();
    const poller = setInterval(() => {
      void refreshLiveStatus();
    }, 20000);
    return () => clearInterval(poller);
  }, [refreshLiveStatus]);

  const handleSave = () => {
    setSaving(true);
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settingsState));
    setTimeout(() => {
      setSaving(false);
      toast.success("Settings saved locally");
    }, 350);
  };

  const systemCards = useMemo(() => {
    const neo4jOnline = backendHealth?.neo4j === "connected";
    const mlOnline = mlHealth?.status === "healthy";
    const gdsReady = graphStatus?.status === "ok";
    const totalAccounts = graphStatus?.gds?.total_accounts || 0;
    const analyzedAccounts = graphStatus?.gds?.with_pagerank || 0;

    return [
      {
        name: "Backend API",
        status: liveStatusLabel(backendHealth?.status === "healthy"),
        detail: backendHealth ? `version ${backendHealth.version}` : "No data",
        ok: backendHealth?.status === "healthy",
      },
      {
        name: "Neo4j Graph DB",
        status: liveStatusLabel(neo4jOnline),
        detail: neo4jOnline ? `${backendHealth?.graph_stats?.total_accounts || 0} accounts` : "Disconnected",
        ok: neo4jOnline,
      },
      {
        name: "Graph Analytics",
        status: liveStatusLabel(gdsReady, "Ready", "Unavailable"),
        detail: gdsReady ? `${analyzedAccounts}/${totalAccounts} with PageRank` : "No analytics status",
        ok: gdsReady,
      },
      {
        name: "ML Engine",
        status: liveStatusLabel(mlOnline, "Running", "Unavailable"),
        detail: mlOnline ? mlHealth?.model_version || "healthy" : "No response on ML health",
        ok: mlOnline,
      },
      {
        name: "Alert Stream",
        status: liveStatusLabel(alertCount > 0, "Active", "Idle"),
        detail: `${alertCount} current alerts`,
        ok: true,
      },
    ];
  }, [backendHealth, graphStatus, mlHealth, alertCount]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-primary">Settings & Profile</h1>
          <p className="text-xs text-muted-foreground mt-1">Live system status + local investigator preferences</p>
          <p className="text-[11px] text-muted-foreground mt-1">Threshold and notification controls are local preferences until a settings API is added.</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-semibold flex items-center gap-2 cursor-pointer hover:bg-primary/90 disabled:opacity-60"
        >
          <Save className="w-4 h-4" /> {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>

      {statusError && <p className="text-xs text-danger">{statusError}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
            <User className="w-4 h-4" /> User Profile
          </div>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-14 h-14 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-lg font-bold">AK</div>
            <div>
              <div className="font-semibold text-foreground">Ajay Kumar</div>
              <div className="text-xs text-muted-foreground">EMP-4421 | Mumbai Main Branch</div>
              <div className="text-xs text-muted-foreground">Role: AML Investigator</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="text-muted-foreground">Employee ID</label>
              <input value="EMP-4421" readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs font-mono text-foreground" />
            </div>
            <div>
              <label className="text-muted-foreground">Branch</label>
              <input value="Mumbai Main" readOnly className="w-full bg-muted border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs mt-3">
            <Shield className="w-4 h-4 text-success" />
            <span>Digital Signature Status:</span>
            <span className="bg-success/10 text-success text-[10px] font-bold px-2 py-0.5 rounded">Active</span>
          </div>
        </div>

        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4" /> Alert Thresholds (Local)
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Velocity Threshold</span><span className="font-bold">{settingsState.velocityThreshold[0]}%</span></div>
              <Slider value={settingsState.velocityThreshold} onValueChange={(value) => setSettingsState((prev) => ({ ...prev, velocityThreshold: value }))} min={100} max={1000} step={50} />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Dormancy Period Alert</span><span className="font-bold">{settingsState.dormancyPeriod[0]} months</span></div>
              <Slider value={settingsState.dormancyPeriod} onValueChange={(value) => setSettingsState((prev) => ({ ...prev, dormancyPeriod: value }))} min={3} max={36} step={1} />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Structuring Threshold (INR)</label>
              <input value={settingsState.structuringAmount} onChange={(event) => setSettingsState((prev) => ({ ...prev, structuringAmount: event.target.value }))} className="w-full bg-background border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Mule Account Age (days)</label>
              <input value={settingsState.muleAge} onChange={(event) => setSettingsState((prev) => ({ ...prev, muleAge: event.target.value }))} className="w-full bg-background border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Min Hop Count</span><span className="font-bold">{settingsState.minHops[0]}</span></div>
              <Slider value={settingsState.minHops} onValueChange={(value) => setSettingsState((prev) => ({ ...prev, minHops: value }))} min={2} max={10} step={1} />
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-4">Detection Modules (Local Toggles)</div>
          <div className="space-y-3">
            {[
              { key: "layering", label: "Rapid Layering Detection" },
              { key: "roundTrip", label: "Round-Trip / Circular Flow" },
              { key: "structuring", label: "Structuring / Smurfing" },
              { key: "dormant", label: "Dormant Account Activation" },
              { key: "profile", label: "Customer Profile Mismatch" },
              { key: "mule", label: "Mule Account Detection" },
            ].map((module) => (
              <div key={module.key} className="flex items-center justify-between">
                <span className="text-xs text-foreground">{module.label}</span>
                <Switch
                  checked={settingsState.modules[module.key]}
                  onCheckedChange={(value) =>
                    setSettingsState((prev) => ({
                      ...prev,
                      modules: { ...prev.modules, [module.key]: value as boolean },
                    }))
                  }
                />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4" /> Notification Settings (Local)
          </div>
          <div className="space-y-3">
            {[
              { key: "email", label: "Email Alerts" },
              { key: "sms", label: "SMS Alerts" },
              { key: "inApp", label: "In-App Notifications" },
              { key: "strReminder", label: "STR Deadline Reminders" },
            ].map((notification) => (
              <div key={notification.key} className="flex items-center justify-between">
                <span className="text-xs text-foreground">{notification.label}</span>
                <Switch
                  checked={settingsState.notifications[notification.key]}
                  onCheckedChange={(value) =>
                    setSettingsState((prev) => ({
                      ...prev,
                      notifications: { ...prev.notifications, [notification.key]: value as boolean },
                    }))
                  }
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-[10px] p-5">
        <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
          <Server className="w-4 h-4" /> System Status (Live)
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {systemCards.map((card) => (
            <div key={card.name} className="text-center p-3 bg-muted/50 rounded-lg">
              <div className="text-xs font-semibold text-foreground">{card.name}</div>
              <div className={`text-[10px] font-medium mt-1 flex items-center justify-center gap-1 ${card.ok ? "text-success" : "text-danger"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${statusLoading ? "bg-warning" : card.ok ? "bg-success" : "bg-danger"}`} />
                {statusLoading ? "Loading" : card.status}
              </div>
              <div className="text-[10px] text-muted-foreground">{card.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
