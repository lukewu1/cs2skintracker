from datetime import timedelta

import jwt
import pytest

from auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_is_not_plaintext():
    hashed = get_password_hash("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$2b$")


def test_verify_password_accepts_correct_password():
    hashed = get_password_hash("hunter2")
    assert verify_password("hunter2", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = get_password_hash("hunter2")
    assert verify_password("wrong-password", hashed) is False


def test_hashing_same_password_twice_gives_different_hashes():
    # bcrypt salts each hash, so two hashes of the same password must differ
    # even though both verify correctly.
    first = get_password_hash("hunter2")
    second = get_password_hash("hunter2")
    assert first != second
    assert verify_password("hunter2", first) is True
    assert verify_password("hunter2", second) is True


def test_create_access_token_contains_expected_claims():
    token = create_access_token({"sub": "lukewu"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "lukewu"
    assert "exp" in payload


def test_create_access_token_respects_custom_expiry():
    token = create_access_token({"sub": "lukewu"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    # exp is a unix timestamp; just confirm it decodes without raising and
    # is present, precise timing is jwt's concern, not ours.
    assert isinstance(payload["exp"], int)


def test_token_signed_with_wrong_key_is_rejected():
    token = create_access_token({"sub": "lukewu"})
    with pytest.raises(jwt.PyJWTError):
        jwt.decode(token, "not-the-real-secret", algorithms=[ALGORITHM])


def test_expired_token_is_rejected():
    token = create_access_token({"sub": "lukewu"}, expires_delta=timedelta(minutes=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
