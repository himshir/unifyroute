"""
Unit tests for shared.security encrypt/decrypt functions.
"""
import os
import base64
import pytest
from shared.security import encrypt_secret, decrypt_secret

@pytest.fixture(autouse=True)
def mock_master_key(monkeypatch):
    key = base64.urlsafe_b64encode(b"0" * 32).decode("utf-8")
    monkeypatch.setenv("VAULT_MASTER_KEY", key)


def test_encrypt_decrypt_roundtrip():
    secret = "my-super-secret-key-123!"
    iv, ciphertext = encrypt_secret(secret)
    assert iv is not None
    assert ciphertext is not None
    assert ciphertext != secret
    
    decrypted = decrypt_secret(iv, ciphertext)
    assert decrypted == secret

def test_different_ivs_produce_different_ciphertext():
    secret = "hello world"
    iv1, ct1 = encrypt_secret(secret)
    iv2, ct2 = encrypt_secret(secret)
    
    assert iv1 != iv2
    assert ct1 != ct2

def test_decrypt_empty_string():
    # Should handle empty gracefully if applicable, or raise.
    # The current implementation returns an active encryption. Let's just roundtrip.
    iv, ct = encrypt_secret("")
    dec = decrypt_secret(iv, ct)
    assert dec == ""

def test_corrupted_ciphertext_raises():
    secret = "valid"
    iv, ct = encrypt_secret(secret)
    corrupted_ct = ct[:-2] + b"XX"  # Mutate last bytes
    
    with pytest.raises(Exception):
        # depending on encryption method, this could be ValueError or cryptography exceptions
        decrypt_secret(iv, corrupted_ct)
