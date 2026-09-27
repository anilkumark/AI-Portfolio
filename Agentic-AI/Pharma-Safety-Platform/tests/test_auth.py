"""
Tests the actual verification logic in src/common/auth.py against a real,
locally-generated RSA keypair and real signed JWTs -- proving the
signature/expiry/audience checks are correct, without needing a live
Cognito User Pool. This is the one thing that genuinely can be proven
without AWS: the crypto and claim-validation logic itself.

Cannot be tested here: that the JWKS URL construction and the real
Cognito token shape match what an actual pool issues -- that needs a
real pool.
"""

import base64
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from src.common import auth
from src.common.auth import TokenVerificationError, verify_reviewer_token

TEST_REGION = "us-east-1"
TEST_USER_POOL_ID = "us-east-1_TESTPOOL"
TEST_APP_CLIENT_ID = "test-app-client-id"
TEST_KID = "test-key-id"


def _b64url_uint(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


@pytest.fixture
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": TEST_KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
    }
    return private_key, jwk


@pytest.fixture(autouse=True)
def configured_env(monkeypatch):
    monkeypatch.setenv("COGNITO_REGION", TEST_REGION)
    monkeypatch.setenv("COGNITO_USER_POOL_ID", TEST_USER_POOL_ID)
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", TEST_APP_CLIENT_ID)
    # reset the module-level JWKS cache between tests
    auth._jwks_cache = None
    auth._jwks_cache_fetched_at = 0.0


def _install_fake_jwks(monkeypatch, jwk: dict):
    monkeypatch.setattr(auth, "_get_jwks", lambda: {"keys": [jwk]})


def _private_key_pem(private_key) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _sign_token(private_key, claims: dict) -> str:
    return jwt.encode(claims, _private_key_pem(private_key), algorithm="RS256", headers={"kid": TEST_KID})


def _valid_claims(**overrides) -> dict:
    claims = {
        "sub": "12345678-aaaa-bbbb-cccc-1234567890ab",
        "aud": TEST_APP_CLIENT_ID,
        "token_use": "id",
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
    }
    claims.update(overrides)
    return claims


def test_valid_token_returns_the_sub_claim(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    _install_fake_jwks(monkeypatch, jwk)
    token = _sign_token(private_key, _valid_claims())

    reviewer_id = verify_reviewer_token(token)
    assert reviewer_id == "12345678-aaaa-bbbb-cccc-1234567890ab"


def test_expired_token_rejected(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    _install_fake_jwks(monkeypatch, jwk)
    token = _sign_token(private_key, _valid_claims(exp=int(time.time()) - 60))

    with pytest.raises(TokenVerificationError):
        verify_reviewer_token(token)


def test_wrong_audience_rejected(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    _install_fake_jwks(monkeypatch, jwk)
    token = _sign_token(private_key, _valid_claims(aud="some-other-app-client-id"))

    with pytest.raises(TokenVerificationError):
        verify_reviewer_token(token)


def test_access_token_use_rejected_only_id_tokens_carry_identity(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    _install_fake_jwks(monkeypatch, jwk)
    token = _sign_token(private_key, _valid_claims(token_use="access"))

    with pytest.raises(TokenVerificationError, match="Expected an ID token"):
        verify_reviewer_token(token)


def test_token_signed_by_a_different_key_is_rejected(rsa_keypair, monkeypatch):
    _, jwk = rsa_keypair  # the JWKS we publish (the "real" Cognito key)
    _install_fake_jwks(monkeypatch, jwk)

    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged_token = _sign_token(attacker_key, _valid_claims())  # signed with a DIFFERENT private key

    with pytest.raises(TokenVerificationError):
        verify_reviewer_token(forged_token)


def test_missing_kid_in_header_rejected(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    _install_fake_jwks(monkeypatch, jwk)
    token = jwt.encode(_valid_claims(), _private_key_pem(private_key), algorithm="RS256")  # no kid header

    with pytest.raises(TokenVerificationError, match="no 'kid'"):
        verify_reviewer_token(token)


def test_empty_token_rejected():
    with pytest.raises(TokenVerificationError, match="No bearer token"):
        verify_reviewer_token("")


def test_unknown_kid_rejected(rsa_keypair, monkeypatch):
    private_key, jwk = rsa_keypair
    other_jwk = dict(jwk, kid="a-completely-different-kid")
    _install_fake_jwks(monkeypatch, other_jwk)  # JWKS only has a DIFFERENT kid published
    token = _sign_token(private_key, _valid_claims())

    with pytest.raises(TokenVerificationError, match="No matching signing key"):
        verify_reviewer_token(token)
