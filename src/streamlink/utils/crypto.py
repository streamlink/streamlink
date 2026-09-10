# ruff: file-ignore[unused-import]
from __future__ import annotations

from os import urandom


# re-export pycryptodome / pycryptodomex stuff in a single place
# so packagers don't have to maintain dozens of patches
try:
    # pycryptodome (drop-in replacement for the old PyCrypto library)
    from Crypto.Cipher import AES, PKCS1_v1_5
    from Crypto.Hash import MD5, SHA256
    from Crypto.PublicKey import RSA
    from Crypto.Util.Padding import pad, unpad
except ImportError:  # pragma: no cover
    # pycryptodomex (independent of the old PyCrypto library)
    from Cryptodome.Cipher import AES, PKCS1_v1_5  # type: ignore
    from Cryptodome.Hash import MD5, SHA256  # type: ignore
    from Cryptodome.PublicKey import RSA  # type: ignore
    from Cryptodome.Util.Padding import pad, unpad  # type: ignore


def evp_bytestokey(password: bytes, salt: bytes, key_len: int, iv_len: int) -> tuple[bytes, bytes]:
    """
    Python implementation of OpenSSL's EVP_BytesToKey()
    :param password: or passphrase
    :param salt: 8 byte salt
    :param key_len: length of key in bytes
    :param iv_len:  length of IV in bytes
    :return: (key, iv)
    """
    d = d_i = b""
    while len(d) < key_len + iv_len:
        d_i = MD5.new(d_i + password + salt).digest()
        d += d_i
    return d[:key_len], d[key_len : key_len + iv_len]


def encrypt_openssl(data: bytes, passphrase: bytes, key_length: int = 32) -> bytes:
    salt = urandom(8)
    key, iv = evp_bytestokey(passphrase, salt, key_length, AES.block_size)
    padded = pad_pkcs5(data, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded)

    return b"Salted__" + salt + encrypted


def decrypt_openssl(data: bytes, passphrase: bytes, key_length: int = 32) -> bytes | None:
    if not data.startswith(b"Salted__"):
        return None

    salt = data[len(b"Salted__") : AES.block_size]
    key, iv = evp_bytestokey(passphrase, salt, key_length, AES.block_size)
    d = AES.new(key, AES.MODE_CBC, iv)
    out = d.decrypt(data[AES.block_size :])

    return unpad_pkcs5(out)


def pad_pkcs5(data: bytes, block_size: int = AES.block_size) -> bytes:
    padding_len = block_size - (len(data) % block_size)
    return data + bytes(padding_len * [padding_len])


def unpad_pkcs5(padded):
    return padded[: -padded[-1]]
