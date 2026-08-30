from streamlink.plugins.rtve import ZTNR, Rtve
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRtve(PluginCanHandleUrl):
    __plugin__ = Rtve

    should_match = [
        "https://www.rtve.es/play/videos/directo/la-1/",
        "https://www.rtve.es/play/videos/directo/canales-lineales/24h/",
        "https://www.rtve.es/play/videos/informe-semanal/la-semilla-de-la-guerra/6670279/",
    ]

    should_not_match = [
        "https://www.rtve.es",
        "http://www.rtve.es/directo/la-1",
        "http://www.rtve.es/directo/la-2/",
        "http://www.rtve.es/directo/teledeporte/",
        "http://www.rtve.es/directo/canal-24h/",
        "http://www.rtve.es/infantil/directo/",
    ]


def test_translate_no_content():
    assert list(ZTNR.translate("")) == []


def test_translate_no_streams():
    # real payload without any tEXt chunks that match the expected format
    data = (
        "iVBORw0KGgoAAAANSUhEUgAAAsAAAAGMAQMAAADuk4YmAAAAA1BMVEX///+nxBvIAAAAAXRSTlMA"
        + "QObYZgAAADlJREFUeF7twDEBAAAAwiD7p7bGDlgYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        + "AAAAAAAAwAGJrAABgPqdWQAAAcp0RVh0ak9lNmRyNkUtV2hmeEE0dERMdS9FOTlCT2d3MF9HMDdG"
        + "RmxQNy1ZLTdFOFRac0MmbD93VEp5SENvUUlseVY1bjdrYmF2ZkhUUjc4aTBHAEBxY08zdk4yYldE"
        + "bm09TDVaNGMyVVpNdklVbS5LVUNCUTdZNVpfSUZMVmRMNlN0VE14TmFPLUFGaTF6ai9YenE6PVg9"
        + "dnJBb3BFU3BBJlpoWFViSER3MCZxbj9AS0d1Si5OSnAudiMwMTYxNDA2MDU2NjcyMDE3MzI4NTcw"
        + "ODcwMDc3MDI3NjIwNjczMTA0ODEyNDY3MzMwNzgxMDQwMTE4NzQ4MDYwMjIwODgxNTI0ODEzNjQ4"
        + "MjU0MTEyMzEyNjUxMzc2NTM3MTMzNzgwNTYwNDE0NjI4NDM1NjIzNTA1MTAxNjYwMDExNzE4MDQx"
        + "MTc3MDMxNTQ2MDEzNDUwMDQ2MTg4MDgwNzMxNDM3MjgwMDQ4NDA3Mzg0MzYxODA0NjU0NDYzMTY1"
        + "NDIxMzY4ODAzNTQ3MjMyMjYzODUwMzY5MTE3MTMwOTMzMjAwNDg1MDExNTE4MTgxMTgwMTAwNjU0"
        + "NTg1MzcxNDQ5MDM5MzY2ODMxNTc0MjUyNDVZsdrfAAAAAElFTkSuQmCC"
    )
    assert list(ZTNR.translate(data)) == []


def test_translate_has_streams():
    # real payload with modified end (IEND chunk of size 0), to reduce test size
    data = (
        "iVBORw0KGgoAAAANSUhEUgAAAVQAAAFUCAIAAAD08FPiAAACr3RFWHRXczlVSWdtM2ZPTGY4b2R4"
        + "dWo5aHZnRlRhOndvZEtxN3pLOG5oNGRpbT1vREBTWHhOMGtzUVomNndAWkV5cz1GOUlCSiYxdDcy"
        + "QmdDOFM2NGFVJmh1Nzk2bUpwOFVJOE1DJlpAY2lzdGcmbEUmRE5DZFV4SHpEOFgvLmppZ1l4b3M1"
        + "QU1lOnl3ZS04VlBwQkZvLlFMUWZHTy1vQjNVeHhfVDF1JkRSQTpPP2J4Wm0zbFlxS3IjAEhEX1JF"
        + "QURZJSUwNTYwNzI4Mjg4MzUyNjQyMzUxMTA0Mzg0NzI4NzY4NDEyODAzODU0ODMwMDQ3NzcwNDEx"
        + "MDAyODE1MzM3NDU3ODAxMDg3MjgxNTg1MzMzNDE3MTYxMTE4NzQ1MTU3MjYxOTUwNzI4NzEyNDgw"
        + "MzI4NTM1ODM1ODU3MzQyNzE0NjcyODE2NTgzNDI4NTE0NTg1MzIwMzgxODU3NDY0NzUwODI3OTQ0"
        + "ODg3NjEzMTUzNDMxMTUxNzYzNDU1NzE0MDA1MDUzNDIxODE0ODYyNDIzODM2MTczMzQ0NjAwNTIw"
        + "NTU2NDYyNDgxODYzNDA2MzA4MTE0ODUxMTQ2Mzg2MzYyMjQ4Mjc3MjIyMjUzNjMxMjI1MjEzMTU0"
        + "NjI1NjIyMjM3MTA4NjEwNjI0NTYyNTMxNTA2ODEyMjQ2MzYzNzE0MzY4MDU1MTgxNTQ2NTU3MTMx"
        + "NTI0NzU4MTU2NjAxMjY0MjA1MDU2MzcwMDM3NzcwMjA0MTYxMzE3MjQxMTI2NzYzMzUyNjY3NTQ1"
        + "NTA1MTUxNTc2NTEzMTUwNjcxNDcyMDI2MTQyMjczNTI4NzExNjA4NTU3NjIzMzMxMzU0NDM1Mzgw"
        + "MTI0MTQzMTU1MTMyNzc4ODI1MjcyMjUwMjY4MzYyMDUzMjQzNjA0MTYyMzkhB8fSAAAAAElFTkQAAAAACg=="
    )

    assert list(ZTNR.translate(data)) == [
        (
            "HD_READY",
            "https://rtvehlsvodlote7modo2.rtve.es/mediavodv2/resources/TE_NGVA/mp4/5/3/1656573649835.mp4/video.m3u8"
            + "?hls_no_audio_only=true&idasset=6638770",
        ),
    ]
