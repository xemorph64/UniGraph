import httpx
from typing import Optional


class FinacleService:
    def __init__(self, api_url: str, client_id: str, client_secret: str):
        self.base_url = api_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None

    async def _get_token(self) -> str:
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10.0,
            )
            if response.status_code == 200:
                self._access_token = response.json()["access_token"]
                return self._access_token
            raise Exception("Failed to get Finacle access token")

    async def mark_lien(self, account_id: str, amount: float, reason: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/accounts/{account_id}/lien",
                json={"amount": amount, "reason": reason, "lienType": "INVESTIGATION"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def freeze_account(self, account_id: str, reason: str, case_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/accounts/{account_id}/freeze",
                json={
                    "reason": reason,
                    "caseId": case_id,
                    "freezeType": "INVESTIGATION",
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def get_account_details(self, account_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/accounts/{account_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def hold_transaction(self, txn_id: str, reason: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/transactions/{txn_id}/hold",
                json={"reason": reason},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            return response.json() if response.status_code == 200 else {}
