export type ParsedShapReason = {
  raw: string;
  driver: string;
  impact: number | null;
  direction: "increase" | "decrease" | "neutral";
  detail?: string;
};

const SHAP_DRIVER_LABELS: Record<string, string> = {
  amount_log: "Large transfer amount (log-transformed)",
  amount_near_ctr_threshold: "Transfer amount near CTR threshold",
  velocity_1h: "High 1-hour transaction velocity",
  velocity_24h: "High 24-hour transaction velocity",
  channel_risk: "Risky transaction channel",
  pagerank: "Account centrality in transaction graph",
  neighbor_fraud_ratio: "High fraud ratio among neighboring accounts",
  dormant_account_activity: "Dormant account reactivation",
  round_tripping_pattern: "Round-tripping transaction pattern",
  high_value_round_trip: "High-value round-trip movement",
};

export function formatImpactPoints(value: number): string {
  const formatted = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return `${value > 0 ? "+" : ""}${formatted} pts`;
}

function titleCaseWords(value: string): string {
  if (!value) return value;
  const upperWords = new Set(["upi", "imps", "rtgs", "neft", "ctr", "shap"]);
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      if (upperWords.has(lower)) return lower.toUpperCase();
      return lower.charAt(0).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

function normalizeToken(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function formatShapDriver(rawDriver: string): string {
  const source = rawDriver.trim();
  const low = source.toLowerCase();

  const highAmount = /^high_amount_(.+)$/i.exec(source);
  if (highAmount) {
    return `High transfer amount (${highAmount[1].replace(/_/g, " ")})`;
  }

  const elevatedAmount = /^elevated_amount_(.+)$/i.exec(source);
  if (elevatedAmount) {
    return `Elevated transfer amount (${elevatedAmount[1].replace(/_/g, " ")})`;
  }

  const velocity1h = /^velocity_1h_(\d+)_txns?$/i.exec(source);
  if (velocity1h) {
    return `High 1-hour transaction velocity (${velocity1h[1]} transactions)`;
  }

  const elevatedVelocity1h = /^elevated_velocity_1h_(\d+)$/i.exec(source);
  if (elevatedVelocity1h) {
    return `Elevated 1-hour transaction velocity (${elevatedVelocity1h[1]} transactions)`;
  }

  const multiHopVelocity = /^high_value_multi_hop_velocity_1h_(\d+)$/i.exec(source);
  if (multiHopVelocity) {
    return `High-value multi-hop transfer burst (${multiHopVelocity[1]} transactions in 1 hour)`;
  }

  const repeatedSubThreshold = /^repeated_sub_threshold_transfers_(\d+)_in_24h$/i.exec(source);
  if (repeatedSubThreshold) {
    return `Repeated sub-threshold transfers (${repeatedSubThreshold[1]} in 24 hours)`;
  }

  const sharedDevice = /^device_shared_(\d+)_accounts$/i.exec(source);
  if (sharedDevice) {
    return `Shared device linked to multiple accounts (${sharedDevice[1]} accounts)`;
  }

  const highRiskChannel = /^high_risk_channel_(.+)$/i.exec(source);
  if (highRiskChannel) {
    return `High-risk transaction channel (${highRiskChannel[1].toUpperCase()})`;
  }

  const velocity24h = /^velocity_24h_(\d+)_txns?$/i.exec(source);
  if (velocity24h) {
    return `High 24-hour transaction velocity (${velocity24h[1]} transactions)`;
  }

  const normalized = normalizeToken(low);
  if (normalized in SHAP_DRIVER_LABELS) {
    return SHAP_DRIVER_LABELS[normalized];
  }

  const readable = source
    .replace(/_/g, " ")
    .replace(/\b1h\b/gi, "1-hour")
    .replace(/\b24h\b/gi, "24-hour")
    .replace(/\btxns?\b/gi, "transactions")
    .replace(/\s+/g, " ")
    .trim();

  return titleCaseWords(readable);
}

export function parseShapReason(raw: string): ParsedShapReason {
  const trimmed = raw.trim();
  const signedImpactMatch = trimmed.match(/([+-]\d+(?:\.\d+)?)\s*(?:pts?|points?)?\s*$/i);

  let impact: number | null = null;
  let driverToken = trimmed;
  let detail: string | undefined;

  if (signedImpactMatch && signedImpactMatch.index !== undefined) {
    impact = Number(signedImpactMatch[1]);
    driverToken = trimmed.slice(0, signedImpactMatch.index).replace(/[:\-–]\s*$/, "").trim();
  } else {
    const featureValueMatch = trimmed.match(/^(.+?)\s*:\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (featureValueMatch) {
      driverToken = featureValueMatch[1].trim();
      detail = `Model feature value: ${featureValueMatch[2]}`;
    }
  }

  const driver = formatShapDriver(driverToken);
  const direction = impact === null ? "neutral" : impact > 0 ? "increase" : impact < 0 ? "decrease" : "neutral";

  return {
    raw: trimmed,
    driver,
    impact,
    direction,
    detail,
  };
}

export function parseShapReasons(values?: string[] | null): ParsedShapReason[] {
  return (values || []).filter(Boolean).map(parseShapReason);
}

export function toShapSummaryLines(values?: string[] | null, limit = 3): string[] {
  return parseShapReasons(values)
    .slice(0, limit)
    .map((reason) => (reason.impact === null ? reason.driver : `${reason.driver} (${formatImpactPoints(reason.impact)})`));
}
