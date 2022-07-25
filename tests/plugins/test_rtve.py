from streamlink.plugins.rtve import Rtve, ZTNR
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtve(PluginCanHandleUrl):
    __plugin__ = Rtve

    should_match = [
        "https://www.rtve.es/play/videos/directo/la-1/",
        "https://www.rtve.es/play/videos/directo/canales-lineales/24h/",
        "https://www.rtve.es/play/videos/rebelion-en-el-reino-salvaje/mata-reyes/5803959/",
    ]

    should_not_match = [
        "https://www.rtve.es",
        "http://www.rtve.es/directo/la-1",
        "http://www.rtve.es/directo/la-2/",
        "http://www.rtve.es/directo/teledeporte/",
        "http://www.rtve.es/directo/canal-24h/",
        "http://www.rtve.es/infantil/directo/",
    ]


def test_translate():
    # real payload with modified end (IEND chunk of size 0), to reduce test size
    data = \
        "iVBORw0KGgoAAAANSUhEUgAAAVQAAAFUCAIAAAD08FPiAAACr3RFWHRXczlVSWdtM2ZPTGY4b2R4" \
        "dWo5aHZnRlRhOndvZEtxN3pLOG5oNGRpbT1vREBTWHhOMGtzUVomNndAWkV5cz1GOUlCSiYxdDcy" \
        "QmdDOFM2NGFVJmh1Nzk2bUpwOFVJOE1DJlpAY2lzdGcmbEUmRE5DZFV4SHpEOFgvLmppZ1l4b3M1" \
        "QU1lOnl3ZS04VlBwQkZvLlFMUWZHTy1vQjNVeHhfVDF1JkRSQTpPP2J4Wm0zbFlxS3IjAEhEX1JF" \
        "QURZJSUwNTYwNzI4Mjg4MzUyNjQyMzUxMTA0Mzg0NzI4NzY4NDEyODAzODU0ODMwMDQ3NzcwNDEx" \
        "MDAyODE1MzM3NDU3ODAxMDg3MjgxNTg1MzMzNDE3MTYxMTE4NzQ1MTU3MjYxOTUwNzI4NzEyNDgw" \
        "MzI4NTM1ODM1ODU3MzQyNzE0NjcyODE2NTgzNDI4NTE0NTg1MzIwMzgxODU3NDY0NzUwODI3OTQ0" \
        "ODg3NjEzMTUzNDMxMTUxNzYzNDU1NzE0MDA1MDUzNDIxODE0ODYyNDIzODM2MTczMzQ0NjAwNTIw" \
        "NTU2NDYyNDgxODYzNDA2MzA4MTE0ODUxMTQ2Mzg2MzYyMjQ4Mjc3MjIyMjUzNjMxMjI1MjEzMTU0" \
        "NjI1NjIyMjM3MTA4NjEwNjI0NTYyNTMxNTA2ODEyMjQ2MzYzNzE0MzY4MDU1MTgxNTQ2NTU3MTMx" \
        "NTI0NzU4MTU2NjAxMjY0MjA1MDU2MzcwMDM3NzcwMjA0MTYxMzE3MjQxMTI2NzYzMzUyNjY3NTQ1" \
        "NTA1MTUxNTc2NTEzMTUwNjcxNDcyMDI2MTQyMjczNTI4NzExNjA4NTU3NjIzMzMxMzU0NDM1Mzgw" \
        "MTI0MTQzMTU1MTMyNzc4ODI1MjcyMjUwMjY4MzYyMDUzMjQzNjA0MTYyMzkhB8fSAAAAAElFTkQAAAAACg=="

    assert list(ZTNR.translate(data)) == [
        (
            "HD_READY",
            "https://rtvehlsvodlote7modo2.rtve.es/mediavodv2/resources/TE_NGVA/mp4/5/3/1656573649835.mp4/video.m3u8"
            + "?hls_no_audio_only=true&idasset=6638770"
        ),
    ]
