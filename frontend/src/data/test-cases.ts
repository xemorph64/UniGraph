export interface TestCase {
  id: string;
  name: string;
  fraudType: string;
  fraudColor: string;
  amount: string;
  accountCount: number;
  triggers: string[];
  riskScore: number;
  alertLevel: "CRITICAL" | "HIGH" | "MEDIUM";
  description: string;
}

export const testCaseSections = [
  {
    title: "Rapid Layering",
    icon: "⚡",
    cases: [
      { id: "TC-LAY-001", name: "Smash & Scatter", fraudType: "Rapid Layering", fraudColor: "bg-danger text-danger-foreground", amount: "₹18,00,000", accountCount: 10, triggers: ["Velocity spike 890% above baseline", "Fan-out ratio 8:1", "Shell company destination", "< 2 hour completion"], riskScore: 94, alertLevel: "CRITICAL" as const, description: "₹18L cash deposit splits into 8 accounts via UPI, consolidated in shell company account." },
      { id: "TC-LAY-002", name: "Salary Ghost Chain", fraudType: "Rapid Layering", fraudColor: "bg-danger text-danger-foreground", amount: "₹9,50,000", accountCount: 4, triggers: ["Dormant reactivation", "Chained velocity", "KYC address update", "3-5% amount reduction per hop"], riskScore: 82, alertLevel: "HIGH" as const, description: "Dormant account reactivates, 3-hop chain with 3-5% reduction per hop." },
      { id: "TC-LAY-003", name: "International Loop", fraudType: "Rapid Layering", fraudColor: "bg-danger text-danger-foreground", amount: "₹42,00,000", accountCount: 9, triggers: ["Cross-border SWIFT origin", "Multi-channel layering", "Structuring below ₹10L", "4-hour completion"], riskScore: 97, alertLevel: "CRITICAL" as const, description: "SWIFT inflow from UAE, split via RTGS to 2 accounts, then IMPS to 6 final destinations." },
      { id: "TC-LAY-004", name: "Card-to-Cash Pyramid", fraudType: "Rapid Layering", fraudColor: "bg-danger text-danger-foreground", amount: "₹6,80,000", accountCount: 9, triggers: ["Card-to-UPI-to-cash pattern", "Same KYC fingerprint", "3 linked cards", "6-hour ATM withdrawals"], riskScore: 79, alertLevel: "HIGH" as const, description: "Credit card cash advances → deposits → UPI transfers → wallet ATM withdrawals." },
      { id: "TC-LAY-005", name: "Round Robin Layering", fraudType: "Rapid Layering", fraudColor: "bg-danger text-danger-foreground", amount: "₹32,00,000", accountCount: 6, triggers: ["Johnson's Cycle Detection", "4 cycles over 72hrs", "₹8L leaked per cycle", "Same account pattern"], riskScore: 96, alertLevel: "CRITICAL" as const, description: "5-account cycle repeats 4 times, leaking ₹8L to final destination each cycle." },
    ],
  },
  {
    title: "Circular Round-Tripping",
    icon: "🔄",
    cases: [
      { id: "TC-RND-001", name: "Boomerang Funds", fraudType: "Round-Tripping", fraudColor: "bg-warning text-warning-foreground", amount: "₹15,00,000", accountCount: 3, triggers: ["Directed cycle in graph", "Net fund flow = ₹0", "3-hop cycle", "< 6 hours"], riskScore: 85, alertLevel: "HIGH" as const, description: "₹15L sent through 3 accounts and returned to origin within 6 hours." },
      { id: "TC-RND-002", name: "Trade Finance Fraud", fraudType: "Round-Tripping", fraudColor: "bg-warning text-warning-foreground", amount: "₹50,00,000", accountCount: 3, triggers: ["Device fingerprint linkage", "Round-trip < 24hrs", "4% skimmed", "Invoice fraud"], riskScore: 91, alertLevel: "CRITICAL" as const, description: "₹50L invoice payment returned as advance, linked by device fingerprint." },
      { id: "TC-RND-003", name: "UPI Ping-Pong", fraudType: "Round-Tripping", fraudColor: "bg-warning text-warning-foreground", amount: "₹2,30,000", accountCount: 2, triggers: ["Bidirectional edge density", "47 transactions in 3 days", "Low individual amounts", "Irregular timing"], riskScore: 67, alertLevel: "MEDIUM" as const, description: "47 UPI transactions ping-ponged between 2 accounts over 3 days." },
      { id: "TC-RND-004", name: "Property Wash", fraudType: "Round-Tripping", fraudColor: "bg-warning text-warning-foreground", amount: "₹75,00,000", accountCount: 3, triggers: ["Same registered address", "3 companies in 6 months", "₹10L total shrinkage", "Property-to-rental loop"], riskScore: 93, alertLevel: "CRITICAL" as const, description: "₹75L property booking → interior payment → rental income back to origin." },
      { id: "TC-RND-005", name: "Loan Layering Round-Trip", fraudType: "Round-Tripping", fraudColor: "bg-warning text-warning-foreground", amount: "₹25,00,000", accountCount: 5, triggers: ["Loan disbursement + same-day outflow", "4-hop cycle", "Unusual repayment velocity", "Fabricated loan history"], riskScore: 88, alertLevel: "HIGH" as const, description: "₹25L loan disbursed, cycled through 4 accounts, returned to repay loan." },
    ],
  },
  {
    title: "Structuring / Smurfing",
    icon: "🧱",
    cases: [
      { id: "TC-STR-001", name: "Classic Smurfing", fraudType: "Structuring", fraudColor: "bg-risk-high text-white", amount: "₹44,40,000", accountCount: 7, triggers: ["Below ₹10L CTR threshold", "KYC device overlap", "Coordinated timing", "Same branch deposits"], riskScore: 95, alertLevel: "CRITICAL" as const, description: "6 individuals deposit ₹7.4L each, all linked by same device fingerprint." },
      { id: "TC-STR-002", name: "ATM Structuring Network", fraudType: "Structuring", fraudColor: "bg-risk-high text-white", amount: "₹4,75,200", accountCount: 4, triggers: ["12 ATM withdrawals ₹9,900", "Same mobile number", "3-hour window", "Threshold avoidance"], riskScore: 80, alertLevel: "HIGH" as const, description: "12 ATM withdrawals of ₹9,900 from 4 accounts sharing same mobile." },
      { id: "TC-STR-003", name: "Fan-In Structuring", fraudType: "Structuring", fraudColor: "bg-risk-high text-white", amount: "₹76,00,000", accountCount: 9, triggers: ["Fan-in graph pattern", "Collective threshold breach", "Same-day timing", "Single beneficiary"], riskScore: 92, alertLevel: "CRITICAL" as const, description: "8 accounts each ₹9.5L same day into single account totaling ₹76L." },
      { id: "TC-STR-004", name: "Multi-Branch Coordinated", fraudType: "Structuring", fraudColor: "bg-risk-high text-white", amount: "₹45,00,000", accountCount: 5, triggers: ["5 branches simultaneously", "KYC mobile linkage", "₹9L per deposit", "Cross-branch coordination"], riskScore: 84, alertLevel: "HIGH" as const, description: "₹9L deposits at 5 branches simultaneously, all linked to same mobile." },
      { id: "TC-STR-005", name: "IMPS Micro-Structuring", fraudType: "Structuring", fraudColor: "bg-risk-high text-white", amount: "₹9,86,000", accountCount: 35, triggers: ["34 × ₹29K IMPS", "Same destination", "New accounts cluster", "Below ₹10L trigger"], riskScore: 90, alertLevel: "CRITICAL" as const, description: "34 IMPS of ₹29K each from 34 new accounts to single destination." },
    ],
  },
  {
    title: "Dormant Account Activation",
    icon: "💤",
    cases: [
      { id: "TC-DOM-001", name: "Sleeping Giant Wakes", fraudType: "Dormant Activation", fraudColor: "bg-primary text-primary-foreground", amount: "₹28,00,000", accountCount: 5, triggers: ["3yr+ dormancy", "Spike magnitude 5600%", "Immediate outflow", "90-min completion"], riskScore: 96, alertLevel: "CRITICAL" as const, description: "3yr dormant account receives ₹28L RTGS, transfers ₹27.5L via 4 UPI in 90min." },
      { id: "TC-DOM-002", name: "Mass Mule Awakening", fraudType: "Dormant Activation", fraudColor: "bg-primary text-primary-foreground", amount: "₹90,00,000", accountCount: 20, triggers: ["18 dormant accounts reactivate", "48-hour window", "Master-spoke topology", "Coordinated dormancy spike"], riskScore: 98, alertLevel: "CRITICAL" as const, description: "18 dormant accounts reactivate within 48hrs, all connected to 2 master accounts." },
      { id: "TC-DOM-003", name: "Seasonal Crop Fraud", fraudType: "Dormant Activation", fraudColor: "bg-primary text-primary-foreground", amount: "₹12,00,000", accountCount: 2, triggers: ["KYC: farmer → urban merchant", "10x historical max", "8-month dormancy", "Same-day transfer"], riskScore: 78, alertLevel: "HIGH" as const, description: "Farmer account dormant 8 months, receives ₹12L, moves to urban merchant same day." },
      { id: "TC-DOM-004", name: "Ghost Employee", fraudType: "Dormant Activation", fraudColor: "bg-primary text-primary-foreground", amount: "₹4,80,000", accountCount: 2, triggers: ["Payroll anomaly", "14-month dormancy", "Immediate full drain", "Employee left company"], riskScore: 83, alertLevel: "HIGH" as const, description: "Salary account inactive 14 months receives ₹4.8L payroll credit, immediately drained." },
      { id: "TC-DOM-005", name: "Inherited Account Misuse", fraudType: "Dormant Activation", fraudColor: "bg-primary text-primary-foreground", amount: "₹6,20,000", accountCount: 2, triggers: ["Post-mortem activity", "Unknown device", "KYC status = deceased", "8 months after death"], riskScore: 99, alertLevel: "CRITICAL" as const, description: "Deceased customer account shows ₹6.2L NEFT activity 8 months after death." },
    ],
  },
  {
    title: "Customer Profile Mismatch",
    icon: "👤",
    cases: [
      { id: "TC-PRF-001", name: "Student to Crore-pati", fraudType: "Profile Mismatch", fraudColor: "bg-destructive text-destructive-foreground", amount: "₹38,00,000", accountCount: 5, triggers: ["Income ratio 3167% anomaly", "Student profile", "₹38L in 30 days", "Lifestyle inconsistency"], riskScore: 87, alertLevel: "HIGH" as const, description: "22yr student with ₹1.2L declared income receives ₹38L in 30 days." },
      { id: "TC-PRF-002", name: "Rural Account, Urban Transactions", fraudType: "Profile Mismatch", fraudColor: "bg-destructive text-destructive-foreground", amount: "₹15,00,000", accountCount: 4, triggers: ["Geographic KYC mismatch", "Mumbai IP cluster", "Hawala pattern", "Rural registration"], riskScore: 81, alertLevel: "HIGH" as const, description: "Rural Maharashtra account, all transactions from Mumbai commercial IPs." },
      { id: "TC-PRF-003", name: "Pension Account Trading", fraudType: "Profile Mismatch", fraudColor: "bg-destructive text-destructive-foreground", amount: "₹15,00,000", accountCount: 4, triggers: ["Account type mismatch", "Multi-account device", "Volume spike", "Age 74 pension"], riskScore: 76, alertLevel: "HIGH" as const, description: "74yr pension account receives/transfers ₹15L in 72hrs via RTGS." },
      { id: "TC-PRF-004", name: "KYC Update Before Fraud", fraudType: "Profile Mismatch", fraudColor: "bg-destructive text-destructive-foreground", amount: "₹22,00,000", accountCount: 2, triggers: ["Suspicious KYC update", "Income ₹3L→₹25L", "2-day gap to large txn", "Address change"], riskScore: 91, alertLevel: "CRITICAL" as const, description: "KYC updated (income ₹3L→₹25L), 2 days later receives ₹22L." },
      { id: "TC-PRF-005", name: "Multi-Identity Device", fraudType: "Profile Mismatch", fraudColor: "bg-destructive text-destructive-foreground", amount: "₹55,00,000", accountCount: 11, triggers: ["Device-to-account ratio 11:1", "Different PAN/name/address", "6-hour coordinated window", "Fraud ring"], riskScore: 97, alertLevel: "CRITICAL" as const, description: "Single device accesses 11 accounts with different identities, coordinated transfers." },
    ],
  },
  {
    title: "Mule Account Detection",
    icon: "🐴",
    cases: [
      { id: "TC-MUL-001", name: "Classic Mule Recruitment", fraudType: "Mule Account", fraudColor: "bg-ubi-navy text-white", amount: "₹8,00,000", accountCount: 3, triggers: ["Account age 6 weeks", "Immediate forwarding", "Overseas destination", "Weekly repeat pattern"], riskScore: 85, alertLevel: "HIGH" as const, description: "6-week old account forwards ₹5-8L overseas within 2 hours, repeated weekly." },
      { id: "TC-MUL-002", name: "Mule Cluster Network", fraudType: "Mule Account", fraudColor: "bg-ubi-navy text-white", amount: "₹60,00,000", accountCount: 13, triggers: ["12 accounts same 2-week window", "Identical behavioral pattern", "Hub-spoke topology", "Same branch"], riskScore: 96, alertLevel: "CRITICAL" as const, description: "12 accounts opened within 2 weeks, all forward to same hub account." },
      { id: "TC-MUL-003", name: "Social Media Mule", fraudType: "Mule Account", fraudColor: "bg-ubi-navy text-white", amount: "₹9,00,000", accountCount: 4, triggers: ["Student income ₹0", "₹2-3L/month for 3 months", "30-min forwarding", "Social media recruitment"], riskScore: 82, alertLevel: "HIGH" as const, description: "University student forwards ₹2-3L/month within 30 minutes of receipt." },
      { id: "TC-MUL-004", name: "Elderly Mule Exploitation", fraudType: "Mule Account", fraudColor: "bg-ubi-navy text-white", amount: "₹9,80,000", accountCount: 3, triggers: ["Device change detected", "Elderly account holder", "₹9.8L same-day forward", "Age-risk flag"], riskScore: 94, alertLevel: "CRITICAL" as const, description: "Senior citizen account used by unknown device, ₹9.8L forwarded same day." },
      { id: "TC-MUL-005", name: "Business Front Mule", fraudType: "Mule Account", fraudColor: "bg-ubi-navy text-white", amount: "₹47,00,000", accountCount: 25, triggers: ["MSME age 3 months", "Fan-in 23:1", "No trade documentation", "Overseas import payment"], riskScore: 98, alertLevel: "CRITICAL" as const, description: "3-month MSME receives ₹47L from 23 individuals, forwards ₹45L as 'import payment'." },
    ],
  },
];
