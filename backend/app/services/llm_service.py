"""
LLM service using Groq API (llama-3.1-70b-versatile).
Data stays secure — Groq is used for hackathon demo only.
In production, replace with on-premise Qwen 3.5 9B via vLLM.
"""

import httpx
import structlog
from typing import Any
from ..config import settings

logger = structlog.get_logger()

STR_NARRATIVE_PROMPT = """You are UniGRAPH's AML investigation assistant for Union Bank of India.
You analyze suspicious transaction patterns and generate FIU-IND compliant STR narratives.
Always be professional, evidence-grounded, and cite transaction IDs, amounts, channels, and timing where available.
Respond in formal banking compliance language.

Generate a Suspicious Transaction Report (STR) narrative for the following case:

Case ID: {case_id}
Flagged Account: {account_id}
Risk Score: {risk_score}/100
Risk Level: {risk_level}
Primary Fraud Type: {primary_fraud_type}

Transaction Chain:
{transaction_chain}

Transaction Snapshot:
{transaction_snapshot}

Graph Context:
{graph_summary}

Rule Violations Detected:
{rule_violations}

Top Risk Factors (SHAP):
{shap_reasons}

Investigator Case Notes:
{case_notes}

Current System Recommendation:
{recommendation}

Generate a detailed STR draft (350-650 words) with these sections:
1. Executive summary of suspicion
2. Evidence and transaction behavior timeline
3. Typology mapping and rationale
4. Immediate risk and customer exposure
5. Recommended investigation and compliance actions
6. Filing readiness statement for FIU-IND
"""

CASE_SUMMARY_PROMPT = """Prepare a detailed investigator note for this fraud case:

Account: {account_id}
Risk Score: {risk_score}
Risk Level: {risk_level}
Alerts: {alert_count}
Primary Fraud Type: {primary_fraud_type}
Rule violations: {rule_violations}
Top SHAP factors:
{shap_reasons}
Current recommendation: {recommendation}
Graph context: {graph_summary}
Transaction snapshot: {transaction_snapshot}
Transaction pattern: {pattern_description}

Respond with concise sections:
1. Why this case was flagged
2. What evidence is strongest
3. What to verify immediately
4. Suggested next investigator actions
Use clear bullet points and keep it practical for on-screen triage.
"""


class LLMService:
    def __init__(self):
        base_url = str(getattr(settings, "LLM_URL", "") or "").rstrip("/")
        if settings.GROQ_API_URL:
            self.api_url = settings.GROQ_API_URL
        elif base_url:
            self.api_url = f"{base_url}/chat/completions"
        else:
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL

    @staticmethod
    def _stringify_list(value: Any, *, default: str = "None") -> str:
        if value is None:
            return default
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return "\n".join(cleaned) if cleaned else default
        text = str(value).strip()
        return text if text else default

    @staticmethod
    def _stringify_rule_violations(value: Any) -> str:
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return ", ".join(cleaned) if cleaned else "none"
        text = str(value or "").strip()
        return text if text else "none"

    async def _call_groq(
        self, system_prompt: str, user_message: str, max_tokens: int = 1000
    ) -> str:
        if not self.api_key or self.api_key in {
            "your_groq_api_key_here",
            "PASTE_YOUR_GROQ_API_KEY_HERE",
        }:
            logger.warning("groq_api_key_not_set")
            return self._mock_llm_response(user_message)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.25,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error("groq_api_error", error=str(e))
                return self._mock_llm_response(user_message)

    def _mock_llm_response(self, context: str) -> str:
        """Fallback when Groq API key is not configured."""
        return """INVESTIGATION NOTE — DRAFT

1) Why this case was flagged:
The account shows high-risk behavioral anomalies including elevated transfer velocity,
multi-hop fund movement, and rule-violation overlap indicating coordinated laundering
behavior rather than isolated customer activity.

2) Strongest evidence:
- Transaction frequency in a compressed window is materially above baseline.
- Counterparty flow pattern indicates layering or pass-through behavior.
- SHAP factors point to amount/channel/velocity as primary risk drivers.

3) Immediate investigator actions:
1. Validate source-of-funds and beneficiary linkage for top-risk transactions.
2. Cross-check linked accounts/devices for recurrence across historical alerts.
3. Escalate for supervisory review if corroborating evidence persists.
4. Prepare STR evidence bundle for FIU-IND filing timeline.

[Note: Demo fallback response. Configure GROQ_API_KEY in root .env for live LLM output.]
"""

    async def generate_str_narrative(self, case_data: dict) -> str:
        """Generate STR narrative for a fraud case."""
        prompt = STR_NARRATIVE_PROMPT.format(
            case_id=case_data.get("case_id", "CASE-DEMO-001"),
            account_id=case_data.get("account_id", "ACC-UNKNOWN"),
            risk_score=case_data.get("risk_score", 0),
            risk_level=case_data.get("risk_level", "HIGH"),
            primary_fraud_type=case_data.get("primary_fraud_type", "UNSPECIFIED"),
            transaction_chain=case_data.get("transaction_chain", "No chain data"),
            transaction_snapshot=case_data.get(
                "transaction_snapshot", "No transaction snapshot available"
            ),
            graph_summary=case_data.get("graph_summary", "No graph summary available"),
            rule_violations=self._stringify_rule_violations(
                case_data.get("rule_violations", [])
            ),
            shap_reasons=self._stringify_list(case_data.get("shap_top3", [])),
            case_notes=case_data.get("case_notes") or "No investigator notes provided",
            recommendation=case_data.get("recommendation", "REVIEW"),
        )
        system = (
            "You are a senior AML compliance officer at Union Bank of India. "
            "You write precise, professional STR reports in plain English. "
            "Be specific about amounts, account IDs, timestamps, channels, and rule rationale. "
            "Use section headers and numbered actions."
        )
        return await self._call_groq(system, prompt, max_tokens=1200)

    async def summarize_case(self, case_data: dict) -> str:
        """Generate a detailed case summary for investigators."""
        prompt = CASE_SUMMARY_PROMPT.format(
            account_id=case_data.get("account_id", "ACC-UNKNOWN"),
            risk_score=case_data.get("risk_score", 0),
            risk_level=case_data.get("risk_level", "UNKNOWN"),
            alert_count=case_data.get("alert_count", 1),
            primary_fraud_type=case_data.get("primary_fraud_type", "UNSPECIFIED"),
            rule_violations=self._stringify_rule_violations(
                case_data.get("rule_violations", [])
            ),
            shap_reasons=self._stringify_list(case_data.get("shap_reasons", [])),
            recommendation=case_data.get("recommendation", "REVIEW"),
            graph_summary=case_data.get("graph_summary", "No graph summary available"),
            transaction_snapshot=case_data.get(
                "transaction_snapshot", "No transaction snapshot available"
            ),
            pattern_description=case_data.get(
                "pattern_description", "No pattern description available"
            ),
        )
        system = (
            "You are a fraud investigation assistant writing analyst-ready notes. "
            "Be specific, concise, and operationally useful for immediate triage."
        )
        return await self._call_groq(system, prompt, max_tokens=700)

    async def answer_investigator_question(self, question: str, context: dict) -> str:
        """Answer investigator's natural language questions about a case."""
        system = (
            "You are UniGRAPH's AML investigation assistant. "
            "Answer questions about fraud cases using the provided context. "
            "Always cite specific data points. Be direct and professional."
        )
        user_msg = f"""Case context: {context}

Investigator question: {question}

Answer in 2-3 sentences using specific data from the context."""
        return await self._call_groq(system, user_msg, max_tokens=400)


llm_service = LLMService()
