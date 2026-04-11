export interface AlertCard {
  id: string;
  fraudType: string;
  fraudColor: string;
  account: string;
  amount: string;
  riskScore: number;
  channel: string;
  timeDetected: string;
  shapReason: string;
  description: string;
  kycStatus: string;
  recommendedAction: string;
  transactionChain: string;
}

const fraudTypes = [
  { type: "Rapid Layering", color: "bg-danger text-danger-foreground" },
  { type: "Round-Tripping", color: "bg-warning text-warning-foreground" },
  { type: "Structuring/Smurfing", color: "bg-risk-high text-white" },
  { type: "Dormant Activation", color: "bg-primary text-primary-foreground" },
  { type: "Profile Mismatch", color: "bg-destructive text-destructive-foreground" },
  { type: "Mule Account", color: "bg-ubi-navy text-white" },
];

export const alertCards: AlertCard[] = [
  // Rapid Layering x3
  { id: "ALT-2024-0847", fraudType: "Rapid Layering", fraudColor: fraudTypes[0].color, account: "XXXX4421", amount: "₹20,00,000", riskScore: 96, channel: "UPI", timeDetected: "08/03/2026 10:12", shapReason: "Rapid velocity spike + fan-out to crypto exchanges", description: "₹20L split into 4 chunks wired to crypto exchanges within 12 min", kycStatus: "Verified", recommendedAction: "Immediate STR filing", transactionChain: "ACC4421 → 4 mule accounts → 4 crypto exchanges" },
  { id: "ALT-2024-0851", fraudType: "Rapid Layering", fraudColor: fraudTypes[0].color, account: "XXXX3344", amount: "₹18,00,000", riskScore: 94, channel: "UPI", timeDetected: "08/03/2026 11:30", shapReason: "Fan-out ratio 8:1 + velocity 890% above baseline", description: "₹18L scattered across 8 accounts in under 2 hours", kycStatus: "Minimal KYC", recommendedAction: "Block outward transfers", transactionChain: "ACC3344 → 8 intermediaries → shell company" },
  { id: "ALT-2024-0860", fraudType: "Rapid Layering", fraudColor: fraudTypes[0].color, account: "XXXX5566", amount: "₹42,00,000", riskScore: 97, channel: "RTGS", timeDetected: "07/03/2026 15:20", shapReason: "Cross-border SWIFT origin + multi-channel layering", description: "₹42L from UAE, split via RTGS+IMPS to 6 final accounts", kycStatus: "Under Review", recommendedAction: "Escalate to MLRO", transactionChain: "SWIFT → ACC5566 → 2 RTGS → 6 IMPS destinations" },
  // Round-Tripping x3
  { id: "ALT-2024-0848", fraudType: "Round-Tripping", fraudColor: fraudTypes[1].color, account: "XXXX1001", amount: "₹50,00,000", riskScore: 92, channel: "NEFT", timeDetected: "08/03/2026 09:45", shapReason: "Circular flow detected + same UBO across entities", description: "₹50L circular flow: A→B→C→A, same UBO", kycStatus: "Verified", recommendedAction: "File STR + freeze accounts", transactionChain: "CompA → CompB (₹50L) → CompC (₹48L) → CompA (₹46L)" },
  { id: "ALT-2024-0855", fraudType: "Round-Tripping", fraudColor: fraudTypes[1].color, account: "XXXX7788", amount: "₹15,00,000", riskScore: 85, channel: "NEFT", timeDetected: "07/03/2026 14:00", shapReason: "Directed cycle in graph + net flow ₹0", description: "₹15L boomerang: 3-hop cycle completed in 6 hours", kycStatus: "Verified", recommendedAction: "Investigate loan records", transactionChain: "ACC7788 → ACC102 → ACC103 → ACC7788" },
  { id: "ALT-2024-0862", fraudType: "Round-Tripping", fraudColor: fraudTypes[1].color, account: "XXXX9900", amount: "₹75,00,000", riskScore: 93, channel: "RTGS", timeDetected: "06/03/2026 10:00", shapReason: "Property wash pattern + same registered address", description: "₹75L property booking → interior → rental income loop", kycStatus: "Verified", recommendedAction: "Cross-check company registrations", transactionChain: "ACC9900 → RealEstate → Interior → ACC9900" },
  // Structuring x3
  { id: "ALT-2024-0849", fraudType: "Structuring/Smurfing", fraudColor: fraudTypes[2].color, account: "XXXX9999", amount: "₹4,90,000", riskScore: 88, channel: "Cash", timeDetected: "08/03/2026 08:30", shapReason: "Sub-threshold deposits across 10 branches + same beneficiary", description: "₹49K × 10 branches → single account, all same day", kycStatus: "Minimal KYC", recommendedAction: "File CTR + STR", transactionChain: "10 branches × ₹49K → ACC9999" },
  { id: "ALT-2024-0856", fraudType: "Structuring/Smurfing", fraudColor: fraudTypes[2].color, account: "XXXX1122", amount: "₹76,00,000", riskScore: 92, channel: "NEFT", timeDetected: "07/03/2026 12:00", shapReason: "Fan-in pattern + collective threshold breach", description: "8 accounts each ₹9.5L same day → single ACC, totaling ₹76L", kycStatus: "Under Review", recommendedAction: "Block account + investigate", transactionChain: "8 accounts × ₹9.5L → ACC1122" },
  { id: "ALT-2024-0863", fraudType: "Structuring/Smurfing", fraudColor: fraudTypes[2].color, account: "XXXX2233", amount: "₹9,86,000", riskScore: 90, channel: "IMPS", timeDetected: "05/03/2026 09:00", shapReason: "34 micro-transactions ₹29K each + new account cluster", description: "34 IMPS of ₹29K from 34 new accounts to same destination", kycStatus: "Minimal KYC", recommendedAction: "Mule network investigation", transactionChain: "34 sources × ₹29K → single destination" },
  // Dormant x3
  { id: "ALT-2024-0850", fraudType: "Dormant Activation", fraudColor: fraudTypes[3].color, account: "XXXX2021", amount: "₹1,50,00,000", riskScore: 85, channel: "RTGS", timeDetected: "08/03/2026 07:00", shapReason: "3+ year dormancy + immediate offshore wire", description: "Dormant since 2021, receives ₹1.5Cr, wires offshore in 6hrs", kycStatus: "Stale KYC", recommendedAction: "Freeze + update KYC", transactionChain: "External RTGS → ACC2021 → SWIFT offshore" },
  { id: "ALT-2024-0857", fraudType: "Dormant Activation", fraudColor: fraudTypes[3].color, account: "XXXX4455", amount: "₹28,00,000", riskScore: 96, channel: "RTGS+UPI", timeDetected: "06/03/2026 16:00", shapReason: "3yr dormancy + spike magnitude 5600%", description: "Dormant 3yr, ₹28L RTGS in, ₹27.5L out via 4 UPI in 90min", kycStatus: "Stale KYC", recommendedAction: "Immediate freeze", transactionChain: "RTGS → ACC4455 → 4 UPI destinations" },
  { id: "ALT-2024-0864", fraudType: "Dormant Activation", fraudColor: fraudTypes[3].color, account: "XXXX6677", amount: "₹6,20,000", riskScore: 99, channel: "NEFT", timeDetected: "04/03/2026 11:00", shapReason: "Post-mortem activity + unknown device", description: "Deceased customer account shows activity 8 months after death", kycStatus: "Deceased", recommendedAction: "Freeze + report to police", transactionChain: "Unknown NEFT → ACC6677 (deceased)" },
  // Profile Mismatch x3
  { id: "ALT-2024-0852", fraudType: "Profile Mismatch", fraudColor: fraudTypes[4].color, account: "XXXX1919", amount: "₹5,00,000/day", riskScore: 94, channel: "UPI", timeDetected: "08/03/2026 13:00", shapReason: "Income-to-transaction ratio 3167% + student profile", description: "19yr student receiving 50 business payments of ₹10K daily", kycStatus: "Minimal KYC", recommendedAction: "Mule recruitment check", transactionChain: "3 corp accounts → ACC1919 × 50 txn/day" },
  { id: "ALT-2024-0858", fraudType: "Profile Mismatch", fraudColor: fraudTypes[4].color, account: "XXXX8899", amount: "₹38,00,000", riskScore: 87, channel: "Mixed", timeDetected: "05/03/2026 08:00", shapReason: "Student account ₹38L in 30 days + lifestyle inconsistency", description: "22yr student receives ₹38L across multiple channels in 30 days", kycStatus: "Verified", recommendedAction: "Enhanced due diligence", transactionChain: "Multiple sources → ACC8899 (₹38L/30 days)" },
  { id: "ALT-2024-0865", fraudType: "Profile Mismatch", fraudColor: fraudTypes[4].color, account: "XXXX3456", amount: "₹22,00,000", riskScore: 91, channel: "RTGS", timeDetected: "03/03/2026 14:00", shapReason: "KYC update 2 days before large transaction", description: "KYC updated (income ₹3L→₹25L), then ₹22L received", kycStatus: "Recently Updated", recommendedAction: "Verify KYC changes", transactionChain: "KYC update → 2 days → ₹22L RTGS inflow" },
  // Mule x3
  { id: "ALT-2024-0853", fraudType: "Mule Account", fraudColor: fraudTypes[5].color, account: "XXXX5511", amount: "₹8,00,000", riskScore: 85, channel: "NEFT", timeDetected: "08/03/2026 14:30", shapReason: "New account + immediate forwarding + overseas destination", description: "6-week old account forwards ₹5-8L overseas weekly", kycStatus: "Basic KYC", recommendedAction: "Close account + investigate", transactionChain: "Inflow → ACC5511 → overseas (2hr turnaround)" },
  { id: "ALT-2024-0859", fraudType: "Mule Account", fraudColor: fraudTypes[5].color, account: "XXXX7722", amount: "₹47,00,000", riskScore: 98, channel: "Mixed", timeDetected: "04/03/2026 09:30", shapReason: "MSME front + fan-in 23:1 + no trade docs", description: "3-month MSME receives ₹47L from 23 individuals, forwards ₹45L overseas", kycStatus: "Basic KYC", recommendedAction: "Freeze + STR + police report", transactionChain: "23 individuals → ACC7722 (MSME) → overseas import" },
  { id: "ALT-2024-0866", fraudType: "Mule Account", fraudColor: fraudTypes[5].color, account: "XXXX9933", amount: "₹9,80,000", riskScore: 94, channel: "UPI", timeDetected: "02/03/2026 16:00", shapReason: "Device change + elderly account + immediate forwarding", description: "Senior citizen account used by unknown device, ₹9.8L forwarded same day", kycStatus: "Verified", recommendedAction: "Contact account holder", transactionChain: "Inflow → ACC9933 (elderly) → unknown destination" },
];
