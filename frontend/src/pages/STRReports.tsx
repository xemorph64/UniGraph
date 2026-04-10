import { useState } from "react";
import { 
  Shield, 
  Receipt, 
  RefreshCw, 
  Sparkles, 
  Copy, 
  RefreshCcw, 
  Search, 
  User, 
  Check, 
  FileType, 
  Save, 
  Maximize2,
  Building2,
  MapPin
} from "lucide-react";
import { motion } from "motion/react";
import { cn } from "@/src/lib/utils";

export default function STRReports() {
  const [step, setStep] = useState(2);

  return (
    <div className="p-8 bg-surface-dim overflow-x-hidden">
      <div className="max-w-5xl mx-auto mb-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-primary mb-2">
              <Shield className="w-4 h-4" />
              <span className="text-[0.65rem] font-bold uppercase tracking-[0.2em]">Enforcement Protocol</span>
            </div>
            <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Generate Suspicious Transaction Report</h1>
            <p className="text-on-surface-variant max-w-xl">Formalize findings for Case <span className="text-primary font-mono">#UBI-2024-88492</span>. Ensure all narrative sections meet regulatory compliance standards.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex -space-x-2">
              {[1, 2].map(i => (
                <img key={i} className="w-10 h-10 rounded-full border-2 border-surface-dim object-cover" src={`https://picsum.photos/seed/user${i}/100/100`} alt="Collaborator" referrerPolicy="no-referrer" />
              ))}
              <div className="w-10 h-10 rounded-full border-2 border-surface-dim bg-surface-container-highest flex items-center justify-center text-[10px] font-bold text-on-surface-variant">
                +2
              </div>
            </div>
            <div className="h-10 w-[1px] bg-outline-variant/20 mx-2"></div>
            <div className="text-right">
              <div className="text-[0.65rem] uppercase font-bold text-on-surface-variant tracking-wider">Priority</div>
              <div className="text-error font-bold flex items-center gap-1 justify-end">
                <span className="w-2 h-2 rounded-full bg-error"></span>
                CRITICAL
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Step Progress */}
      <div className="max-w-5xl mx-auto mb-12">
        <div className="relative flex justify-between">
          <div className="absolute top-5 left-0 w-full h-[2px] bg-surface-container-highest -z-0"></div>
          <div className="absolute top-5 left-0 w-2/3 h-[2px] bg-primary -z-0"></div>
          {[
            { n: 1, label: "Transactions" },
            { n: 2, label: "Narrative" },
            { n: 3, label: "Subject" },
            { n: 4, label: "Review" },
          ].map((s) => (
            <div key={s.n} className="relative z-10 flex flex-col items-center gap-3">
              <div className={cn(
                "w-10 h-10 rounded-full flex items-center justify-center font-bold ring-4 ring-surface-dim shadow-lg transition-all",
                s.n <= step ? "bg-primary text-on-primary" : "bg-surface-container-highest text-on-surface-variant"
              )}>
                {s.n}
              </div>
              <span className={cn(
                "text-[0.65rem] font-bold uppercase tracking-widest transition-colors",
                s.n <= step ? "text-primary" : "text-on-surface-variant"
              )}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-12 gap-8">
        <div className="col-span-12 lg:col-span-8 space-y-8">
          {/* Section 1: Transaction Details */}
          <section className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
                <Receipt className="text-primary w-5 h-5" />
                Transaction Foundation
              </h2>
              <button className="text-xs font-bold text-primary uppercase tracking-widest flex items-center gap-1 hover:underline">
                <RefreshCw className="w-3 h-3" />
                Refresh from Ledger
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Entity Reference ID</label>
                <input className="w-full bg-surface-container-highest border-0 rounded-lg text-on-surface focus:ring-1 focus:ring-primary text-sm font-mono p-3 outline-none" type="text" defaultValue="TRX-992-004-X"/>
              </div>
              <div className="space-y-2">
                <label className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Transaction Value (INR)</label>
                <div className="relative">
                  <input className="w-full bg-surface-container-highest border-0 rounded-lg text-on-surface focus:ring-1 focus:ring-primary text-sm font-mono p-3 pl-8 outline-none" type="text" defaultValue="4,50,000.00"/>
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-xs">₹</span>
                </div>
              </div>
              <div className="space-y-2 md:col-span-2">
                <label className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Risk Indicators Flagged</label>
                <div className="flex flex-wrap gap-2 pt-1">
                  {["Rapid Outflow", "Round Sums"].map(tag => (
                    <span key={tag} className="px-3 py-1 bg-tertiary-container text-on-tertiary-container rounded-full text-[10px] font-bold uppercase tracking-wider">{tag}</span>
                  ))}
                  <span className="px-3 py-1 bg-secondary-container text-on-secondary-container rounded-full text-[10px] font-bold uppercase tracking-wider">High Risk Geo</span>
                  <button className="px-3 py-1 bg-surface-container-highest text-primary border border-primary/20 rounded-full text-[10px] font-bold uppercase tracking-wider hover:bg-primary/10 transition-colors">+ Add Flag</button>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: LLM Narrative Box */}
          <section className="bg-surface-container rounded-xl p-6 border border-primary/20 glow-primary relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-3xl -mr-16 -mt-16"></div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
                <Sparkles className="text-primary w-5 h-5" />
                Intelligent Narrative Synthesis
              </h2>
              <div className="flex items-center gap-2 bg-primary-container px-3 py-1 rounded-lg">
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></span>
                <span className="text-[10px] font-bold text-primary uppercase tracking-wider">AI Drafting Active</span>
              </div>
            </div>
            <p className="text-xs text-on-surface-variant mb-4">The sentinel has analyzed transaction patterns and entity relationships to generate this draft. Review and refine for legal submission.</p>
            <div className="relative group">
              <textarea 
                className="w-full bg-surface-container-highest border-0 rounded-xl text-on-surface focus:ring-2 focus:ring-primary/50 text-sm leading-relaxed p-6 resize-none transition-all outline-none" 
                rows={8}
                defaultValue="The subject, ARAVIND CONSULTANCY SERVICES, initiated three sequential transfers of ₹1,50,000 each within a 24-hour window. This pattern circumvents the standard ₹2,00,000 internal audit threshold. Funds were routed through multiple intermediary shell accounts before being consolidated into a single offshore entity (LUX-INV-99). This structure suggests intentional layering and integration phases of money laundering. No clear business purpose for these transfers has been identified in the KYC documentation provided during onboarding."
              />
              <div className="absolute bottom-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-2 bg-surface-container-low text-on-surface-variant hover:text-primary rounded-lg shadow-xl"><Copy className="w-4 h-4" /></button>
                <button className="p-2 bg-surface-container-low text-on-surface-variant hover:text-primary rounded-lg shadow-xl"><RefreshCcw className="w-4 h-4" /></button>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4">
              <button className="text-[10px] font-bold text-primary bg-primary/10 px-4 py-2 rounded-lg hover:bg-primary/20 transition-all uppercase tracking-widest">Formalize Language</button>
              <button className="text-[10px] font-bold text-on-surface-variant bg-surface-container-highest px-4 py-2 rounded-lg hover:text-white transition-all uppercase tracking-widest">Expand details</button>
            </div>
          </section>

          {/* Section 3: Subject Details */}
          <section className="bg-surface-container-low rounded-xl p-6 border border-outline-variant/10">
            <h2 className="text-lg font-bold text-on-surface flex items-center gap-2 mb-6">
              <Search className="text-primary w-5 h-5" />
              Subject Identity
            </h2>
            <div className="flex items-start gap-6 mb-8 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/5">
              <div className="w-16 h-16 rounded-xl bg-surface-container-highest flex items-center justify-center">
                <Building2 className="w-8 h-8 text-primary" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-on-surface">ARAVIND CONSULTANCY SERVICES</h3>
                  <span className="px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded text-[10px] font-mono">PAN: ABZPAXXXXX</span>
                </div>
                <p className="text-xs text-on-surface-variant mt-1">Status: <span className="text-error font-semibold">Flagged Entity</span> • Active since 2018</p>
                <div className="flex gap-4 mt-3">
                  <div className="flex flex-col">
                    <span className="text-[0.6rem] text-on-surface-variant uppercase font-bold tracking-tighter">Connected Accounts</span>
                    <span className="text-xs font-mono">12 Active / 4 Suspended</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[0.6rem] text-on-surface-variant uppercase font-bold tracking-tighter">Risk Score</span>
                    <span className="text-xs font-mono text-error">88/100</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Primary Address</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-3 w-4 h-4 text-on-surface-variant" />
                  <textarea className="w-full bg-surface-container-highest border-0 rounded-lg text-on-surface focus:ring-1 focus:ring-primary text-xs p-3 pl-10 outline-none" rows={2} defaultValue="Suite 404, Tech Park East, Mumbai, Maharashtra 400001" />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Associated Person</label>
                <div className="flex items-center gap-3 bg-surface-container-highest p-3 rounded-lg">
                  <div className="w-8 h-8 rounded-full bg-surface-container flex items-center justify-center">
                    <User className="w-4 h-4 text-on-surface-variant" />
                  </div>
                  <span className="text-xs font-medium">Rajesh Kumar (Director)</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="col-span-12 lg:col-span-4 space-y-8">
          <div className="bg-surface-container-high rounded-xl p-6 border border-outline-variant/10 sticky top-24">
            <h3 className="text-[0.65rem] font-bold uppercase tracking-[0.2em] text-primary mb-6">Finalize Protocol</h3>
            <div className="space-y-4 mb-8">
              <div className="flex items-center gap-3 p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/10">
                <Check className="text-primary w-5 h-5" />
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Data Integrity</div>
                  <div className="text-xs font-semibold">Verified by Ledger</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/10">
                <FileType className="text-primary w-5 h-5" />
                <div>
                  <div className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Audit Trail</div>
                  <div className="text-xs font-semibold">Logging Sequence 04X</div>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <button className="w-full py-4 bg-primary text-on-primary font-bold rounded-xl active:scale-95 transition-transform flex items-center justify-center gap-2 glow-primary uppercase tracking-widest text-xs">
                Generate & Export to PDF
              </button>
              <button className="w-full py-3 bg-surface-container-highest text-on-surface font-bold rounded-xl active:scale-95 transition-transform flex items-center justify-center gap-2 border border-outline-variant/20 hover:bg-surface-container-highest/80 uppercase tracking-widest text-xs">
                <Save className="w-4 h-4" />
                Save Draft
              </button>
            </div>
            <div className="mt-8 pt-6 border-t border-outline-variant/15">
              <h4 className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant mb-4">Submission Check-list</h4>
              <ul className="space-y-3">
                {[
                  { label: "FIU-IND Format Compliant", checked: true },
                  { label: "Narrative word count (>200)", checked: true },
                  { label: "Supporting docs attached", checked: false },
                ].map((item) => (
                  <li key={item.label} className="flex items-center gap-3 text-xs">
                    <span className={cn(
                      "w-4 h-4 rounded flex items-center justify-center",
                      item.checked ? "bg-primary/20 text-primary" : "bg-surface-container-highest text-on-surface-variant"
                    )}>
                      {item.checked && <Check className="w-3 h-3" />}
                    </span>
                    {item.label}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="bg-surface-container-low rounded-xl overflow-hidden border border-outline-variant/10">
            <div className="p-4 border-b border-outline-variant/10 flex justify-between items-center">
              <span className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">Entity Context</span>
              <Maximize2 className="w-3 h-3 text-primary" />
            </div>
            <div className="aspect-square bg-surface-container-lowest relative group cursor-crosshair">
              <img className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity" src="https://picsum.photos/seed/graph/400/400" alt="Graph Context" referrerPolicy="no-referrer" />
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="p-2 bg-primary/10 border border-primary/40 rounded backdrop-blur-sm">
                  <span className="text-[8px] font-bold text-primary uppercase tracking-[0.2em]">Live Investigation Map</span>
                </div>
              </div>
            </div>
            <div className="p-4 bg-surface-container-low">
              <p className="text-[10px] leading-relaxed text-on-surface-variant italic">Showing 3rd-degree connections. Red nodes indicate high-risk offshore recipients.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
