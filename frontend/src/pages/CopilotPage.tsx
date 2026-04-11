import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Bot, Send } from "lucide-react";
import { alertCards } from "@/data/alerts-data";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import { toast } from "sonner";

const caseFacts: Record<string, string[]> = {
  "ALT-2024-0847": [
    "₹20L received in single NEFT transfer",
    "Split across 4 accounts within 12 minutes",
    "All destination accounts opened < 3 months ago",
    "3 accounts share same device fingerprint",
    "Funds fully withdrawn within 2 hours",
  ],
};

const defaultFacts = [
  "Transaction flagged by AI risk engine",
  "Pattern matches known fraud typology",
  "Account activity deviates from baseline",
  "Multiple risk indicators triggered simultaneously",
];

const suggestions = [
  "Summarize this case",
  "Should I file an STR?",
  "What pattern is this?",
  "Who are the key accounts?",
  "Show similar past cases",
  "What's the risk level?",
];

interface Message {
  role: "assistant" | "user";
  content: string;
  time: string;
}

function getTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function getResponse(text: string, alert: typeof alertCards[0]): string {
  const t = text.toLowerCase();
  if (t.includes("summarize") || t.includes("summary")) {
    return `📋 **Case Summary — ${alert.id}**

**Fraud Type:** ${alert.fraudType}
**Risk Level:** 🔴 ${alert.riskScore >= 90 ? "Critical" : alert.riskScore >= 80 ? "High" : "Medium"}

**What happened:**
On ${alert.timeDetected}, account ${alert.account} was flagged for ${alert.fraudType}. ${alert.description}

**Key red flags:**
✗ ${alert.shapReason}
✗ Transaction chain: ${alert.transactionChain}
✗ KYC Status: ${alert.kycStatus}

**My recommendation:**
${alert.recommendedAction}. Confidence: High.`;
  }
  if (t.includes("str") || t.includes("file") || t.includes("report") || t.includes("should i")) {
    return `Based on my analysis of ${alert.id}:

✅ **STR Filing is RECOMMENDED**

**Reasons:**
1. Amount ${alert.amount} triggers reporting threshold (PMLA Section 12)
2. ${alert.fraudType} pattern confirmed (FATF Typology)
3. ${alert.shapReason}
4. KYC Status: ${alert.kycStatus}

**Deadline:** File within 7 days of detection.

I can auto-draft the STR if you click 'Generate STR' below.`;
  }
  if (t.includes("pattern") || t.includes("what is") || t.includes("type")) {
    return `🔍 **Pattern Analysis: ${alert.fraudType}**

This case matches a known FATF Typology pattern.

**How it works:**
${alert.description}

**Transaction chain:**
${alert.transactionChain}

**Key indicator:** ${alert.shapReason}`;
  }
  if (t.includes("account") || t.includes("who") || t.includes("key")) {
    return `🏦 **Key Accounts in This Case:**

**Primary Account (Flagged):**
• ${alert.account} — ${alert.amount}, KYC: ${alert.kycStatus}
  Risk: ${alert.riskScore >= 90 ? "Critical" : "High"} | Channel: ${alert.channel}

**Transaction Chain:**
${alert.transactionChain}`;
  }
  if (t.includes("risk") || t.includes("score") || t.includes("level")) {
    return `⚠️ **Risk Assessment: ${getRiskLabel(alert.riskScore)} (Score ${alert.riskScore}/100)**

**Risk factors:**
• ${alert.shapReason}
• KYC: ${alert.kycStatus}
• Amount: ${alert.amount}
• Channel: ${alert.channel}

This case is in the **top 5%** of alerts by risk score this month.

**Recommended action:** ${alert.recommendedAction}`;
  }
  if (t.includes("similar") || t.includes("past") || t.includes("cases")) {
    return `📂 **Similar Cases Found: 4 matches**

1. **ALT-2024-0722** — ${alert.fraudType}, ₹18L — STR Filed ✅
2. **ALT-2024-0698** — ${alert.fraudType}, ₹25L — Confirmed Fraud ✅
3. **ALT-2024-0634** — ${alert.fraudType}, ₹14L — STR Filed ✅
4. **ALT-2024-0589** — ${alert.fraudType}, ₹31L — Escalated to RBI

Conviction rate for this pattern: **78%**`;
  }
  return `I can help you analyze this case. Try asking:
• "Summarize this case"
• "Should I file an STR?"
• "What pattern is this?"
• "Who are the key accounts?"
• "What is the risk level?"`;
}

function getGreeting(alert: typeof alertCards[0]): Message {
  return {
    role: "assistant",
    content: `Hello Ajay 👋 I'm your Investigator Copilot.

I've loaded case **${alert.id}** — a ${alert.riskScore >= 90 ? "Critical" : "High"} ${alert.fraudType} alert on account ${alert.account} involving ${alert.amount}.

I can help you:
• Analyze the fraud pattern
• Decide whether to file an STR
• Identify key accounts in the network
• Draft investigation notes

What would you like to know?`,
    time: getTime(),
  };
}

export default function CopilotPage() {
  const navigate = useNavigate();
  const [selectedCase, setSelectedCase] = useState("ALT-2024-0847");
  const activeAlert = alertCards.find((a) => a.id === selectedCase) || alertCards[0];
  const [messages, setMessages] = useState<Message[]>([getGreeting(activeAlert)]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const facts = caseFacts[selectedCase] || defaultFacts;

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const handleCaseChange = useCallback((id: string) => {
    setSelectedCase(id);
    const alert = alertCards.find(a => a.id === id) || alertCards[0];
    setMessages([getGreeting(alert)]);
    setInput("");
  }, []);

  function sendMessage(text: string) {
    if (!text.trim()) return;
    const userMsg: Message = { role: "user", content: text.trim(), time: getTime() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setThinking(true);
    setTimeout(() => {
      setThinking(false);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: getResponse(text, activeAlert), time: getTime() },
      ]);
    }, 1200);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-10 gap-4" style={{ minHeight: "calc(100vh - 200px)" }}>
      {/* LEFT — Case Context */}
      <div className="lg:col-span-3 space-y-3">
        <div className="bg-card border border-border rounded-[10px] p-4">
          <div className="text-sm font-bold text-primary mb-3">Active Case Context</div>

          <label className="text-[11px] text-muted-foreground mb-1 block">Load a case:</label>
          <select
            value={selectedCase}
            onChange={(e) => handleCaseChange(e.target.value)}
            className="w-full bg-background border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer mb-3"
          >
            {alertCards.map((a) => (
              <option key={a.id} value={a.id}>{a.id} — {a.fraudType}</option>
            ))}
          </select>

          {/* Case Card */}
          <div className="bg-muted/50 rounded-lg p-3 mb-4" style={{ borderLeft: `3px solid ${getRiskColor(activeAlert.riskScore)}` }}>
            <div className="text-sm font-bold text-foreground">{activeAlert.id}</div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white" style={{ background: getRiskColor(activeAlert.riskScore) }}>
                {getRiskLabel(activeAlert.riskScore)}
              </span>
              <span className="text-xs text-foreground">{activeAlert.fraudType}</span>
            </div>
            <div className="mt-2 space-y-1 text-xs text-foreground">
              <div>Account: <span className="font-mono">{activeAlert.account}</span></div>
              <div>Amount: <span className="font-semibold">{activeAlert.amount}</span></div>
              <div>Date: {activeAlert.timeDetected}</div>
              <div>Status: Under Investigation</div>
            </div>
            <div className="mt-2">
              <RiskScoreBar score={activeAlert.riskScore} size="sm" />
            </div>
          </div>

          {/* What we know */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-primary mb-2">What we know:</div>
            <ul className="space-y-1">
              {facts.map((f, i) => (
                <li key={i} className="text-xs text-foreground leading-relaxed">• {f}</li>
              ))}
            </ul>
          </div>

          {/* Quick Prompts */}
          <div className="mb-4">
            <div className="text-[11px] text-muted-foreground mb-2">Ask Copilot:</div>
            <div className="grid grid-cols-2 gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="bg-info/10 text-info border border-info/20 rounded-full px-3 py-1.5 text-[11px] text-left cursor-pointer hover:bg-info/15"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Copilot Actions */}
        <div className="bg-card border border-border rounded-lg p-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-muted-foreground mr-1">Copilot Actions:</span>
          <button onClick={() => navigate(`/graph?alert=${selectedCase}`)} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer">
            🕸 View Case Graph
          </button>
          <button onClick={() => navigate(`/str-generator?alert=${selectedCase}`)} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer">
            📋 Generate STR
          </button>
          <button onClick={() => toast.success("Chat log exported")} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer">
            📁 Export Chat Log
          </button>
        </div>
      </div>

      {/* RIGHT — Chat */}
      <div className="lg:col-span-7 flex flex-col gap-3">
        <div className="bg-card border border-border rounded-[10px] overflow-hidden flex flex-col flex-1">
          {/* Chat Header */}
          <div className="bg-primary px-5 py-3.5 flex items-center gap-3">
            <div className="bg-danger w-9 h-9 rounded-full flex items-center justify-center shrink-0">
              <Bot className="w-[18px] h-[18px] text-white" />
            </div>
            <div className="flex-1">
              <div className="text-white font-bold text-sm">Investigator Copilot</div>
              <div className="text-[11px]" style={{ color: "#93C5FD" }}>Powered by Qwen 3.5 9B · Analyzing case context</div>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-success" />
              <span className="text-[11px]" style={{ color: "#93C5FD" }}>Ready</span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 bg-background space-y-4 scrollbar-thin" style={{ minHeight: 300 }}>
            {messages.map((m, i) =>
              m.role === "assistant" ? (
                <div key={i} className="flex gap-2 items-start max-w-[85%]">
                  <div className="bg-danger w-7 h-7 rounded-full flex items-center justify-center shrink-0">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div>
                    <div className="bg-card border border-border rounded-xl rounded-tl-none p-3.5 text-[13px] text-foreground leading-relaxed whitespace-pre-wrap">
                      {m.content.split(/(\*\*.*?\*\*)/).map((part, pi) =>
                        part.startsWith("**") && part.endsWith("**") ? (
                          <strong key={pi}>{part.slice(2, -2)}</strong>
                        ) : (
                          <span key={pi}>{part}</span>
                        )
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1">{m.time}</div>
                  </div>
                </div>
              ) : (
                <div key={i} className="flex gap-2 items-start self-end ml-auto max-w-[80%] flex-row-reverse">
                  <div className="bg-info w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white text-[10px] font-bold">
                    AK
                  </div>
                  <div>
                    <div className="bg-primary text-primary-foreground rounded-xl rounded-tr-none p-3 text-[13px] leading-relaxed whitespace-pre-wrap">
                      {m.content}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1 text-right">{m.time}</div>
                  </div>
                </div>
              )
            )}
            {thinking && (
              <div className="flex gap-2 items-start max-w-[85%]">
                <div className="bg-danger w-7 h-7 rounded-full flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-card border border-border rounded-xl rounded-tl-none p-3.5 text-[13px] text-muted-foreground italic flex items-center gap-1">
                  Copilot is thinking
                  <span className="animate-thinking-dot-1">●</span>
                  <span className="animate-thinking-dot-2">●</span>
                  <span className="animate-thinking-dot-3">●</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <div className="bg-card border-t border-border px-4 py-3 flex gap-3 items-center">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
              placeholder="Ask anything about this case..."
              className="flex-1 bg-background border border-border rounded-full px-4 py-2.5 text-[13px] text-foreground outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              onClick={() => sendMessage(input)}
              className="bg-primary text-white rounded-full w-10 h-10 flex items-center justify-center cursor-pointer hover:bg-primary/90 shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
