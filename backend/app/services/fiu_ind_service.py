import httpx


class FIUIndService:
    def __init__(self, api_url: str, mtls_cert_path: str, mtls_key_path: str):
        self.base_url = api_url
        self.mtls_cert_path = mtls_cert_path
        self.mtls_key_path = mtls_key_path

    async def submit_str(self, str_xml: str, digital_signature: str) -> dict:
        async with httpx.AsyncClient(
            cert=(self.mtls_cert_path, self.mtls_key_path)
        ) as client:
            response = await client.post(
                f"{self.base_url}/v2/str/submit",
                json={
                    "str": str_xml,
                    "digitalSignature": digital_signature,
                    "submissionType": "STR",
                },
                timeout=30.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def submit_ctr(self, ctr_xml: str) -> dict:
        async with httpx.AsyncClient(
            cert=(self.mtls_cert_path, self.mtls_key_path)
        ) as client:
            response = await client.post(
                f"{self.base_url}/v2/ctr/submit",
                json={"ctr": ctr_xml, "submissionType": "CTR"},
                timeout=30.0,
            )
            return response.json() if response.status_code == 200 else {}

    async def get_submission_status(self, reference_id: str) -> dict:
        async with httpx.AsyncClient(
            cert=(self.mtls_cert_path, self.mtls_key_path)
        ) as client:
            response = await client.get(
                f"{self.base_url}/v2/submissions/{reference_id}/status", timeout=10.0
            )
            return response.json() if response.status_code == 200 else {}
