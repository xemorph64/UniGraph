export interface Transaction {
  txnId: string;
  source: string;
  destination: string;
  amount: string;
  amountNum: number;
  channel: "UPI" | "RTGS" | "NEFT" | "IMPS" | "CASH" | "Card";
  timestamp: string;
  riskScore: number;
  status: string;
  flags: string[];
  branch: string;
}
