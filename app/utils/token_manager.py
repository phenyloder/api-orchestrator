import os
from dotenv import load_dotenv
load_dotenv()
import time
import threading
import requests
import logging
from typing import Optional

logger = logging.getLogger("token_manager")

class TokenManager:
    """
    Handles OAuth2 token retrieval and caching for enterprise OpenAI key usage.
    Fetches a new token only when expired, with a buffer for best performance.
    """
    _lock = threading.Lock()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.client_id = os.getenv("CISCO_CLIENT_ID")
        self.client_secret = os.getenv("CISCO_CLIENT_SECRET")
        self.token_url = os.getenv("CISCO_AZURE_TOKEN_URL")
        self.token: Optional[str] = None
        self.expiry: float = 0
        self.expiry_buffer = int(os.getenv("TOKEN_EXPIRY_BUFFER", 300))  # seconds
        if not all([self.client_id, self.client_secret, self.token_url]):
            logger.error("Missing required environment variables for token manager.")
            raise RuntimeError("CISCO_CLIENT_ID, CISCO_CLIENT_SECRET, and CISCO_AZURE_TOKEN_URL must be set.")

    def _fetch_token(self):
        payload = "grant_type=client_credentials"
        import base64
        value = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode('utf-8')).decode('utf-8')
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {value}"
        }
        try:
            logger.info("Requesting new OAuth2 token from Azure...")
            resp = requests.post(self.token_url, headers=headers, data=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            self.token = access_token
            self.expiry = time.time() + expires_in
            logger.info("Successfully obtained new token.")
        except Exception as e:
            logger.error(f"Failed to fetch token: {e}")
            raise RuntimeError(f"Failed to fetch token: {e}")

    def get_token(self) -> str:
        """
        Returns a valid token, refreshing if expired or near expiry.
        """
        with self._lock:
            now = time.time()
            if not self.token or (self.expiry - now) < self.expiry_buffer:
                self._fetch_token()
            return self.token

get_token = TokenManager().get_token 