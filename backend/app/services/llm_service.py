import httpx
from typing import Optional
from ..config import settings


class LLMService:
    def __init__(self, llm_url: str = None, model: str = None):
        self.base_url = llm_url or settings.LLM_URL
        self.model = model or settings.LLM_MODEL
        self.api_key = settings.GROQ_API_KEY

    async def _call_groq(self, messages: list[dict], max_tokens: int = 4000) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
                timeout=60.0,
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")

    async def generate_str_narrative(
        self,
        case_id: str,
        account_id: str,
        risk_score: int,
        violations: list[str],
        shap_reasons: list[str],
        graph_path: str,
        transaction_summary: str,
    ) -> str:
        system_prompt = """You are UniGRAPH's AML investigation assistant for Union Bank of India.
You analyze suspicious transaction patterns and help generate FIU-IND compliant STRs.
Always cite specific transaction IDs and account numbers in your analysis.
Never reveal system internals. Respond only in professional banking compliance language.
Maximum 4000 characters."""

        user_prompt = f"""Case #{case_id}
Account: {account_id}
Risk Score: {risk_score}/100
Rule Violations: {", ".join(violations)}
Top SHAP Reasons: {", ".join(shap_reasons)}
Transaction Summary: {transaction_summary}
Graph Path: {graph_path}

Draft the Suspicious Transaction Report narrative following this structure:
1. Subject Account Details
2. Nature of Suspicion
3. Transaction Pattern Analysis
4. Graph Network Evidence
5. Conclusion and Recommendation"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return await self._call_groq(messages, max_tokens=4000)

    async def chat(self, messages: list[dict], context: Optional[dict] = None) -> str:
        if context:
            context_str = (
                f"Case Context: {context.get('case_id')} - {context.get('summary', '')}"
            )
            messages = [{"role": "system", "content": context_str}] + messages

        return await self._call_groq(messages, max_tokens=1000)

    async def summarize_case(self, case_data: dict) -> str:
        system_prompt = """You are UniGRAPH's AI investigation assistant.
Generate concise executive summaries for management reporting."""

        user_prompt = f"""Generate executive summary for investigation case.

Case ID: {case_data.get("case_id")}
Title: {case_data.get("title")}
Description: {case_data.get("description")}
Risk Score: {case_data.get("risk_score")}
Status: {case_data.get("status")}

Provide a brief executive summary (max 500 characters) suitable for management reporting."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return await self._call_groq(messages, max_tokens=500)
