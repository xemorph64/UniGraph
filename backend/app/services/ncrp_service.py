import httpx


class NCRPService:
    def __init__(self, api_url: str, api_key: str):
        self.base_url = api_url
        self.api_key = api_key

    async def submit_complaint(self, complaint_data: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/complaints",
                json=complaint_data,
                headers={"X-API-Key": self.api_key},
                timeout=30.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def auto_lien(self, complaint_id: str, account_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/complaints/{complaint_id}/auto-lien",
                json={"accountId": account_id},
                headers={"X-API-Key": self.api_key},
                timeout=15.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def report_status(self, complaint_id: str, status: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/complaints/{complaint_id}/status",
                json={"status": status},
                headers={"X-API-Key": self.api_key},
                timeout=15.0,
            )
            return response.json() if response.status_code == 200 else {}
