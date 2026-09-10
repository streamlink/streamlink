import base64

import pytest

from streamlink.utils.crypto import decrypt_openssl, encrypt_openssl, evp_bytestokey


def test_evp_bytestokey():
    assert evp_bytestokey(b"hello", b"", 16, 16) == (
        b"]A@*\xbcK*v\xb9q\x9d\x91\x10\x17\xc5\x92",
        b"(\xb4n\xd3\xc1\x11\xe8Q\x02\x90\x9b\x1c\xfbP\xea\x0f",
    )


@pytest.mark.parametrize(
    "data",
    [
        # Old fixture data
        # > echo "this is a test" | openssl enc -aes-256-cbc -pass pass:streamlink -base64
        pytest.param(b"U2FsdGVkX18nVyJ6Y+ksOASMSHKuRoQ9b4DKHuPbyQc=", id="random-salt"),
        # Custom KDF salt: no prefix with -S since OpenSSL 3.0
        # > (
        # >   printf 'Salted__\x01\x23\x45\x67\x89\xab\xcd\xef'
        # >   echo "this is a test" | openssl enc -aes-256-cbc -md md5 -S 0123456789abcdef -pass pass:streamlink
        # > ) | base64
        pytest.param(b"U2FsdGVkX18BI0VniavN772AmBz3M35evEFhaFfFvQo=", id="null-byte-salt"),
    ],
)
def test_decrypt_openssl(data: str):
    decoded = base64.b64decode(data, validate=True)
    assert decrypt_openssl(decoded, b"streamlink") == b"this is a test\n"


def test_encrypt_openssl(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("streamlink.utils.crypto.urandom", lambda *_, **__: b"\x01\x23\x45\x67\x89\xab\xcd\xef")
    encrypted = encrypt_openssl(b"this is a test\n", b"streamlink")
    assert base64.b64encode(encrypted) == b"U2FsdGVkX18BI0VniavN772AmBz3M35evEFhaFfFvQo="


@pytest.mark.parametrize("key_length", range(16, 32 + 1, 8))
def test_encrypt_decrypt_openssl(key_length: int):
    message = b"this is a test\n"
    passphrase = b"streamlink"
    assert decrypt_openssl(encrypt_openssl(message, passphrase, key_length), passphrase, key_length) == message
