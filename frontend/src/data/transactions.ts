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

const channels: Transaction["channel"][] = ["UPI", "RTGS", "NEFT", "IMPS", "CASH", "Card"];
const accounts = [
  "XXXX4421", "XXXX7781", "XXXX1001", "XXXX1002", "XXXX9999",
  "XXXX2021", "XXXX1919", "XXXX5501", "XXXX8800", "XXXX5503",
  "XXXX3301", "XXXX2200", "XXXX6600", "XXXX4400", "XXXX8811",
  "XXXX3344", "XXXX5566", "XXXX7788", "XXXX9900", "XXXX1122",
];
const branches = ["Mumbai Main", "Delhi CP", "Bangalore MG", "Chennai Anna", "Kolkata Park", "Hyderabad Sec", "Pune FC", "Ahmedabad CG"];
const flagOptions = ["Velocity", "Dormant", "Layering", "Round-Trip", "Structuring", "Mule", "KYC Mismatch", "New Device", "High Amount", "Unusual Time"];
const statuses = ["Cleared", "Flagged", "Pending", "Cleared", "Cleared"];

function randomAmount(): { formatted: string; num: number } {
  const amt = Math.floor(Math.random() * 4950000 + 5000);
  const formatted = "₹" + amt.toLocaleString("en-IN");
  return { formatted, num: amt };
}

function randomTime(idx: number): string {
  const h = String(Math.floor(Math.random() * 24)).padStart(2, "0");
  const m = String(Math.floor(Math.random() * 60)).padStart(2, "0");
  const s = String(Math.floor(Math.random() * 60)).padStart(2, "0");
  const day = String(Math.min(8, 1 + Math.floor(idx / 7))).padStart(2, "0");
  return `${day}/03/2026 ${h}:${m}:${s}`;
}

export function generateTransactions(count = 50): Transaction[] {
  return Array.from({ length: count }, (_, i) => {
    const srcIdx = Math.floor(Math.random() * accounts.length);
    let destIdx = Math.floor(Math.random() * accounts.length);
    if (destIdx === srcIdx) destIdx = (destIdx + 1) % accounts.length;
    const { formatted, num } = randomAmount();
    const riskScore = Math.floor(Math.random() * 100);
    const flags: string[] = [];
    if (riskScore > 50) {
      const numFlags = Math.floor(Math.random() * 3) + 1;
      for (let j = 0; j < numFlags; j++) {
        const f = flagOptions[Math.floor(Math.random() * flagOptions.length)];
        if (!flags.includes(f)) flags.push(f);
      }
    }
    return {
      txnId: `TXN-${String(800000 + i)}`,
      source: accounts[srcIdx],
      destination: accounts[destIdx],
      amount: formatted,
      amountNum: num,
      channel: channels[Math.floor(Math.random() * channels.length)],
      timestamp: randomTime(i),
      riskScore,
      status: riskScore > 80 ? "Flagged" : riskScore > 60 ? "Pending" : statuses[Math.floor(Math.random() * statuses.length)],
      flags,
      branch: branches[Math.floor(Math.random() * branches.length)],
    };
  });
}
