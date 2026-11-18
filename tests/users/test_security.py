"""Tests for password hashing and access tokens (FR-01, QR-04).

The malformed-hash tests are one per early-exit path of verify_password; they are the basis paths
used in the white-box analysis (docs/m2/danish-whitebox.md).
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.users.security import (
    TokenData,
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(scope="module")
def secret_hash() -> str:
    """One stored hash of "secret", shared because each hash costs 600000 PBKDF2 iterations."""
    return hash_password("secret")


# ---------- password hashing ----------


def test_hash_is_not_the_plain_password(secret_hash: str) -> None:
    assert secret_hash != "secret"
    assert "secret" not in secret_hash


def test_two_hashes_of_the_same_password_differ_because_of_the_salt(secret_hash: str) -> None:
    assert hash_password("secret") != secret_hash


def test_stored_hash_records_algorithm_and_iterations(secret_hash: str) -> None:
    algorithm, iterations, salt_b64, hash_b64 = secret_hash.split("$")

    assert algorithm == "pbkdf2_sha256"
    assert iterations == "600000"
    assert salt_b64
    assert hash_b64


def test_verify_accepts_the_correct_password(secret_hash: str) -> None:
    assert verify_password("secret", secret_hash) is True


def test_verify_rejects_a_wrong_password(secret_hash: str) -> None:
    assert verify_password("wrong", secret_hash) is False


# ---------- malformed stored hashes: False, never an exception ----------


def test_verify_returns_false_for_wrong_number_of_parts() -> None:
    assert verify_password("secret", "pbkdf2_sha256$600000$onlythreeparts") is False


def test_verify_returns_false_for_unknown_algorithm(secret_hash: str) -> None:
    _, iterations, salt_b64, hash_b64 = secret_hash.split("$")
    stored = f"md5${iterations}${salt_b64}${hash_b64}"

    assert verify_password("secret", stored) is False


def test_verify_returns_false_for_non_numeric_iterations(secret_hash: str) -> None:
    algorithm, _, salt_b64, hash_b64 = secret_hash.split("$")
    stored = f"{algorithm}$many${salt_b64}${hash_b64}"

    assert verify_password("secret", stored) is False


def test_verify_returns_false_for_zero_iterations(secret_hash: str) -> None:
    algorithm, _, salt_b64, hash_b64 = secret_hash.split("$")
    stored = f"{algorithm}$0${salt_b64}${hash_b64}"

    assert verify_password("secret", stored) is False


def test_verify_returns_false_for_invalid_base64(secret_hash: str) -> None:
    algorithm, iterations, _, _ = secret_hash.split("$")
    stored = f"{algorithm}${iterations}$not*base64!${'%%%%'}"

    assert verify_password("secret", stored) is False


# ---------- access tokens ----------


def test_token_round_trip_gives_user_id_and_role() -> None:
    token = create_access_token(user_id=7, role="STUDENT")

    data = decode_access_token(token)

    assert data == TokenData(user_id=7, role="STUDENT")


def test_token_with_one_character_changed_is_rejected() -> None:
    header, payload, signature = create_access_token(user_id=7, role="STUDENT").split(".")
    # Change the FIRST signature character: all 6 of its bits are real data, whereas the last
    # character carries padding bits and changing it might not alter the decoded signature.
    changed = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(TokenError):
        decode_access_token(f"{header}.{payload}.{changed}")


def test_token_signed_with_another_secret_is_rejected() -> None:
    claims = {"sub": "7", "role": "STUDENT", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    forged = jwt.encode(claims, "not-the-cfbs-secret-but-long-enough-for-hs256", algorithm="HS256")

    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_expired_token_is_rejected() -> None:
    token = create_access_token(user_id=7, role="STUDENT", expires_in=timedelta(seconds=-1))

    with pytest.raises(TokenError):
        decode_access_token(token)
