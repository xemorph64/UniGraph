import { useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { User, Shield, Bell, Server, Save } from "lucide-react";
import { toast } from "sonner";

export default function SettingsPage() {
  const [velocityThreshold, setVelocityThreshold] = useState([500]);
  const [dormancyPeriod, setDormancyPeriod] = useState([12]);
  const [structuringAmount, setStructuringAmount] = useState("10,00,000");
  const [muleAge, setMuleAge] = useState("45");
  const [minHops, setMinHops] = useState([3]);
  const [saving, setSaving] = useState(false);

  const [modules, setModules] = useState({
    layering: true, roundTrip: true, structuring: true, dormant: true, profile: true, mule: true,
  });
  const [notifications, setNotifications] = useState({
    email: true, sms: false, inApp: true, strReminder: true,
  });

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast.success("Settings saved successfully");
    }, 1500);
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-primary">Settings & Profile</h1>
          <p className="text-xs text-muted-foreground mt-1">Configure detection thresholds and notification preferences</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-semibold flex items-center gap-2 cursor-pointer hover:bg-primary/90 disabled:opacity-60"
        >
          <Save className="w-4 h-4" /> {saving ? "Saving..." : "Save Settings"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* User Profile */}
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

        {/* Alert Thresholds */}
        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
            <Shield className="w-4 h-4" /> Alert Thresholds
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Velocity Threshold</span><span className="font-bold">{velocityThreshold[0]}%</span></div>
              <Slider value={velocityThreshold} onValueChange={setVelocityThreshold} min={100} max={1000} step={50} />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Dormancy Period Alert</span><span className="font-bold">{dormancyPeriod[0]} months</span></div>
              <Slider value={dormancyPeriod} onValueChange={setDormancyPeriod} min={3} max={36} step={1} />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Structuring Threshold (₹)</label>
              <input value={structuringAmount} onChange={(e) => setStructuringAmount(e.target.value)} className="w-full bg-background border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Mule Account Age (days)</label>
              <input value={muleAge} onChange={(e) => setMuleAge(e.target.value)} className="w-full bg-background border border-border rounded-md py-1.5 px-2 mt-1 text-xs text-foreground" />
            </div>
            <div>
              <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Min Hop Count</span><span className="font-bold">{minHops[0]}</span></div>
              <Slider value={minHops} onValueChange={setMinHops} min={2} max={10} step={1} />
            </div>
          </div>
        </div>

        {/* Detection Modules */}
        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide mb-4">Detection Modules</div>
          <div className="space-y-3">
            {[
              { key: "layering", label: "Rapid Layering Detection" },
              { key: "roundTrip", label: "Round-Trip / Circular Flow" },
              { key: "structuring", label: "Structuring / Smurfing" },
              { key: "dormant", label: "Dormant Account Activation" },
              { key: "profile", label: "Customer Profile Mismatch" },
              { key: "mule", label: "Mule Account Detection" },
            ].map((m) => (
              <div key={m.key} className="flex items-center justify-between">
                <span className="text-xs text-foreground">{m.label}</span>
                <Switch checked={(modules as any)[m.key]} onCheckedChange={(v) => setModules({ ...modules, [m.key]: v as boolean })} />
              </div>
            ))}
          </div>
        </div>

        {/* Notification Settings */}
        <div className="bg-card border border-border rounded-[10px] p-5">
          <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4" /> Notification Settings
          </div>
          <div className="space-y-3">
            {[
              { key: "email", label: "Email Alerts" },
              { key: "sms", label: "SMS Alerts" },
              { key: "inApp", label: "In-App Notifications" },
              { key: "strReminder", label: "STR Deadline Reminders" },
            ].map((n) => (
              <div key={n.key} className="flex items-center justify-between">
                <span className="text-xs text-foreground">{n.label}</span>
                <Switch checked={(notifications as any)[n.key]} onCheckedChange={(v) => setNotifications({ ...notifications, [n.key]: v as boolean })} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-card border border-border rounded-[10px] p-5">
        <div className="text-xs font-semibold text-foreground uppercase tracking-wide flex items-center gap-2 mb-4">
          <Server className="w-4 h-4" /> System Status
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { name: "Neo4j Graph DB", status: "Online", detail: "99.97% uptime" },
            { name: "Kafka Stream", status: "Active", detail: "864K txn/day" },
            { name: "ML Engine", status: "Running", detail: "XGBoost + GNN + IF" },
            { name: "FIU-IND API", status: "Connected", detail: "FINnet 2.0" },
            { name: "Qwen LLM", status: "Available", detail: "v3.5 9B loaded" },
          ].map((s) => (
            <div key={s.name} className="text-center p-3 bg-muted/50 rounded-lg">
              <div className="text-xs font-semibold text-foreground">{s.name}</div>
              <div className="text-[10px] text-success font-medium mt-1 flex items-center justify-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-success" />
                {s.status}
              </div>
              <div className="text-[10px] text-muted-foreground">{s.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
