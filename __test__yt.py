import re
import requests
import argparse
import logging
from contextlib import closing
from pathlib import Path
from typing import Mapping, Type

from streamlink import Streamlink
from streamlink.exceptions import NoPluginError
from streamlink.plugin import Plugin
from streamlink.stream.stream import Stream
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.times import LOCAL as LOCALTIMEZONE
from streamlink_cli.constants import STREAM_SYNONYMS
from streamlink_cli.output import FileOutput
from streamlink_cli.streamrunner import StreamRunner
from streamlink_cli.utils import Formatter, datetime

log = logging.getLogger(__name__)


def format_valid_streams(plugin: Plugin, streams: Mapping[str, Stream]) -> str:
    """Formats a dict of streams.

    Filters out synonyms and displays them next to
    the stream they point to.

    Streams are sorted according to their quality
    (based on plugin.stream_weight).

    """

    delimiter = ", "
    validstreams = []

    for name, stream in sorted(streams.items(), key=lambda s: plugin.stream_weight(s[0])):
        if name in STREAM_SYNONYMS:
            continue

        synonyms = [key for key, value in streams.items() if stream is value and key != name]

        if synonyms:
            joined = delimiter.join(synonyms)
            name = f"{name} ({joined})"

        validstreams.append(name)

    return delimiter.join(validstreams)


def resolve_stream_name(streams: Mapping[str, Stream], stream_name: str) -> str:
    """Returns the real stream name of a synonym."""

    if stream_name in STREAM_SYNONYMS and stream_name in streams:
        for name, stream in streams.items():
            if stream is streams[stream_name] and name not in STREAM_SYNONYMS:
                return name

    return stream_name


def get_formatter(plugin: Plugin):
    return Formatter(
        {
            "url": url,
            "plugin": lambda: plugin.module,
            "id": plugin.get_id,
            "author": plugin.get_author,
            "category": plugin.get_category,
            "game": plugin.get_category,
            "title": plugin.get_title,
            "time": lambda: datetime.now(tz=LOCALTIMEZONE),
        },
        {
            "time": lambda dt, fmt: dt.strftime(fmt),
        },
    )


def check_file_output(path: Path) -> FileOutput:
    """
    Checks if path already exists and asks the user if it should be overwritten if it does.
    """

    # rewrap path and resolve using `os.path.realpath` instead of `path.resolve()`
    # to avoid a pathlib issues on py39 and below
    realpath = path.resolve()

    print(f"Writing output to\n{realpath}")

    return FileOutput(filename=realpath)


def open_stream(stream):
    """Opens a stream and reads 8192 bytes from it.

    This is useful to check if a stream actually has data
    before opening the output.

    """
    # Attempts to open the stream
    stream_fd = stream.open()

    # Read 8192 bytes before proceeding to check for errors.
    # This is to avoid opening the output unnecessarily.
    print("Pre-buffering 8192 bytes")
    prebuffer = stream_fd.read(8192)

    if not prebuffer:
        stream_fd.close()
        raise ValueError("No data returned from stream")

    return stream_fd, prebuffer


# def set_option_test(streamlink: Streamlink):
#     import time
#     time.sleep(10)
#     streamlink.set_option('interface', '192.168.1.15')
#     print('New interface set!!!')


def output_stream(stream, output, formatter: Formatter):
    """Open stream, create output and finally write the stream to output."""

    # create output before opening the stream, so file outputs can prompt on existing output
    output = check_file_output(formatter.path(output))

    stream_fd, prebuffer = open_stream(stream)

    if isinstance(stream, HLSStream):
        print(f"HLS Record start timestamp: {stream.first_segment_timestamp}")
        print(f'Segment duration: {stream.segment_duration}')
    stream_fd.close()
    return True

    output.open()

    # from threading import Thread

    with closing(output):
        print("Writing stream to output")
        stream_runner = StreamRunner(stream_fd, output)
        # Thread(target=set_option_test, args=(stream.session,), daemon=True).start()
        stream_runner.run(prebuffer)

    return True


def handle_stream(plugin: Plugin, streams: Mapping[str, Stream], stream_name: str, output: str,) -> None:
    """Decides what to do with the selected stream."""

    stream_name = resolve_stream_name(streams, stream_name)
    stream = streams[stream_name]

    if isinstance(stream, DASHStream):
        print(
            f"DASH Record start timestamp: {int(stream.mpd.availabilityStartTime.timestamp() * 1000 + stream.mpd.periods[0].segmentList.presentationTimeOffset)}")

    # Find any streams with a '_alt' suffix and attempt
    # to use these in case the main stream is not usable.
    alt_streams = list(filter(lambda k: f"{stream_name}_alt" in k, sorted(streams.keys())))

    formatter = get_formatter(plugin)

    for name in [stream_name, *alt_streams]:
        stream = streams[name]
        stream_type = type(stream).shortname()

        stream.session.broadcast_start_time = plugin.broadcast_start_time
        print(f"Opening stream: {name} ({stream_type})")
        success = output_stream(stream, output, formatter)

        if success:
            break


chs = ["https://youtube.com/channel/UCq-Fj5jknLsUf-MWSy4_brA", "https://youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA", "https://youtube.com/channel/UCbCmjCuTUZos6Inko4u57UQ", "https://youtube.com/channel/UCpEhnqL0y41EpW2TvWAHD7Q", "https://youtube.com/channel/UCk8GzjMOrta8yxDcKfylJYw", "https://youtube.com/channel/UCvlE5gTbOvjiolFlEm-c_Ow", "https://youtube.com/channel/UCJplp5SjeGSdVdwsfb9Q7lQ", "https://youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw", "https://youtube.com/channel/UCFFbwnve3yF62-tVXkTyHqg", "https://youtube.com/channel/UCJ5v_MCY6GNUBTO8-D3XoAg", "https://youtube.com/channel/UCyoXW-Dse7fURq30EWl_CUA", "https://youtube.com/channel/UCOmHUn--16B90oW2L6FRR3A", "https://youtube.com/channel/UCBnZ16ahKA2DZ_T5W0FPUXg", "https://youtube.com/channel/UC6-F5tO8uklgE9Zy8IvbdFw", "https://youtube.com/channel/UC295-Dw_tDNtZXFeAPAW6Aw", "https://youtube.com/channel/UCcdwLMPsaU2ezNSJU1nFoBQ", "https://youtube.com/channel/UCppHT7SZKKvar4Oc9J4oljQ", "https://youtube.com/channel/UCLkAepWjdylmXSltofFvsYQ", "https://youtube.com/channel/UC3IZKseVpdzPSBaWxBxundA", "https://youtube.com/channel/UC55IWqFLDH1Xp7iu1_xknRA", "https://youtube.com/channel/UCP6uH_XlsxrXwZQ4DlqbqPg", "https://youtube.com/channel/UCaayLD9i5x4MmIoVZxXSv_g", "https://youtube.com/channel/UCffDXn7ycAzwL2LDlbyWOTw", "https://youtube.com/channel/UCJrDMFOdv1I2k8n9oK_V21w", "https://youtube.com/channel/UCK1i2UviaXLUNrZlAFpw_jA",
       "https://youtube.com/channel/UCt4t-jeY85JegMlZ-E5UWtA", "https://youtube.com/channel/UC22nIfOTM7KLIQuFGMKzQbg", "https://youtube.com/channel/UC1ciY6kR3yj3kaKZ6R7ewAg", "https://youtube.com/channel/UC3gNmTGu-TTbFPpfSs5kNkg", "https://youtube.com/channel/UCRijo3ddMTht_IHyNSNXpNQ", "https://youtube.com/channel/UC56gTxNs4f9xZ7Pa2i5xNzg", "https://youtube.com/channel/UCbTLwN10NoCU4WDzLf1JMOA", "https://youtube.com/channel/UCqECaJ8Gagnn7YCbPEzWH6g", "https://youtube.com/channel/UCEdvpU2pFRCVqU6yIPyTpMQ", "https://youtube.com/channel/UC4NALVCmcmL5ntpV0thoH6w", "https://youtube.com/channel/UCRx3mKNUdl8QE06nEug7p6Q", "https://youtube.com/channel/UCgFXm4TI8htWmCyJ6cVPG_A", "https://youtube.com/channel/UC0C-w0YjGpqDXGB8IHb662A", "https://youtube.com/channel/UCrnQFuUabBHaw-BRhPo8xEA", "https://youtube.com/channel/UC2tsySbe9TNrI-xh2lximHA", "https://youtube.com/channel/UCF1JIbMUs6uqoZEY1Haw0GQ", "https://youtube.com/channel/UCe9JSDmyqNgA_l2BzGHq1Ug", "https://youtube.com/channel/UC4JCksJF76g_MdzPVBJoC3Q", "https://youtube.com/channel/UClZkHt2kNIgyrTTPnSQV3SA", "https://youtube.com/channel/UCYiGq8XF7YQD00x7wAd62Zg", "https://youtube.com/channel/UCY1kMZp36IQSyNx_9h4mpCg", "https://youtube.com/channel/UCiGm_E4ZwYSHV3bcW1pnSeQ", "https://youtube.com/channel/UCqJ5zFEED1hWs0KNQCQuYdQ", "https://youtube.com/channel/UCvh1at6xpV1ytYOAzxmqUsA", "https://youtube.com/channel/UCOnIJiQuk1fDSp6p1GCZy3A",
       "https://youtube.com/channel/UCRv76wLBC73jiP7LX4C3l8Q", "https://youtube.com/channel/UCu59yAFE8fM0sVNTipR4edw", "https://youtube.com/channel/UCJg19noZp7-BYIGvypu_cow", "https://youtube.com/channel/UCYWOjHweP2V-8kGKmmAmQJQ", "https://youtube.com/channel/UCstEtN0pgOmCf02EdXsGChw", "https://youtube.com/channel/UC6gVx_vALsYT-z_u1djJbBQ", "https://youtube.com/channel/UCV306eHqgo0LvBf3Mh36AHg", "https://youtube.com/channel/UCYLNGLIzMhRTi6ZOLjAPSmw", "https://youtube.com/channel/UCL5nlHWXVLeOsSjKH2fhmsg", "https://youtube.com/channel/UCoQm-PeHC-cbJclKJYJ8LzA", "https://youtube.com/channel/UCj0O6W8yDuLg3iraAXKgCrQ", "https://youtube.com/channel/UCJrOtniJ0-NWz37R30urifQ", "https://youtube.com/channel/UCYvmuw-JtVrTZQ-7Y4kd63Q", "https://youtube.com/channel/UC4tS4Q_Cno5JVcIUXxQOOpA", "https://youtube.com/channel/UCWi_65E_L8tQZ34C6wVAlpQ", "https://youtube.com/channel/UC4rlAVgAK0SGk-yTfe48Qpw", "https://youtube.com/channel/UC3KQ5GWANYF8lChqjZpXsQw", "https://youtube.com/channel/UCMgapddJymOC6MBOiOqia1A", "https://youtube.com/channel/UCOsyDsO5tIt-VZ1iwjdQmew", "https://youtube.com/channel/UCQ7x25F6YXY9DvGeHFxLhRQ", "https://youtube.com/channel/UC0Wju2yvRlfwqraLlz5152Q", "https://youtube.com/channel/UCbp9MyKCTEww4CxEzc_Tp0Q", "https://youtube.com/channel/UCS94J1s6-qc8v7btCdS2pNg", "https://youtube.com/channel/UC_gV70G_Y51LTa3qhu8KiEA", "https://youtube.com/channel/UCECJDeK0MNapZbpaOzxrUPA",
       "https://youtube.com/channel/UCwHE1kM1CPJd_pI9FQ0-4dg", "https://youtube.com/channel/UC5gxP-2QqIh_09djvlm9Xcg", "https://youtube.com/channel/UCw7xjxzbMwgBSmbeYwqYRMg", "https://youtube.com/channel/UCRWFSbif-RFENbBrSiez1DA", "https://youtube.com/channel/UCLsooMJoIpl_7ux2jvdPB-Q", "https://youtube.com/channel/UCtW7qWjpCZ8zps-Cf2NF26w", "https://youtube.com/channel/UC-LPIU24bQXVljUXivKEeRQ", "https://youtube.com/channel/UCKe6w0exI94U-RzqAyoY1VA", "https://youtube.com/channel/UC5c9VlYTSvBSCaoMu_GI6gQ", "https://youtube.com/channel/UCKAqou7V9FAWXpZd9xtOg3Q", "https://youtube.com/channel/UCsSsgPaZ2GSmO6il8Cb5iGA", "https://youtube.com/channel/UCaHEdZtk6k7SVP-umnzifmQ", "https://youtube.com/channel/UC3ZkCd7XtUREnjjt3cyY_gg", "https://youtube.com/channel/UCsT0YIqwnpJCM-mx7-gSA4Q", "https://youtube.com/channel/UCNUQK9mQoqi4yNXw2_Rj6SA", "https://youtube.com/channel/UC_A7K2dXFsTMAciGmnNxy-Q", "https://youtube.com/channel/UCcOMTVILq-yIqtFmOqt-QOg", "https://youtube.com/channel/UCK5Q72Uyo73uRPk8PmM2A3w", "https://youtube.com/channel/UCj-SWZSE0AmotGSQ3apROHw", "https://youtube.com/channel/UCpEJRZdSpdVZ8vh63T9I2KQ", "https://youtube.com/channel/UC8f7MkX4MFOOJ2SerXLInCA", "https://youtube.com/channel/UCRm96I5kmb_iGFofE5N691w", "https://youtube.com/channel/UCttspZesZIDEwwpVIgoZtWQ", "https://youtube.com/channel/UCo6y9hnRawAqtyWhRhblXqg", "https://youtube.com/channel/UCX8pnu3DYUnx8qy8V_c6oHg"]


is_live = {
    ch.replace("https://youtube.com/channel/", ""): False for ch in chs
}

output = '~/Downloads/ss.ts'

streamlink = Streamlink(options={
    # 'm3u8-proxy': 'https://spmi81gcgo:k6h5guq~wn8WmAjB7O@gate.smartproxy.com:10001',
    'ffmpeg-start-at-zero': True,
})

chs = ['https://www.youtube.com/watch?v=UaRbN00A5yw', ]
stream_name = '720p'

for ch in chs:
    url = ch

    try:
        pluginname, pluginclass, resolved_url = streamlink.resolve_url(url)
    except NoPluginError:
        continue
    plugin = pluginclass(streamlink, resolved_url)
    print(f"Found matching plugin {pluginname} for URL {url}")
    # import logging
    # for name in logging.root.manager.loggerDict:
    #     if 'streamlink' in name:
    #         logging.getLogger(name).setLevel(logging.DEBUG)

    streams = plugin.streams()
    # print(f'Streams keys: {",".join(streams.keys())}')
    print(f'id: {plugin.id}, author: {plugin.author}, category: {plugin.category}, title: {plugin.title}, is_live: {plugin.is_live}, latency_class: {plugin.latency_class if pluginname == "youtube" else None}, broadcast_start_time: {plugin.broadcast_start_time}')

    validstreams = format_valid_streams(plugin, streams)
    print(f"Available streams: {validstreams}")

    if stream_name in streams:
        handle_stream(plugin, streams, stream_name, output)

# for i in range(100):
#     res = requests.get('https://manifest.googlevideo.com/api/manifest/hls_playlist/expire/1714673148/ei/nIEzZo63NsTYs8IP4ayT4A0/ip/52.78.145.156/id/M57EY2CQ--0.1/itag/300/source/yt_live_broadcast/requiressl/yes/ratebypass/yes/live/1/sgoap/gir%3Dyes%3Bitag%3D140/sgovp/gir%3Dyes%3Bitag%3D298/rqh/1/hdlc/1/hls_chunk_host/rr4---sn-oguelnlz.googlevideo.com/xpc/EgVo2aDSNQ%3D%3D/spc/UWF9fyBBFv-h0DZROYbn6awVBRFRoxet0cui18WamMT3XT_B1cOqqsjpYQ7y/vprv/1/playlist_type/LIVE/hcs/ir/initcwndbps/41250/mh/S3/mm/44/mn/sn-oguelnlz/ms/lva/mv/m/mvi/4/pl/20/dover/11/pacing/0/keepalive/yes/mt/1714651228/sparams/expire,ei,ip,id,itag,source,requiressl,ratebypass,live,sgoap,sgovp,rqh,hdlc,xpc,spc,vprv,playlist_type/sig/AJfQdSswRgIhALpK6PyU_8HOwzR5UQKqqAFt7wX7gC4Cy9JurnkGvl1IAiEA100eo0uGYbibTtD4u4hiraBR30mMjd9_rI15XceXu-A%3D/lsparams/hls_chunk_host,hcs,initcwndbps,mh,mm,mn,ms,mv,mvi,pl/lsig/AHWaYeowRgIhAOQEV9CI9lvItzPOs_CDk221YCvvLXvLlJ4IIxbxop25AiEA-fKJphtK_TCuCP7oa-bNJg60M1tNdtwM9jbEEdkbYTk%3D/playlist/index.m3u8')
#     print(res.status_code)

# res = requests.get("https://checkip.amazonaws.com", proxies={'https': 'https://spmi81gcgo:k6h5guq~wn8WmAjB7O@gate.smartproxy.com:10001',
#                    'http': 'https://spmi81gcgo:k6h5guq~wn8WmAjB7O@gate.smartproxy.com:10001'})
# print('asdf'+res.content.decode('utf-8').strip()+'asdf')

# stream.set_option('ffmpeg-verbose', True)
