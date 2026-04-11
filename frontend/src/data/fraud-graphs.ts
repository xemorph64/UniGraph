export interface GraphNode {
  id: string;
  label: string;
  type: "source" | "suspicious" | "mule" | "clean" | "destination" | "device" | "branch";
  x: number;
  y: number;
  fx?: number | null;
  fy?: number | null;
  kycStatus?: string;
  balance?: string;
  accountType?: string;
  riskScore?: number;
  lastTxnAmount?: string;
  lastTxnDate?: string;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  amount: string;
  channel: string;
  isFraudPath?: boolean;
}

export interface GraphDataset {
  nodes: GraphNode[];
  links: GraphLink[];
}

function makeNode(id: string, label: string, type: GraphNode["type"], extra?: Partial<GraphNode>): GraphNode {
  return { id, label, type, x: 0, y: 0, kycStatus: "Verified", balance: "₹2,50,000", accountType: "Savings", riskScore: 45, lastTxnAmount: "₹50,000", lastTxnDate: "08/03/2026", ...extra };
}

export const fraudGraphs: Record<string, GraphDataset> = {
  "Rapid Layering": {
    nodes: [
      makeNode("ACC001", "Source A/C", "source", { riskScore: 96, balance: "₹20,00,000", kycStatus: "Verified" }),
      makeNode("ACC002", "Mule A/C 1", "suspicious", { riskScore: 88, kycStatus: "Minimal KYC", balance: "₹5,00,000" }),
      makeNode("ACC003", "Mule A/C 2", "suspicious", { riskScore: 85, kycStatus: "Minimal KYC", balance: "₹5,00,000" }),
      makeNode("ACC004", "Mule A/C 3", "mule", { riskScore: 90, kycStatus: "Minimal KYC", balance: "₹5,00,000" }),
      makeNode("ACC005", "Intermediary", "suspicious", { riskScore: 78, kycStatus: "Under Review" }),
      makeNode("ACC006", "Clean A/C", "clean", { riskScore: 12, kycStatus: "Verified" }),
      makeNode("ACC007", "Mule A/C 4", "mule", { riskScore: 91, kycStatus: "Minimal KYC" }),
      makeNode("ACC008", "Shell Co.", "suspicious", { riskScore: 82, accountType: "Current" }),
      makeNode("ACC009", "Crypto Exit", "destination", { riskScore: 95, kycStatus: "Unverified", accountType: "Exchange Wallet" }),
      makeNode("DEV001", "Device", "device", { riskScore: 0 }),
      makeNode("BRN001", "Branch", "branch", { riskScore: 0 }),
    ],
    links: [
      { source: "ACC001", target: "ACC002", amount: "₹5L", channel: "UPI", isFraudPath: true },
      { source: "ACC001", target: "ACC003", amount: "₹5L", channel: "NEFT", isFraudPath: true },
      { source: "ACC001", target: "ACC004", amount: "₹5L", channel: "IMPS", isFraudPath: true },
      { source: "ACC002", target: "ACC009", amount: "₹4.8L", channel: "RTGS", isFraudPath: true },
      { source: "ACC003", target: "ACC005", amount: "₹4.9L", channel: "UPI", isFraudPath: true },
      { source: "ACC004", target: "ACC007", amount: "₹4.7L", channel: "UPI", isFraudPath: true },
      { source: "ACC005", target: "ACC009", amount: "₹4.6L", channel: "NEFT", isFraudPath: true },
      { source: "ACC007", target: "ACC009", amount: "₹4.5L", channel: "IMPS", isFraudPath: true },
      { source: "ACC006", target: "ACC008", amount: "₹1.1L", channel: "UPI", isFraudPath: false },
      { source: "DEV001", target: "ACC001", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "BRN001", target: "ACC001", amount: "", channel: "BRANCH", isFraudPath: false },
    ],
  },
  "Round-Tripping": {
    nodes: [
      makeNode("COMP-A", "Company A", "source", { riskScore: 92, accountType: "Current", balance: "₹2,10,00,000" }),
      makeNode("COMP-B", "Company B", "suspicious", { riskScore: 88, accountType: "Current", balance: "₹48,00,000" }),
      makeNode("COMP-C", "Company C", "suspicious", { riskScore: 86, accountType: "Current", kycStatus: "Under Review" }),
      makeNode("UBO-001", "UBO (Shared)", "mule", { riskScore: 95, kycStatus: "Flagged" }),
      makeNode("BANK-A", "Bank Account", "clean", { riskScore: 20, kycStatus: "Verified" }),
      makeNode("DEV002", "Shared Device", "device", { riskScore: 0 }),
      makeNode("BRN002", "Delhi Branch", "branch", { riskScore: 0 }),
      makeNode("ACC-EXT", "External A/C", "destination", { riskScore: 60 }),
      makeNode("ACC-FEE", "Fee Account", "mule", { riskScore: 70 }),
    ],
    links: [
      { source: "COMP-A", target: "COMP-B", amount: "₹50L", channel: "NEFT", isFraudPath: true },
      { source: "COMP-B", target: "COMP-C", amount: "₹48L", channel: "NEFT", isFraudPath: true },
      { source: "COMP-C", target: "COMP-A", amount: "₹46L", channel: "NEFT", isFraudPath: true },
      { source: "UBO-001", target: "COMP-A", amount: "", channel: "OWNED_BY", isFraudPath: false },
      { source: "UBO-001", target: "COMP-B", amount: "", channel: "OWNED_BY", isFraudPath: false },
      { source: "UBO-001", target: "COMP-C", amount: "", channel: "OWNED_BY", isFraudPath: false },
      { source: "COMP-B", target: "ACC-FEE", amount: "₹2L", channel: "UPI", isFraudPath: false },
      { source: "DEV002", target: "COMP-A", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "BRN002", target: "COMP-A", amount: "", channel: "BRANCH", isFraudPath: false },
    ],
  },
  "Structuring/Smurfing": {
    nodes: [
      makeNode("BR-01", "Branch Mumbai", "branch", { riskScore: 0 }),
      makeNode("BR-02", "Branch Delhi", "branch", { riskScore: 0 }),
      makeNode("BR-03", "Branch Bangalore", "branch", { riskScore: 0 }),
      makeNode("BR-04", "Branch Chennai", "branch", { riskScore: 0 }),
      makeNode("BR-05", "Branch Kolkata", "branch", { riskScore: 0 }),
      makeNode("DEP-01", "Depositor 1", "suspicious", { riskScore: 80, kycStatus: "Walk-in" }),
      makeNode("DEP-02", "Depositor 2", "suspicious", { riskScore: 78, kycStatus: "Walk-in" }),
      makeNode("DEP-03", "Depositor 3", "suspicious", { riskScore: 82, kycStatus: "Walk-in" }),
      makeNode("DEP-04", "Depositor 4", "mule", { riskScore: 85, kycStatus: "Walk-in" }),
      makeNode("DEP-05", "Depositor 5", "mule", { riskScore: 79, kycStatus: "Walk-in" }),
      makeNode("ACC-X", "Beneficiary X", "destination", { riskScore: 95, kycStatus: "Minimal KYC", balance: "₹4,90,000" }),
      makeNode("DEV-X", "Shared Phone", "device", { riskScore: 0 }),
    ],
    links: [
      { source: "DEP-01", target: "ACC-X", amount: "₹49K", channel: "Cash", isFraudPath: true },
      { source: "DEP-02", target: "ACC-X", amount: "₹49K", channel: "Cash", isFraudPath: true },
      { source: "DEP-03", target: "ACC-X", amount: "₹49K", channel: "Cash", isFraudPath: true },
      { source: "DEP-04", target: "ACC-X", amount: "₹49K", channel: "Cash", isFraudPath: true },
      { source: "DEP-05", target: "ACC-X", amount: "₹49K", channel: "Cash", isFraudPath: true },
      { source: "BR-01", target: "DEP-01", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "BR-02", target: "DEP-02", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "BR-03", target: "DEP-03", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "BR-04", target: "DEP-04", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "BR-05", target: "DEP-05", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "DEV-X", target: "DEP-01", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "DEV-X", target: "DEP-02", amount: "", channel: "ACCESS", isFraudPath: false },
    ],
  },
  "Dormant Activation": {
    nodes: [
      makeNode("EXT-SRC", "External RTGS", "source", { riskScore: 60, accountType: "Current", kycStatus: "External" }),
      makeNode("DORM-01", "Dormant A/C", "suspicious", { riskScore: 96, kycStatus: "Stale KYC", balance: "₹1,50,00,000" }),
      makeNode("OFF-01", "Offshore A/C", "destination", { riskScore: 90, kycStatus: "Foreign", accountType: "NRE" }),
      makeNode("DORM-02", "Dormant A/C 2", "suspicious", { riskScore: 88, kycStatus: "Stale KYC" }),
      makeNode("DORM-03", "Dormant A/C 3", "suspicious", { riskScore: 85, kycStatus: "Stale KYC" }),
      makeNode("MASTER-01", "Master Hub", "mule", { riskScore: 98, kycStatus: "Flagged" }),
      makeNode("MASTER-02", "Master Hub 2", "mule", { riskScore: 95 }),
      makeNode("GHOST-EMP", "Ghost Payroll", "suspicious", { riskScore: 83 }),
      makeNode("DECEASED", "Deceased A/C", "suspicious", { riskScore: 99, kycStatus: "Deceased" }),
      makeNode("DEV-UNK", "Unknown Device", "device", { riskScore: 0 }),
      makeNode("BRN-MUM", "Mumbai Branch", "branch", { riskScore: 0 }),
    ],
    links: [
      { source: "EXT-SRC", target: "DORM-01", amount: "₹1.5Cr", channel: "RTGS", isFraudPath: true },
      { source: "DORM-01", target: "OFF-01", amount: "₹1.5Cr", channel: "SWIFT", isFraudPath: true },
      { source: "MASTER-01", target: "DORM-02", amount: "₹5L", channel: "NEFT", isFraudPath: true },
      { source: "MASTER-01", target: "DORM-03", amount: "₹8L", channel: "NEFT", isFraudPath: true },
      { source: "MASTER-02", target: "DORM-01", amount: "₹3L", channel: "UPI", isFraudPath: false },
      { source: "GHOST-EMP", target: "DORM-02", amount: "₹4.8L", channel: "NEFT", isFraudPath: false },
      { source: "DEV-UNK", target: "DECEASED", amount: "", channel: "ACCESS", isFraudPath: true },
      { source: "BRN-MUM", target: "DORM-01", amount: "", channel: "BRANCH", isFraudPath: false },
    ],
  },
  "Profile Mismatch": {
    nodes: [
      makeNode("CORP-01", "Corp A/C (MH)", "source", { riskScore: 40, accountType: "Current", balance: "₹80,00,000" }),
      makeNode("CORP-02", "Corp A/C (DL)", "source", { riskScore: 38, accountType: "Current", balance: "₹65,00,000" }),
      makeNode("CORP-03", "Corp A/C (KA)", "source", { riskScore: 42, accountType: "Current", balance: "₹55,00,000" }),
      makeNode("STUDENT", "Student A/C", "suspicious", { riskScore: 94, kycStatus: "Minimal KYC", accountType: "Savings (Student)", balance: "₹5,00,000" }),
      makeNode("RURAL-01", "Rural A/C", "suspicious", { riskScore: 81, kycStatus: "Verified" }),
      makeNode("PENSION", "Pension A/C", "suspicious", { riskScore: 76, kycStatus: "Verified", accountType: "Pension" }),
      makeNode("KYC-UPD", "KYC Updated", "mule", { riskScore: 91 }),
      makeNode("MULTI-ID", "Multi-ID Device", "device", { riskScore: 97 }),
      makeNode("HAWALA-01", "Hawala Hub", "destination", { riskScore: 88 }),
      makeNode("BRN-RUR", "Rural Branch", "branch", { riskScore: 0 }),
    ],
    links: [
      { source: "CORP-01", target: "STUDENT", amount: "₹10K×50", channel: "UPI", isFraudPath: true },
      { source: "CORP-02", target: "STUDENT", amount: "₹10K×50", channel: "UPI", isFraudPath: true },
      { source: "CORP-03", target: "STUDENT", amount: "₹10K×50", channel: "UPI", isFraudPath: true },
      { source: "RURAL-01", target: "HAWALA-01", amount: "₹15L", channel: "NEFT", isFraudPath: true },
      { source: "MULTI-ID", target: "STUDENT", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "MULTI-ID", target: "RURAL-01", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "MULTI-ID", target: "KYC-UPD", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "KYC-UPD", target: "PENSION", amount: "₹22L", channel: "RTGS", isFraudPath: false },
      { source: "BRN-RUR", target: "RURAL-01", amount: "", channel: "BRANCH", isFraudPath: false },
    ],
  },
  "Mule Account": {
    nodes: [
      makeNode("MULE-01", "Mule (19yr)", "mule", { riskScore: 85, kycStatus: "Basic KYC" }),
      makeNode("MULE-02", "Mule (21yr)", "mule", { riskScore: 82, kycStatus: "Basic KYC" }),
      makeNode("MULE-03", "Mule (Student)", "mule", { riskScore: 82, kycStatus: "Basic KYC" }),
      makeNode("MULE-04", "Mule (Elderly)", "suspicious", { riskScore: 94, kycStatus: "Verified" }),
      makeNode("MSME-01", "MSME Front", "suspicious", { riskScore: 98, kycStatus: "Basic KYC", accountType: "Current" }),
      makeNode("HUB-01", "Hub Account", "destination", { riskScore: 96 }),
      makeNode("OVERSEAS", "Overseas A/C", "destination", { riskScore: 88, kycStatus: "Foreign" }),
      makeNode("SRC-01", "Inflow Source 1", "source", { riskScore: 30 }),
      makeNode("SRC-02", "Inflow Source 2", "source", { riskScore: 28 }),
      makeNode("SRC-03", "Inflow Source 3", "source", { riskScore: 35 }),
      makeNode("DEV-NEW", "New Device", "device", { riskScore: 0 }),
      makeNode("BRN-HUB", "Same Branch", "branch", { riskScore: 0 }),
    ],
    links: [
      { source: "SRC-01", target: "MULE-01", amount: "₹8L", channel: "NEFT", isFraudPath: true },
      { source: "SRC-02", target: "MULE-02", amount: "₹6L", channel: "NEFT", isFraudPath: true },
      { source: "SRC-03", target: "MULE-03", amount: "₹3L", channel: "UPI", isFraudPath: true },
      { source: "MULE-01", target: "HUB-01", amount: "₹7.8L", channel: "UPI", isFraudPath: true },
      { source: "MULE-02", target: "HUB-01", amount: "₹5.8L", channel: "UPI", isFraudPath: true },
      { source: "MULE-03", target: "HUB-01", amount: "₹2.9L", channel: "UPI", isFraudPath: true },
      { source: "HUB-01", target: "OVERSEAS", amount: "₹45L", channel: "SWIFT", isFraudPath: true },
      { source: "MULE-04", target: "OVERSEAS", amount: "₹9.7L", channel: "NEFT", isFraudPath: true },
      { source: "MSME-01", target: "OVERSEAS", amount: "₹45L", channel: "RTGS", isFraudPath: true },
      { source: "DEV-NEW", target: "MULE-04", amount: "", channel: "ACCESS", isFraudPath: false },
      { source: "BRN-HUB", target: "MULE-01", amount: "", channel: "BRANCH", isFraudPath: false },
      { source: "BRN-HUB", target: "MULE-02", amount: "", channel: "BRANCH", isFraudPath: false },
    ],
  },
};

// Map alert IDs to fraud types
export function getFraudTypeForAlert(alertId: string): string {
  const map: Record<string, string> = {
    // Original alerts
    "AL-001": "Rapid Layering",
    "AL-002": "Round-Tripping",
    "AL-003": "Structuring/Smurfing",
    "AL-004": "Dormant Activation",
    "AL-005": "Profile Mismatch",
    // Alert cards
    "ALT-2024-0847": "Rapid Layering",
    "ALT-2024-0851": "Rapid Layering",
    "ALT-2024-0860": "Rapid Layering",
    "ALT-2024-0848": "Round-Tripping",
    "ALT-2024-0855": "Round-Tripping",
    "ALT-2024-0862": "Round-Tripping",
    "ALT-2024-0849": "Structuring/Smurfing",
    "ALT-2024-0856": "Structuring/Smurfing",
    "ALT-2024-0863": "Structuring/Smurfing",
    "ALT-2024-0850": "Dormant Activation",
    "ALT-2024-0857": "Dormant Activation",
    "ALT-2024-0864": "Dormant Activation",
    "ALT-2024-0852": "Profile Mismatch",
    "ALT-2024-0858": "Profile Mismatch",
    "ALT-2024-0865": "Profile Mismatch",
    "ALT-2024-0853": "Mule Account",
    "ALT-2024-0859": "Mule Account",
    "ALT-2024-0866": "Mule Account",
  };
  return map[alertId] || "Rapid Layering";
}
