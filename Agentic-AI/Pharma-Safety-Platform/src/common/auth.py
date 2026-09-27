"""
Real Cognito JWT verification -- this is the module get_authenticated_reviewer_id()
in review/api.py delegates to. Reviewer identity comes from here and only here,
never from the request body, so a decision can never be misattributed even if a
request were altered in transit (the 21 CFR Part 11 attribution requirement
the design names explicitly).

REQUIRES a real Cognito User Pool provisioned, and COGNITO_REGION /
COGNITO_USER_POOL_ID / COGNITO_APP_CLIENT_ID set in the environment. Cannot
verify a real token without that pool existing -- the verification logic
itself (signature check, expiry check, audience check) is standard and
correct, but there is no live JWKS endpoint to test it against in this
sandbox.
"""

import os
import time

import requests
from jose import jwt
from jose.exceptions import JWTError

_jwks_cache: dict | None = None
_jwks_cache_fetched_at: float = 0.0
JWKS_CACHE_TTL_SECONDS = 3600


class TokenVerificationError(Exception):
    """Raised on any failure to verify a bearer token -- signature mismatch,
    expiry, wrong audience, or a malformed token. A caller must treat this
    as 'not authenticated', never as 'authenticated as unknown'."""


def _get_jwks() -> dict:
    """Fetches and caches Cognito's public signing keys. Cached for an hour
    -- Cognito rotates keys rarely, and re-fetching on every request would
    add real latency to every single review decision for no benefit."""
    global _jwks_cache, _jwks_cache_fetched_at

    if _jwks_cache is not None and (time.time() - _jwks_cache_fetched_at) < JWKS_CACHE_TTL_SECONDS:
        return _jwks_cache

    region = os.environ["COGNITO_REGION"]
    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"

    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    _jwks_cache = response.json()
    _jwks_cache_fetched_at = time.time()
    return _jwks_cache


def _find_signing_key(jwks: dict, kid: str) -> dict:
    for key in jwks["keys"]:
        if key["kid"] == kid:
            return key
    raise TokenVerificationError(
        f"No matching signing key found for kid={kid!r} -- the JWKS cache may be "
        "stale after a key rotation; this is not silently retried automatically, "
        "since silently trusting a token against a refetched key set without "
        "re-validating everything else would be a real hole."
    )


def verify_reviewer_token(bearer_token: str) -> str:
    """
    Verifies a Cognito-issued JWT and returns the reviewer's stable identity
    (the token's 'sub' claim -- a UUID Cognito assigns, not an email that
    could change). Raises TokenVerificationError on any failure; there is
    no fallback identity and no partial trust.
    """
    if not bearer_token:
        raise TokenVerificationError("No bearer token provided.")

    try:
        unverified_header = jwt.get_unverified_header(bearer_token)
    except JWTError as e:
        raise TokenVerificationError(f"Malformed token header: {e}") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise TokenVerificationError("Token header has no 'kid' -- cannot select a signing key.")

    jwks = _get_jwks()
    signing_key = _find_signing_key(jwks, kid)

    app_client_id = os.environ["COGNITO_APP_CLIENT_ID"]

    try:
        claims = jwt.decode(
            bearer_token,
            signing_key,
            algorithms=["RS256"],
            audience=app_client_id,
            options={"require_exp": True, "require_sub": True},
        )
    except JWTError as e:
        raise TokenVerificationError(f"Token signature/claims verification failed: {e}") from e

    if claims.get("token_use") != "id":
        raise TokenVerificationError(
            f"Expected an ID token (token_use='id'), got {claims.get('token_use')!r}. "
            "Access tokens don't carry the reviewer's identity claims this system needs."
        )

    return claims["sub"]
