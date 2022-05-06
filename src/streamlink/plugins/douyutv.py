import hashlib
import re
import time

import js2py

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream

API_URL = "https://www.douyu.com/lapi/live/getH5Play/{room_id}"
VAPI_URL = "https://v.douyu.com/api/stream/getStreamUrl"

ROUTES = {
    "ws-h5": "main",
    "tct-h5": "backup5",
    "ali-h5": "backup6",
    "other": "other"
}
RATES = {0: "BD10M", 4: "BD4M", 1: "SD", 2: "HD", 3: "TD", 5: "BD"}

_url_re = re.compile(
    r"""
    http(s)?://
    (?:
        (?P<subdomain>.+)
        \.
    )?
    douyu.com/
    (?:
        show/(?P<vid>[^/&?]+)|
        (?P<roomid>\d+)|
        topic/\w+\?rid=(?P<rid>\d+)
    )
""", re.VERBOSE)

_room_online_re = re.compile(r"/member/report/\?rid=(?P<roomid>\d+)")

_room_schema = validate.Schema(
    {
        "data":
        validate.any(
            None, {
                "rtmp_url":
                validate.text,
                "rtmp_live":
                validate.text,
                "cdnsWithName":
                validate.all(
                    validate.any([],
                                 validate.all([
                                     {
                                         "name": validate.text,
                                         "cdn": validate.text
                                     },
                                 ])),
                    validate.transform(lambda cdns: dict([(e['name'], e['cdn'])
                                                          for e in cdns]))),
                "multirates":
                validate.all(
                    validate.any([],
                                 validate.all([
                                     {
                                         "name": validate.text,
                                         "rate": int
                                     },
                                 ])),
                    validate.transform(lambda cdns: dict(
                        [(e['name'], e['rate']) for e in cdns]))),
                "rate":
                int,
                "rtmp_cdn":
                validate.text
            }),
        "error":
        validate.all(validate.transform(int),
                     validate.transform(lambda x: x == 0))
    }, validate.get("data"))

_video_schema = validate.Schema(
    {
        "data":
        validate.any(
            None,
            validate.all(
                {
                    "thumb_video":
                    validate.all(
                        dict,
                        validate.transform(lambda x: dict(
                            [(ek, ev.get("url")) for ek, ev in x.items()])))
                },
                validate.transform(
                    lambda x: {k: v
                               for k, v in x.get('thumb_video').items()}))),
        "error":
        validate.all(validate.transform(int),
                     validate.transform(lambda x: x == 0))
    }, validate.get("data"))


def urldecode(qs):
    return dict([x.split("=") for x in qs.split("&")])


def md5_compat(content):
    m = hashlib.md5()
    m.update(str(content).encode("utf-8"))
    return m.hexdigest()


class CryptoJS:
    __slots__ = ("MD5", )

    def __init__(self):
        self.MD5 = md5_compat


JS_CTX = js2py.EvalJs({'CryptoJS': CryptoJS()})


class Douyutv(Plugin):
    '''
    斗鱼直播: https://www.douyu.com/9999
    斗鱼视频: https://v.douyu.com/show/aRbBv3o63ZDv6PYV
    '''
    js_ctx_initd = False

    @classmethod
    def can_handle_url(cls, url):
        '''
        override method to validate url input
        '''
        return _url_re.match(url)

    # @classmethod
    # def stream_weight(cls, stream):
    #     # if stream in STREAM_WEIGHTS:
    #     #     return STREAM_WEIGHTS[stream], "douyutv"
    #     return Plugin.stream_weight(stream)

    @staticmethod
    def simple_re_validate(content, name, pattern, pos, _type):
        _re = re.compile(pattern)
        _schema = validate.Schema(
            validate.all(validate.transform(_re.search), validate.get(pos),
                         validate.transform(_type)))
        return _schema.validate(content, name=name)

    @staticmethod
    def generateDeviceId():
        return md5_compat(time.time())

    def __js_ctx_init(self, html):
        # TODO: need thread-safe ?
        if not self.js_ctx_initd:
            param = Douyutv.simple_re_validate(html, "sign_param",
                                               r"function ub98484234\(([^,]*)",
                                               1, str)
            const = Douyutv.simple_re_validate(
                html, "sign_const",
                r"var %s=\[[^]]*\]" % param[:len(param) - 1], 0, str)
            function = Douyutv.simple_re_validate(
                html, "sign_function",
                r"function ub98484234.*return eval\(strc\)\(%s[^}]*;\}" % param,
                0, str)

            # print("%s;%s"%(const, function))

            JS_CTX.execute(";".join([const, function]))
            self.js_ctx_initd = True

    def __generate_sign(self, html, room_id):

        self.__js_ctx_init(html)

        did = Douyutv.generateDeviceId()
        tt = int(time.time())

        return urldecode(JS_CTX.ub98484234(room_id, did, tt))

    @staticmethod
    def __valid_address(html, pattern, _type=str):
        maybe = re.findall(pattern, html)
        if not maybe:
            return None
        return _type(maybe[0])

    def __parse_video_stream(self, url):
        html = self.session.http.get(url)
        vid = Douyutv.__valid_address(html.text, '"vid":"([^"]*)"', str)
        if not vid:
            self.logger.warn(
                "{target} is recognized by Douyutv, but  not valid.".format(
                    target=url))
            return

        pid = Douyutv.simple_re_validate(html.text, "point_id",
                                         r'"point_id":(\d+)', 1, int)
        # self.logger.debug("vid: %s pid: %s"%(vid, pid))
        sign = self.__generate_sign(html.text, pid)
        sign['vid'] = vid

        res = self.session.http.post(VAPI_URL,
                                     data=sign,
                                     cookies={"dy_did": sign['did']})
        # self.logger.debug(res.json())
        video = self.session.http.json(res, schema=_video_schema)
        for source, addr in video.items():
            self.logger.debug("m3u8: name:{name}, addres:{address}".format(
                name=source, address=addr))
            yield source, HLSStream(self.session, addr)

    def __parse_live_stream(self, url):
        html = self.session.http.get(url)

        # 以https://www.douyu.com/90016为例, url后缀数字为90016, 但对应roomid为532152
        # https://www.douyu.com/99999999 符合正则匹配, 但是却无效
        room_id = Douyutv.__valid_address(html.text, r'room_id ?= ?(\d*);', int)
        if not room_id:
            self.logger.warn(
                "{target} is recognized by Douyutv, but is not valid.".format(
                    target=url))
            return
        online = True if _room_online_re.search(html.text) else False
        if not online:
            self.logger.warn("Stream currently unavailable: 未开播")
            return

        def fetch_stream_info(room_id, data, rate=None, cdn=None):
            if rate is not None and type(rate) == int:
                data['rate'] = rate
            if cdn is not None and type(cdn) == str:
                data['cdn'] = cdn
            res = self.session.http.post(API_URL.format(room_id=room_id),
                                         data=data)
            return self.session.http.json(res, schema=_room_schema)

        sign = self.__generate_sign(html.text, room_id)
        pre_room = fetch_stream_info(room_id, sign)
        for cdnName, cdn in pre_room["cdnsWithName"].items():
            for rateName, rate in pre_room["multirates"].items():
                real_room = fetch_stream_info(room_id, sign, rate, cdn)
                rtmp_address = "{rtmp_url}/{rtmp_live}".format(
                    rtmp_url=real_room["rtmp_url"],
                    rtmp_live=real_room["rtmp_live"])
                name = "{cdn}_{rate}".format(cdn=ROUTES.get(cdn, "main"),
                                             rate=RATES.get(rate, "BD"))
                self.logger.debug(
                    "rtmp: name: {cdn}({rate}), address: {addr}".format(
                        cdn=cdnName, rate=rateName, addr=rtmp_address))
                yield name, HTTPStream(self.session, url=rtmp_address)

    def _get_streams(self):
        '''
        override method to get stream links
        seesion : Streamlink

        {name: stream} or (name, stream)
        '''
        match = _url_re.match(self.url)
        subdomain = match.group("subdomain")

        if subdomain == 'v':
            yield from self.__parse_video_stream(self.url)
            return
        yield from self.__parse_live_stream(self.url)


__plugin__ = Douyutv
