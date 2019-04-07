import re
import logging
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from time import time
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
from Crypto import Hash
from Crypto.Hash import HMAC, BLAKE2b
from Crypto.Random import get_random_bytes

log = logging.getLogger(__name__)

base_url = 'https://idp.securetve.com/rest/'
base_path = 'v2/platforms/urn:foxnews:com:sp:site:2/'
guard_url = base_url + 'security/' + base_path + 'tokens/guard'
fingerprint_url = base_url + 'authn/' + base_path + 'init/fingerprint'
id_url = base_url + 'authn/' + base_path + 'tokens/id'
access_url = base_url + 'authz/' + base_path + 'resources/FoxNews'
crossover_url = base_url + 'authz/' + base_path + 'tokens/crossover'
stream_url = 'https://fncgohls-i.akamaihd.net/hls/live/263399/FNCGOHLSv2/master.m3u8'

class Foxnews(Plugin):
    url_re = re.compile(r"https?://(?:www\.|video\.)?foxnews.com")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _pad (self, data):
        BLOCK_SIZE = 16
        pad = BLOCK_SIZE - len(data) % BLOCK_SIZE
        return data + pad * chr(pad).encode()

    def _create_fingerprint(self, options):
        fingerprint = BLAKE2b.new(
                digest_bits=128, 
                key=get_random_bytes(64)
            ).hexdigest()
        fingerprint += str(int(round(time()*1000)))
        for key in options:
            fingerprint += "_" + options[key]
        return fingerprint

    def _create_key(self, km, extFn): 
        ikm = b64decode(km['ikm'].encode())
        salt = b64decode(km['salt'].encode())
        size = int(km['bytes'])
        return HKDF(ikm, size, salt, extFn)

    def _encrypt_fingerprint(self, fingerprint, key_material):
        extFn = hash=getattr(Hash, key_material['extFn'].upper())
        hmacFn = hash=getattr(Hash, key_material['hmacFn'].upper())
        enc_key = self._create_key(key_material['enc_km'], extFn)
        hmac_key = self._create_key(key_material['hmac_km'], extFn)
        fingerprint = "id:".encode() + b64encode(fingerprint.encode())
        fp_hmac = b64encode(HMAC.new(
            b64encode(hmac_key), 
            msg=fingerprint, 
            digestmod=hmacFn
            ).digest())
        fp_with_hmac = b64encode(fingerprint + "~hmac:".encode() + fp_hmac);
        cipher = AES.new(enc_key, AES.MODE_ECB)
        log.debug("\n%s%s\n%s%s\n%s%s\n%s%s\n%s%s\n" %(
            '  enc_key = ',  enc_key,
            '  hmac_key = ',  hmac_key,
            '  fingerprint = ',  fingerprint,
            '  fp_hmac = ',  fp_hmac,
            '  fp_with_hmac = ', fp_with_hmac 
        ))
        return b64encode(cipher.encrypt(self._pad(fp_with_hmac)))

    def _create_encrypted_fingerprint(self, key_material):
        options = key_material['fp_params']
        fingerprint = self._create_fingerprint(options)
        return self._encrypt_fingerprint(fingerprint, key_material)

    def _get_streams(self):
        response = self.session.http.get(guard_url)
        guard_token = self.session.http.json(response)['guard_token']
        response = self.session.http.get(fingerprint_url, headers={
            'Akamai-Token-Guard': guard_token})
        key_material = self.session.http.json(response)
        enc_fp = self._create_encrypted_fingerprint(key_material).decode()
        response = self.session.http.get(id_url, headers={
            'Akamai-Token-Guard': guard_token, 
            'Akamai-Authentication': "fingerprint/ob " + enc_fp})
        identity_token = self.session.http.json(response)['identity_token']
        response = self.session.http.get(access_url, headers={
            'Akamai-Token-ID': identity_token})
        access_token = self.session.http.json(response)['access_token']
        response = self.session.http.get(crossover_url, headers={
            'Akamai-Token-Access': access_token})
        crossover_token = self.session.http.json(response)['crossover_token']
        mrl = stream_url + '?hdnea=' + crossover_token
        log.debug("stream url: " + mrl)
        return HLSStream.parse_variant_playlist(self.session, mrl)

__plugin__ = Foxnews
