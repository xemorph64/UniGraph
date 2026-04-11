export interface Alert {
  id: string;
  typology: string;
  riskScore: number;
  status: string;
  description: string;
}

export const alerts: Alert[] = [
  {
    id: "AL-001",
    typology: "Rapid Layering",
    riskScore: 96,
    status: "Pending Review",
    description:
      "₹20 Lakh split into four ₹5 Lakh chunks and instantly wired to crypto exchanges via 4 different savings accounts within 12 minutes.",
  },
  {
    id: "AL-002",
    typology: "Circular Transactions (Round-Tripping)",
    riskScore: 92,
    status: "Pending Review",
    description:
      "Company A transferred ₹50 Lakhs to Company B, B transferred ₹48 Lakhs to Company C, and C transferred ₹46 Lakhs back to Company A. All share the same Ultimate Beneficial Owner (UBO).",
  },
  {
    id: "AL-003",
    typology: "Structuring (Smurfing)",
    riskScore: 88,
    status: "Pending Review",
    description:
      "₹49,000 in cash deposited across 10 different bank branches on the same day, all converging into a single beneficiary account (Account X).",
  },
  {
    id: "AL-004",
    typology: "Dormant Account Activation",
    riskScore: 85,
    status: "Pending Review",
    description:
      "Savings account untouched since 2021 suddenly receives a ₹1.5 Crore RTGS transfer and wires the full amount offshore within 6 hours.",
  },
  {
    id: "AL-005",
    typology: "Customer Profile Mismatch",
    riskScore: 94,
    status: "Pending Review",
    description:
      "19-year-old student with zero declared income receiving 50 business payments of ₹10,000 each per day from corporate accounts across three states.",
  },
];
