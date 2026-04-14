import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import Alerts from "@/pages/Alerts";
import STRReports from "@/pages/STRReports";

vi.mock("@/lib/unigraph-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/unigraph-api")>("@/lib/unigraph-api");

  const txn = {
    id: "TXN100001",
    from_account: "ACC1001",
    to_account: "ACC1011",
    amount: 12450,
    channel: "UPI",
    timestamp: "2026-03-01T09:05:00Z",
    risk_score: 84,
    is_flagged: true,
    rule_violations: ["RAPID_LAYERING"],
    primary_fraud_type: "RAPID_LAYERING",
    model_version: "unigraph-ml-service-bootstrap-xgb-v1-fraud-scenarios",
    scoring_source: "ml_blended",
    scoring_latency_ms: 12.5,
  };

  const alert = {
    id: "ALERT100001",
    transaction_id: "TXN100001",
    account_id: "ACC1001",
    risk_score: 84,
    risk_level: "HIGH",
    recommendation: "Escalate and review linked accounts",
    shap_top3: [
      "velocity_1h=+0.41",
      "shared_device_count=+0.28",
      "round_trip_pattern=+0.16",
    ],
    rule_flags: ["RAPID_LAYERING", "MULE_NETWORK"],
    primary_fraud_type: "RAPID_LAYERING",
    status: "OPEN",
    created_at: "2026-03-01T09:05:10Z",
    alert_timestamp: "2026-03-01T09:05:10Z",
  };

  const toUiTransaction = (backendTxn: Record<string, unknown>) => {
    const amountNum = Number(backendTxn.amount || 0);
    const riskScore = Math.round(Number(backendTxn.risk_score || 0));
    return {
      txnId: String(backendTxn.id || "TXN100001"),
      source: String(backendTxn.from_account || "ACC1001"),
      destination: String(backendTxn.to_account || "ACC1011"),
      amount: `INR ${Math.round(amountNum).toLocaleString("en-IN")}`,
      amountNum,
      channel: String(backendTxn.channel || "UPI") as "UPI" | "RTGS" | "NEFT" | "IMPS" | "CASH" | "Card",
      timestamp: "01/03/2026 09:05",
      timestampIso: String(backendTxn.timestamp || "2026-03-01T09:05:00Z"),
      riskScore,
      status: backendTxn.is_flagged ? "Flagged" : "Cleared",
      flags: (backendTxn.rule_violations as string[]) || [],
      branch: "BR001",
      scoringSource: String(backendTxn.scoring_source || "ml_blended"),
      modelVersion: String(backendTxn.model_version || "v1"),
      scoringLatencyMs: Number(backendTxn.scoring_latency_ms || 0),
    };
  };

  const toAlertCard = (backendAlert: Record<string, unknown>, backendTxn?: Record<string, unknown>) => {
    const score = Math.round(Number(backendAlert.risk_score || backendAlert.ensemble_score || 0));
    const amountNum = Number(backendTxn?.amount || 12450);
    return {
      id: String(backendAlert.id || "ALERT100001"),
      fraudType: "Rapid Layering",
      account: String(backendAlert.account_id || backendTxn?.from_account || "ACC1001"),
      amount: `INR ${Math.round(amountNum).toLocaleString("en-IN")}`,
      riskScore: score,
      channel: String(backendTxn?.channel || "UPI").toUpperCase(),
      timeDetected: "01/03/2026 09:05",
      shapReason: "velocity_1h and shared device activity",
      description: String(backendAlert.recommendation || "Suspicious transfer pattern detected"),
      recommendedAction: String(backendAlert.recommendation || "Escalate for review"),
      status: String(backendAlert.status || "OPEN"),
      transactionId: String(backendAlert.transaction_id || backendTxn?.id || "TXN100001"),
    };
  };

  return {
    ...actual,
    connectAlertsWebSocket: vi.fn((_, __, onConnectionChange?: (connected: boolean) => void) => {
      if (typeof onConnectionChange === "function") {
        onConnectionChange(true);
      }
      return () => {
        if (typeof onConnectionChange === "function") {
          onConnectionChange(false);
        }
      };
    }),
    listTransactions: vi.fn(async () => ({
      items: [txn],
      total: 1,
      page: 1,
      page_size: 1,
    })),
    getTransaction: vi.fn(async () => txn),
    listAlerts: vi.fn(async () => ({
      items: [alert],
      total: 1,
      page: 1,
      page_size: 1,
    })),
    investigateAlert: vi.fn(async () => ({
      alert,
      transaction: txn,
      graph: {
        nodes: [
          { id: "ACC1001", labels: ["Account"], risk_score: 84 },
          { id: "ACC1011", labels: ["Account"], risk_score: 62 },
        ],
        edges: [
          {
            id: "EDGE100001",
            source: "ACC1001",
            target: "ACC1011",
            type: "TRANSFER",
            amount: 12450,
            channel: "UPI",
          },
        ],
      },
      investigation_note: "Connected accounts show suspicious velocity patterns.",
    })),
    listStrReports: vi.fn(async () => ({
      items: [
        {
          id: "STR100001",
          alert_id: "ALERT100001",
          account_id: "ACC1001",
          risk_score: 84,
          narrative: "Draft STR narrative",
          status: "DRAFT",
          created_at: "2026-03-01T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 1,
    })),
    generateStrReport: vi.fn(async () => ({
      str_id: "STR100001",
      narrative: "Draft STR narrative",
      status: "DRAFT",
      alert_id: "ALERT100001",
      account_id: "ACC1001",
      risk_score: 84,
    })),
    submitStrReport: vi.fn(async () => ({
      str_id: "STR100001",
      status: "SUBMITTED",
      reference_id: "FIU-REF-100001",
    })),
    ingestTransaction: vi.fn(async () => ({
      txn_id: "TXN100001",
      from_account: "ACC1001",
      to_account: "ACC1011",
      amount: 12450,
      channel: "UPI",
      timestamp: "2026-03-01T09:05:00Z",
      risk_score: 84,
      risk_level: "HIGH",
      recommendation: "Escalate",
      rule_violations: ["RAPID_LAYERING"],
      is_flagged: true,
      alert_id: "ALERT100001",
      scoring_source: "ml_blended",
      scoring_latency_ms: 12.5,
    })),
    getBackendHealth: vi.fn(async () => ({
      status: "healthy",
      version: "1.0.0",
      neo4j: "connected",
      fraud_scoring: {
        ml_service_reachable: true,
        ml_service_url: "http://localhost:8002",
        ml_model_version: "unigraph-ml-service-bootstrap-xgb-v1-fraud-scenarios",
        fallback_mode_available: true,
      },
      graph_stats: {
        total_accounts: 2,
        total_transactions: 1,
        total_alerts: 1,
        flagged_accounts: 1,
      },
    })),
    getGraphAnalyticsStatus: vi.fn(async () => ({
      status: "ok",
      gds: {
        total_accounts: 2,
        with_pagerank: 2,
        with_community: 2,
        with_betweenness: 2,
        max_pagerank: 0.89,
        distinct_communities: 1,
        top_accounts: [
          {
            account_id: "ACC1001",
            pagerank: 0.89,
            community_id: 1,
            betweenness_centrality: 0.45,
            risk_score: 84,
          },
        ],
      },
      algorithms: ["pagerank", "louvain", "betweenness"],
    })),
    getMlHealth: vi.fn(async () => ({
      status: "healthy",
      model_version: "unigraph-ml-service-bootstrap-xgb-v1-fraud-scenarios",
      gnn_loaded: true,
      if_loaded: true,
      xgb_loaded: true,
      fallback_ready: false,
    })),
    toUiTransaction,
    toAlertCard,
  };
});

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  } as Response;
}

function renderAppAt(path: string) {
  window.history.pushState({}, "Test", path);
  return render(<App />);
}

async function expectTextVisible(value: string | RegExp) {
  const matches = await screen.findAllByText(value);
  expect(matches.length).toBeGreaterThan(0);
}

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    if (url.includes("/api/v1/alerts")) {
      return jsonResponse({
        items: [
          {
            id: "ALERT100001",
            transaction_id: "TXN100001",
            account_id: "ACC1001",
            risk_score: 84,
            risk_level: "HIGH",
            recommendation: "Escalate and review linked accounts",
            shap_top3: ["velocity_1h=+0.41"],
            rule_flags: ["RAPID_LAYERING"],
            status: "OPEN",
          },
        ],
      });
    }

    return jsonResponse({});
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Routed page smoke tests", () => {
  it("renders dashboard route", async () => {
    renderAppAt("/");
    await expectTextVisible(/Dashboard Overview/i);
  });

  it("renders alerts queue route", async () => {
    renderAppAt("/alerts");
    await expectTextVisible(/Alerts & Cases/i);
  });

  it("renders graph explorer route", async () => {
    renderAppAt("/graph");
    await expectTextVisible(/Graph Investigation/i);
  });

  it("renders transaction monitor route", async () => {
    renderAppAt("/transactions");
    await expectTextVisible(/Transaction Monitor/i);
  });

  it("renders STR generator route", async () => {
    renderAppAt("/str-generator");
    await expectTextVisible(/STR Generator/i);
  });

  it("renders copilot route", async () => {
    renderAppAt("/copilot");
    await expectTextVisible(/Investigator Copilot/i);
  });

  it("renders pipeline status route", async () => {
    renderAppAt("/pipeline-status");
    await expectTextVisible(/Pipeline Status \(Real Data Only\)/i);
  });

  it("renders settings route", async () => {
    renderAppAt("/settings");
    await expectTextVisible(/Settings & Profile/i);
  });

  it("renders not found route", async () => {
    renderAppAt("/route-that-does-not-exist");
    await expectTextVisible(/Oops! Page not found/i);
  });
});

describe("Non-routed page smoke tests", () => {
  it("renders Alerts page component", async () => {
    render(<Alerts />);
    await expectTextVisible(/Alerts Command Center/i);
  });

  it("renders STRReports page component", async () => {
    render(<STRReports />);
    await expectTextVisible(/Generate Suspicious Transaction Report/i);
  });
});
