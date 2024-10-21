# ruff: noqa: F401
import hashlib


# re-export pycryptodome / pycryptodomex stuff in a single place
# so packagers don't have to maintain dozens of patches
try:
    # pycryptodome (drop-in replacement for the old PyCrypto library)
    from Crypto.Cipher import AES, PKCS1_v1_5
    from Crypto.Hash import SHA256
    from Crypto.PublicKey import RSA
    from Crypto.Util.Padding import pad, unpad
except ImportError:  # pragma: no cover
    # pycryptodomex (independent of the old PyCrypto library)
    from Cryptodome.Cipher import AES, PKCS1_v1_5  # type: ignore
    from Cryptodome.Hash import SHA256  # type: ignore
    from Cryptodome.PublicKey import RSA  # type: ignore
    from Cryptodome.Util.Padding import pad, unpad  # type: ignore


def evp_bytestokey(password, salt, key_len, iv_len):
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
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_len], d[key_len : key_len + iv_len]


def decrypt_openssl(data, passphrase, key_length=32):
    if data.startswith(b"Salted__"):
        salt = data[len(b"Salted__") : AES.block_size]
        key, iv = evp_bytestokey(passphrase, salt, key_length, AES.block_size)
        d = AES.new(key, AES.MODE_CBC, iv)
        out = d.decrypt(data[AES.block_size :])
        return unpad_pkcs5(out)


def unpad_pkcs5(padded):
    return padded[: -padded[-1]]
