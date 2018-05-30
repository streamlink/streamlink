from __future__ import absolute_import
import hashlib

from Crypto.Cipher import AES

from streamlink.compat import is_py3


def evp_bytestokey(password, salt, key_len, iv_len):
    """
    Python implementation of OpenSSL's EVP_BytesToKey()
    :param password: or passphrase
    :param salt: 8 byte salt
    :param key_len: length of key in bytes
    :param iv_len:  length of IV in bytes
    :return: (key, iv)
    """
    d = d_i = b''
    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_len], d[key_len:key_len + iv_len]


def decrypt_openssl(data, passphrase, key_length=32):
    if data.startswith(b"Salted__"):
        salt = data[len(b"Salted__"):AES.block_size]
        key, iv = evp_bytestokey(passphrase, salt, key_length, AES.block_size)
        d = AES.new(key, AES.MODE_CBC, iv)
        out = d.decrypt(data[AES.block_size:])
        return unpad_pkcs5(out)


def unpad_pkcs5(padded):
    if is_py3:
        return padded[:-padded[-1]]
    else:
        return padded[:-ord(padded[-1])]
