import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bot, Send } from "lucide-react";
import RiskScoreBar, { getRiskColor, getRiskLabel } from "@/components/RiskScoreBar";
import {
  investigateAlert,
  listAlerts,
  listStrReports,
  listTransactions,
  toAlertCard,
  type AlertCardLike,
  type InvestigationResponse,
} from "@/lib/unigraph-api";
import { toast } from "sonner";

interface Message {
  role: "assistant" | "user";
  content: string;
  time: string;
}

const suggestions = [
  "Summarize this case",
  "Should I file an STR?",
  "What pattern is this?",
  "Who are the key accounts?",
  "Show similar past cases",
  "What's the risk level?",
];

function getTime() {
  return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function prettifyFlag(flag: string): string {
  return flag
    .toLowerCase()
    .split("_")
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

function buildFacts(alert: AlertCardLike | undefined, investigation: InvestigationResponse | null): string[] {
  if (!alert) return ["No live alert selected", "Select an alert to load investigation context"];

  const facts: string[] = [
    `Risk score ${alert.riskScore}/100 (${getRiskLabel(alert.riskScore)}) on account ${alert.account}`,
    `Detected pattern: ${alert.fraudType} through channel ${alert.channel}`,
    `Recommendation: ${alert.recommendedAction}`,
  ];

  const graphNodeCount = investigation?.graph?.nodes?.length || 0;
  const graphEdgeCount = investigation?.graph?.edges?.length || 0;
  facts.push(`Linked graph neighborhood: ${graphNodeCount} nodes, ${graphEdgeCount} edges`);

  const shapReasons = (investigation?.alert?.shap_top3 || []).slice(0, 2);
  if (shapReasons.length) {
    facts.push(`Top explainers: ${shapReasons.join(" | ")}`);
  }

  return facts;
}

function getResponse(params: {
  text: string;
  alert: AlertCardLike;
  investigation: InvestigationResponse | null;
  similarAlerts: AlertCardLike[];
  strCountForAccount: number;
}): string {
  const { text, alert, investigation, similarAlerts, strCountForAccount } = params;
  const query = text.toLowerCase();
  const graphNodeCount = investigation?.graph?.nodes?.length || 0;
  const graphEdgeCount = investigation?.graph?.edges?.length || 0;
  const ruleFlags = (investigation?.alert?.rule_flags || []).map(prettifyFlag);
  const keyAccounts = (investigation?.graph?.nodes || [])
    .map((node) => String(node.id || ""))
    .filter(Boolean)
    .slice(0, 6);

  if (query.includes("summarize") || query.includes("summary")) {
    return `Case Summary - ${alert.id}\n\nFraud Type: ${alert.fraudType}\nRisk Level: ${getRiskLabel(alert.riskScore)} (${alert.riskScore}/100)\nStatus: ${alert.status}\n\nWhat happened:\n${alert.description}\n\nGraph context:\n${graphNodeCount} linked accounts/devices and ${graphEdgeCount} flow edges in current neighborhood.\n\nInvestigator note:\n${investigation?.investigation_note || "No generated note available yet."}`;
  }

  if (query.includes("str") || query.includes("file") || query.includes("report") || query.includes("should i")) {
    const shouldFile = alert.riskScore >= 60;
    const filing = shouldFile ? "STR filing is recommended" : "STR filing can be deferred unless additional suspicious activity appears";
    return `${filing}.\n\nReasoning:\n1. Current risk score is ${alert.riskScore} (${getRiskLabel(alert.riskScore)}).\n2. Pattern detected: ${alert.fraudType}.\n3. Rule/SHAP evidence: ${ruleFlags.concat(investigation?.alert?.shap_top3 || []).slice(0, 3).join(" | ") || "Pattern-based detection"}.\n4. Historical STRs for this account: ${strCountForAccount}.\n\nYou can open STR Generator directly for this alert.`;
  }

  if (query.includes("pattern") || query.includes("typology") || query.includes("what is")) {
    return `Pattern Analysis\n\nDetected typology: ${alert.fraudType}\nRule flags: ${ruleFlags.join(", ") || "Not returned"}\nRecommended action: ${alert.recommendedAction}\n\nSignal explanation:\n${(investigation?.alert?.shap_top3 || []).join("\n") || "No SHAP contributors returned."}`;
  }

  if (query.includes("account") || query.includes("who") || query.includes("key")) {
    return `Key Accounts\n\nPrimary account: ${alert.account}\nAmount: ${alert.amount}\nChannel: ${alert.channel}\n\nLinked entities:\n${keyAccounts.length ? keyAccounts.map((accountId) => `- ${accountId}`).join("\n") : "No linked nodes returned yet."}`;
  }

  if (query.includes("risk") || query.includes("score") || query.includes("level")) {
    return `Risk Assessment\n\nScore: ${alert.riskScore}/100 (${getRiskLabel(alert.riskScore)})\nStatus: ${alert.status}\nRecommendation: ${alert.recommendedAction}\n\nTop drivers:\n${(investigation?.alert?.shap_top3 || []).slice(0, 3).join("\n") || "No explainability payload available."}`;
  }

  if (query.includes("similar") || query.includes("past") || query.includes("cases")) {
    if (!similarAlerts.length) {
      return `No similar live alerts found for ${alert.fraudType} in the current backend dataset.`;
    }

    const lines = similarAlerts
      .slice(0, 4)
      .map((item, index) => `${index + 1}. ${item.id} - ${item.fraudType} - ${item.amount} - risk ${item.riskScore}`)
      .join("\n");

    return `Similar Live Alerts (${similarAlerts.length})\n\n${lines}`;
  }

  return `I can help analyze this live alert. Try one of these:\n- Summarize this case\n- Should I file an STR?\n- What pattern is this?\n- Who are the key accounts?\n- Show similar past cases\n- What's the risk level?`;
}

export default function CopilotPage() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<AlertCardLike[]>([]);
  const [selectedCase, setSelectedCase] = useState("");
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [strHistoryCountByAccount, setStrHistoryCountByAccount] = useState<Record<string, number>>({});
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const activeAlert = useMemo(
    () => alerts.find((alert) => alert.id === selectedCase) || alerts[0],
    [alerts, selectedCase],
  );

  const facts = useMemo(() => buildFacts(activeAlert, investigation), [activeAlert, investigation]);

  const similarAlerts = useMemo(() => {
    if (!activeAlert) return [];
    return alerts.filter((alert) => alert.id !== activeAlert.id && alert.fraudType === activeAlert.fraudType);
  }, [alerts, activeAlert]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const loadLiveContext = useCallback(async () => {
    setLoading(true);
    try {
      const [alertResp, txnResp, strResp] = await Promise.all([
        listAlerts({ page: 1, pageSize: 200 }),
        listTransactions({ page: 1, pageSize: 500 }),
        listStrReports({ page: 1, pageSize: 500 }),
      ]);

      const txnById = new Map(txnResp.items.map((txn) => [txn.id, txn]));
      const mappedAlerts = alertResp.items.map((alert) => toAlertCard(alert, txnById.get(alert.transaction_id)));
      setAlerts(mappedAlerts);

      const strCountMap: Record<string, number> = {};
      strResp.items.forEach((report) => {
        const accountId = report.account_id || "";
        if (!accountId) return;
        strCountMap[accountId] = (strCountMap[accountId] || 0) + 1;
      });
      setStrHistoryCountByAccount(strCountMap);

      if (!mappedAlerts.length) {
        setSelectedCase("");
        setInvestigation(null);
        setMessages([
          {
            role: "assistant",
            content: "No live alerts are currently available. Ingest or trigger a suspicious transaction to begin Copilot analysis.",
            time: getTime(),
          },
        ]);
      } else {
        const initialAlert = mappedAlerts[0];
        setSelectedCase(initialAlert.id);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load live Copilot context");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInvestigation = useCallback(async (alertId: string) => {
    if (!alertId) return;
    try {
      const payload = await investigateAlert(alertId, 2);
      if ((payload as unknown as { error?: string }).error) {
        throw new Error((payload as unknown as { error: string }).error);
      }
      setInvestigation(payload);
    } catch {
      setInvestigation(null);
    }
  }, []);

  useEffect(() => {
    void loadLiveContext();
  }, [loadLiveContext]);

  useEffect(() => {
    if (!selectedCase || !activeAlert) return;

    void loadInvestigation(selectedCase);
    setMessages([
      {
        role: "assistant",
        content: `Live case context loaded for ${activeAlert.id}.\n\nPattern: ${activeAlert.fraudType}\nRisk: ${activeAlert.riskScore}/100 (${getRiskLabel(activeAlert.riskScore)})\nAccount: ${activeAlert.account}\nAmount: ${activeAlert.amount}\n\nAsk me for summary, STR recommendation, key accounts, similar cases, or risk assessment.`,
        time: getTime(),
      },
    ]);
    setInput("");
  }, [selectedCase, activeAlert, loadInvestigation]);

  const handleCaseChange = useCallback((id: string) => {
    setSelectedCase(id);
  }, []);

  const exportChatLog = useCallback(() => {
    const blob = new Blob([JSON.stringify(messages, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `copilot-chat-${selectedCase || "case"}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Chat log exported");
  }, [messages, selectedCase]);

  function sendMessage(text: string) {
    if (!text.trim() || !activeAlert) return;

    const userMsg: Message = { role: "user", content: text.trim(), time: getTime() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setThinking(true);

    setTimeout(() => {
      setThinking(false);
      const response = getResponse({
        text,
        alert: activeAlert,
        investigation,
        similarAlerts,
        strCountForAccount: strHistoryCountByAccount[activeAlert.account] || 0,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: response, time: getTime() }]);
    }, 700);
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-10 gap-4" style={{ minHeight: "calc(100vh - 200px)" }}>
      <div className="lg:col-span-3 space-y-3">
        <div className="bg-card border border-border rounded-[10px] p-4">
          <div className="text-sm font-bold text-primary mb-3">Active Case Context</div>
          <label className="text-[11px] text-muted-foreground mb-1 block">Load a live alert:</label>
          <select
            value={selectedCase}
            onChange={(event) => handleCaseChange(event.target.value)}
            className="w-full bg-background border border-border rounded-md py-2 px-3 text-[13px] text-foreground outline-none cursor-pointer mb-3"
            disabled={!alerts.length}
          >
            {!alerts.length && <option value="">No live alerts</option>}
            {alerts.map((alert) => (
              <option key={alert.id} value={alert.id}>{alert.id} - {alert.fraudType}</option>
            ))}
          </select>

          {activeAlert && (
            <>
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
                  <div>Detected: {activeAlert.timeDetected}</div>
                  <div>Status: {activeAlert.status}</div>
                </div>
                <div className="mt-2">
                  <RiskScoreBar score={activeAlert.riskScore} size="sm" />
                </div>
              </div>

              <div className="mb-4">
                <div className="text-xs font-semibold text-primary mb-2">Live facts</div>
                <ul className="space-y-1">
                  {facts.map((fact, index) => (
                    <li key={`${fact}-${index}`} className="text-xs text-foreground leading-relaxed">- {fact}</li>
                  ))}
                </ul>
              </div>
            </>
          )}

          <div className="mb-4">
            <div className="text-[11px] text-muted-foreground mb-2">Ask Copilot:</div>
            <div className="grid grid-cols-2 gap-1.5">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => sendMessage(suggestion)}
                  className="bg-info/10 text-info border border-info/20 rounded-full px-3 py-1.5 text-[11px] text-left cursor-pointer hover:bg-info/15"
                  disabled={!activeAlert}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-muted-foreground mr-1">Copilot Actions:</span>
          <button onClick={() => selectedCase && navigate(`/graph?alert=${selectedCase}`)} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer" disabled={!selectedCase}>
            View Case Graph
          </button>
          <button onClick={() => selectedCase && navigate(`/str-generator?alert=${selectedCase}`)} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer" disabled={!selectedCase}>
            Generate STR
          </button>
          <button onClick={exportChatLog} className="text-[11px] border border-border rounded-md px-3 py-1.5 bg-card text-foreground hover:bg-muted cursor-pointer" disabled={!messages.length}>
            Export Chat Log
          </button>
        </div>
      </div>

      <div className="lg:col-span-7 flex flex-col gap-3">
        <div className="bg-card border border-border rounded-[10px] overflow-hidden flex flex-col flex-1">
          <div className="bg-primary px-5 py-3.5 flex items-center gap-3">
            <div className="bg-danger w-9 h-9 rounded-full flex items-center justify-center shrink-0">
              <Bot className="w-[18px] h-[18px] text-white" />
            </div>
            <div className="flex-1">
              <div className="text-white font-bold text-sm">Investigator Copilot</div>
              <div className="text-[11px]" style={{ color: "#93C5FD" }}>Live backend context · deterministic assistant responses</div>
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${loading ? "bg-warning" : "bg-success"}`} />
              <span className="text-[11px]" style={{ color: "#93C5FD" }}>{loading ? "Loading" : "Ready"}</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-5 bg-background space-y-4 scrollbar-thin" style={{ minHeight: 300 }}>
            {error && <p className="text-xs text-danger">{error}</p>}
            {messages.map((message, index) =>
              message.role === "assistant" ? (
                <div key={index} className="flex gap-2 items-start max-w-[85%]">
                  <div className="bg-danger w-7 h-7 rounded-full flex items-center justify-center shrink-0">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div>
                    <div className="bg-card border border-border rounded-xl rounded-tl-none p-3.5 text-[13px] text-foreground leading-relaxed whitespace-pre-wrap">
                      {message.content.split(/(\*\*.*?\*\*)/).map((part, partIndex) =>
                        part.startsWith("**") && part.endsWith("**") ? (
                          <strong key={partIndex}>{part.slice(2, -2)}</strong>
                        ) : (
                          <span key={partIndex}>{part}</span>
                        ),
                      )}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1">{message.time}</div>
                  </div>
                </div>
              ) : (
                <div key={index} className="flex gap-2 items-start self-end ml-auto max-w-[80%] flex-row-reverse">
                  <div className="bg-info w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-white text-[10px] font-bold">
                    AK
                  </div>
                  <div>
                    <div className="bg-primary text-primary-foreground rounded-xl rounded-tr-none p-3 text-[13px] leading-relaxed whitespace-pre-wrap">
                      {message.content}
                    </div>
                    <div className="text-[10px] text-muted-foreground mt-1 text-right">{message.time}</div>
                  </div>
                </div>
              ),
            )}
            {thinking && (
              <div className="flex gap-2 items-start max-w-[85%]">
                <div className="bg-danger w-7 h-7 rounded-full flex items-center justify-center shrink-0">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
                <div className="bg-card border border-border rounded-xl rounded-tl-none p-3.5 text-[13px] text-muted-foreground italic flex items-center gap-1">
                  Copilot is analyzing live context
                  <span className="animate-thinking-dot-1">.</span>
                  <span className="animate-thinking-dot-2">.</span>
                  <span className="animate-thinking-dot-3">.</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="bg-card border-t border-border px-4 py-3 flex gap-3 items-center">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && sendMessage(input)}
              placeholder="Ask anything about this live case..."
              className="flex-1 bg-background border border-border rounded-full px-4 py-2.5 text-[13px] text-foreground outline-none focus:ring-1 focus:ring-primary"
              disabled={!activeAlert}
            />
            <button
              onClick={() => sendMessage(input)}
              className="bg-primary text-white rounded-full w-10 h-10 flex items-center justify-center cursor-pointer hover:bg-primary/90 shrink-0 disabled:opacity-60"
              disabled={!activeAlert}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
