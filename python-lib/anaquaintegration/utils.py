import base64
import dataiku
import hashlib
import hmac
import json
import logging
import pandas as pd
import requests
import secrets
import time

from dataiku.customrecipe import get_recipe_config
from urllib.parse import urlparse

def make_nonce_b64(num_bytes: int = 20) -> str:
    # 20 random bytes, base64-encoded
    return base64.b64encode((secrets.token_bytes(num_bytes)).lower()).decode("ascii")

def aqx_request(
    method: str,
    base_url: str,
    api_path: str,
    api_key_id: str,
    api_key_content: str,
    **kwargs):
    
    return internal_aqx_request(
        method=method,
        base_url=base_url,
        api_path=api_path,
        api_key_id=api_key_id,
        api_key_content=api_key_content,
        timeout=30,
        **kwargs
    )
    
def internal_aqx_request(
    method: str,
    base_url: str,
    api_path: str,
    api_key_id: str,
    api_key_content: str,
    **kwargs):
    """
    Convenience wrapper: generates a fresh token for *every* call (AQX token is single-use).

    base_url example: "https://<implementation-name>"
    api_path  example: "/api/v10.10/Reference/TherapeuticArea/All"
    """

    # The secret must be used in bytes, not with the raw string
    # provided copied from the Anaqua UI:
    key_bytes = base64.b64decode(api_key_content, validate=True)

    # Building paths:
    full_url = base_url + api_path
    path = urlparse(full_url).path
    assert path.startswith("/api")
    rel_api_path = path[len("/api"):]

    # Generating timestamp and nonce:
    ts = int(time.time())
    nonce = make_nonce_b64()

    # First part of the token is in plain content in lower cases:
    plain_content = f"{api_key_id}:{ts}:{nonce}".lower()

    # Second part of the token uses the plain content,
    # concatenate it with method and api path, convert
    # everything in lower case, hash it with the secret
    # key and encoded it in base 64:
    to_hash = f"{api_key_id}:{ts}:{nonce}:{method}:{rel_api_path}".lower()
    hashed_content = hmac.new(
        key_bytes,
        to_hash.encode("utf-8"),
        hashlib.sha256
    ).digest()
    encoded_content = base64.b64encode(hashed_content).decode("ascii")

    # Unique token data to be used:
    token_data = f"{plain_content}:{encoded_content}"

    # Building the additional headers needed to send a request:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"X-API-Token {token_data}"
    headers["LawEngineEnabled"] = "true"
    headers["Content-Type"] = "application/json"
    headers["accept"] = "text/plain"

    # Sending the request and returning the response:
    resp = requests.request(
        method=method,
        url=full_url,
        headers=headers,
        **kwargs
    )

    return resp

def validate_and_load_config(cfg):
    """
    Validate recipe configuration and return a normalized config dict.
    Raises ValueError if something is wrong.
    """
    
    if "api-key" not in cfg:
        raise ValueError(f"Missing API Key preset. Select an API Key preset in the recipe configuration")

    # ---- Base URL validation ----
    if "baseUrl" not in cfg['api-key']:
        raise ValueError("Missing required recipe parameter: 'baseUrl'")

    base_url = cfg.get("api-key").get("baseUrl")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("Parameter 'baseUrl' must be a non-empty string")

    if not base_url.startswith(("http://", "https://")):
        raise ValueError(
            "Parameter 'baseUrl' must start with 'http://' or 'https://'"
        )

    # ---- API key validation ----
    api_key = cfg.get("api-key").get("credentials")
    if not isinstance(api_key, dict):
        raise ValueError("Parameter 'credentials' must be a credential object")

    key_id = api_key.get("user")
    key_secret = api_key.get("password")

    if not key_id or not key_secret:
        raise ValueError(
            "API credentials are incomplete. "
            "Both 'user' and 'password' must be provided."
        )

    return {
        "base_url": base_url.rstrip("/"),
        "key_id": key_id,
        "key_secret": key_secret
    }

def run_initialization():
    cfg          = get_recipe_config()
    verbose_mode = bool(cfg.get("verbose", False))
    config       = validate_and_load_config(cfg)
    BASE_URL     = config["base_url"]
    KEY_ID       = config["key_id"]
    KEY_SECRET   = config["key_secret"]

    logger = logging.getLogger("Anaqua Integration Recipes")
    logging.basicConfig(
        level=logging.DEBUG if verbose_mode else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )

    logger.debug("********** ---[ Anaqua Integration Recipes ]--- **********")
    logger.debug("get_recipe_config():")
    logger.debug(get_recipe_config())
    
    return {
        "baseUrl": BASE_URL,
        "keyId": KEY_ID,
        "keySecret": KEY_SECRET,
        "verboseMode": verbose_mode,
        "logger": logger,
        "config": cfg
    }