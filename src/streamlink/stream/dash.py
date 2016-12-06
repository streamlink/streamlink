import itertools
from streamlink import StreamError
from streamlink.compat import urlparse, urlunparse
from streamlink.plugin.api import http
from streamlink.stream import Stream
from streamlink.stream import StreamIOIterWrapper
from streamlink.stream.dash_manifest import MPD, sleeper
from streamlink.stream.ffmpegmux import FFMPEGMuxer
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter


class DASHStreamWriter(SegmentedStreamWriter):
    def __init__(self, reader, *args, **kwargs):
        options = reader.stream.session.options
        kwargs["retries"] = options.get("dash-segment-attempts")
        kwargs["threads"] = options.get("dash-segment-threads")
        kwargs["timeout"] = options.get("dash-segment-timeout")
        SegmentedStreamWriter.__init__(self, reader, *args, **kwargs)

    def fetch(self, segment, retries=None):
        if self.closed or not retries:
            return

        try:
            return self.session.http.get(segment.url,
                                         stream=True,
                                         timeout=self.timeout,
                                         exception=StreamError)
        except StreamError as err:
            self.logger.error("Failed to open segment {0}: {1}", segment.url, err)
            return self.fetch(segment, retries - 1)

    def write(self, segment, res, chunk_size=8192):
        for chunk in StreamIOIterWrapper(res.iter_content(chunk_size)):
            if not self.closed:
                self.reader.buffer.write(chunk)
            else:
                self.logger.debug("Download of segment: {} aborted".format(segment.url))
                return

        self.logger.debug("Download of segment: {} complete".format(segment.url))


class DASHStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)
        self.mpd = self.stream.mpd
        self.period = self.stream.period

    def iter_segments(self):
        init = True
        while not self.closed:
            # find the representation by ID
            representation = None
            for aset in self.mpd.periods[0].adaptionSets:
                for rep in aset.representations:
                    if rep.id == self.reader.representation_id:
                        representation = rep
            min_wait = self.mpd.minimumUpdatePeriod.total_seconds() if self.mpd.minimumUpdatePeriod else 5
            with sleeper(min_wait):
                if representation:
                    for segment in representation.segments(init=init):
                        if self.closed:
                            break
                        yield segment
                        self.logger.debug("Adding segment {0} to queue", segment.url)

                    if self.mpd.type == "dynamic":
                        self.reload()
                    else:
                        return
                    init = False

    def reload(self):
        if self.closed:
            return

        self.reader.buffer.wait_free()
        self.logger.debug("Reloading manifest")
        res = self.session.http.get(self.mpd.url, exception=StreamError)

        self.mpd = MPD(http.xml(res, ignore_ns=True),
                       base_url=self.mpd.base_url,
                       url=self.mpd.url,
                       timelines=self.mpd.timelines)


class DASHStreamReader(SegmentedStreamReader):
    __worker__ = DASHStreamWorker
    __writer__ = DASHStreamWriter

    def __init__(self, stream, representation_id, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)
        self.logger = stream.session.logger.new_module("stream.dash")
        self.representation_id = representation_id


class DASHStream(Stream):
    __shortname__ = "dash"

    def __init__(self,
                 session,
                 mpd,
                 video_representation,
                 audio_representation=None,
                 period=0):
        super(DASHStream, self).__init__(session)
        self.mpd = mpd
        self.video_representation = video_representation
        self.audio_representation = audio_representation
        self.period = period

    @classmethod
    def parse_manifest(cls, session, url):
        res = http.get(url)

        urlp = list(urlparse(url))
        urlp[2], _ = urlp[2].rsplit("/", 1)

        mpd = MPD(http.xml(res, ignore_ns=True), base_url=urlunparse(urlp), url=url)

        video, audio = [], []

        for aset in mpd.periods[0].adaptionSets:
            for rep in aset.representations:
                if rep.mimeType.startswith("video"):
                    video.append(rep)
                elif rep.mimeType.startswith("audio"):
                    audio.append(rep)

        for vid, aud in itertools.product(video, audio):
            stream = DASHStream(session, mpd, vid, aud)
            vid_name = "{:0.0f}{}".format(vid.height or vid.bandwidth, "p" if vid.height else "k")
            if len(audio) > 1:
                vid_name += "+a{:0.0f}k".format(aud.bandwidth)
            yield vid_name, stream

    def open(self):
        video = DASHStreamReader(self, self.video_representation.id)
        audio = DASHStreamReader(self, self.audio_representation.id)
        video.open()
        audio.open()
        muxer = FFMPEGMuxer(self.session, video, audio).open()
        return muxer
