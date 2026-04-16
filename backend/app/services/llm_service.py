"""
LLM service using Groq API (llama-3.1-70b-versatile).
Data stays secure — Groq is used for hackathon demo only.
In production, replace with on-premise Qwen 3.5 9B via vLLM.
"""

import httpx
import structlog
from typing import Optional
from ..config import settings

logger = structlog.get_logger()

STR_NARRATIVE_PROMPT = """You are UniGRAPH's AML investigation assistant for Union Bank of India.
Analyze the provided transaction patterns and generate a professional STR narrative.

STRICT GUIDELINES:
1. ONLY use data explicitly provided in the context below.
2. DO NOT invent account names, branch details, or transaction histories.
3. If a specific data point (like SHAP reasons) is missing, do not guess it.
4. Maintain a formal, neutral tone. No speculation.
5. Reference specific Transaction IDs and exact amounts.

Generate a Suspicious Transaction Report (STR) narrative:

Case ID: {case_id}
Flagged Account: {account_id}
Risk Score: {risk_score}/100
Risk Level: {risk_level}

Transaction Chain:
{transaction_chain}

Rule Violations Detected:
{rule_violations}

Top Risk Factors (SHAP):
{shap_reasons}

Generate a concise STR narrative (max 500 words) covering:
1. Nature of suspicion
2. Transaction pattern description
3. Why this matches a known fraud typology
4. Recommended investigation steps
"""

CASE_SUMMARY_PROMPT = """Summarize this fraud investigation case for an investigator:

Account: {account_id}
Risk Score: {risk_score}
Alerts: {alert_count}
Rule violations: {rule_violations}
Transaction pattern: {pattern_description}

Provide a 3-sentence summary of:
1. What happened
2. Why it's suspicious
3. What to investigate next
"""


class LLMService:
    def __init__(self):
        self.api_url = settings.GROQ_API_URL
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL

    async def _call_groq(
        self, system_prompt: str, user_message: str, max_tokens: int = 1000
    ) -> str:
        if not self.api_key or self.api_key == "your_groq_api_key_here":
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
            "temperature": 0.3,
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
        return """SUSPICIOUS TRANSACTION REPORT — DRAFT

Based on the analysis performed by UniGRAPH's ML ensemble, this account has been
flagged for exhibiting patterns consistent with rapid layering fraud. Multiple
high-value transactions were detected within a compressed time window, with funds
moving through several intermediary accounts before reaching the destination.

The transaction velocity (8 transactions in 47 minutes) significantly exceeds the
account's historical baseline. The GraphSAGE GNN model detected that this account
belongs to a community with elevated fraud risk (community risk score: 0.87).

RECOMMENDED INVESTIGATION STEPS:
1. Freeze account pending investigation under PMLA 2002 Section 12
2. Request KYC documents from originating branch
3. Cross-reference beneficiary accounts with MuleHunter.AI database
4. File STR with FIU-IND within 7 days if suspicion is confirmed

[Note: This is a demo response. Configure GROQ_API_KEY for live LLM generation.]
"""

    async def generate_str_narrative(self, case_data: dict) -> str:
        """Generate STR narrative for a fraud case."""
        prompt = STR_NARRATIVE_PROMPT.format(
            case_id=case_data.get("case_id", "CASE-DEMO-001"),
            account_id=case_data.get("account_id", "ACC-UNKNOWN"),
            risk_score=case_data.get("risk_score", 0),
            risk_level=case_data.get("risk_level", "HIGH"),
            transaction_chain=case_data.get("transaction_chain", "No chain data"),
            rule_violations=", ".join(case_data.get("rule_violations", [])),
            shap_reasons="\n".join(case_data.get("shap_top3", [])),
        )
        system = (
            "You are a senior AML compliance officer at Union Bank of India. "
            "You write precise, professional STR reports in plain English. "
            "Be specific about amounts, account IDs, and timestamps."
        )
        return await self._call_groq(system, prompt, max_tokens=800)

    async def summarize_case(self, case_data: dict) -> str:
        """Generate a quick case summary for investigators."""
        prompt = CASE_SUMMARY_PROMPT.format(**case_data)
        system = "You are a fraud investigation assistant. Be concise and actionable."
        return await self._call_groq(system, prompt, max_tokens=300)

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
