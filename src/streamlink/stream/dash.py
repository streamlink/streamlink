import copy
import itertools
import logging
import datetime
import os.path

import requests
from streamlink import StreamError, PluginError
from streamlink.compat import urlparse, urlunparse
from streamlink.stream.http import valid_args, normalize_key
from streamlink.stream.stream import Stream
from streamlink.stream.dash_manifest import MPD, sleeper, sleep_until, utc, freeze_timeline
from streamlink.stream.ffmpegmux import FFMPEGMuxer
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.utils import parse_xml
from streamlink.utils.l10n import Language

log = logging.getLogger(__name__)


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
            request_args = copy.deepcopy(self.reader.stream.args)
            headers = request_args.pop("headers", {})
            now = datetime.datetime.now(tz=utc)
            if segment.available_at > now:
                time_to_wait = (segment.available_at - now).total_seconds()
                fname = os.path.basename(urlparse(segment.url).path)
                log.debug("Waiting for segment: {fname} ({wait:.01f}s)".format(fname=fname, wait=time_to_wait))
                sleep_until(segment.available_at)

            if segment.range:
                start, length = segment.range
                if length:
                    end = start + length - 1
                else:
                    end = ""
                headers["Range"] = "bytes={0}-{1}".format(start, end)

            return self.session.http.get(segment.url,
                                         timeout=self.timeout,
                                         exception=StreamError,
                                         headers=headers,
                                         **request_args)
        except StreamError as err:
            log.error("Failed to open segment {0}: {1}", segment.url, err)
            return self.fetch(segment, retries - 1)

    def write(self, segment, res, chunk_size=8192):
        for chunk in res.iter_content(chunk_size):
            if not self.closed:
                self.reader.buffer.write(chunk)
            else:
                log.warning("Download of segment: {} aborted".format(segment.url))
                return

        log.debug("Download of segment: {} complete".format(segment.url))


class DASHStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)
        self.mpd = self.stream.mpd
        self.period = self.stream.period

    @staticmethod
    def get_representation(mpd, representation_id, mime_type):
        for aset in mpd.periods[0].adaptationSets:
            for rep in aset.representations:
                if rep.id == representation_id and rep.mimeType == mime_type:
                    return rep

    def iter_segments(self):
        init = True
        back_off_factor = 1
        while not self.closed:
            # find the representation by ID
            representation = self.get_representation(self.mpd, self.reader.representation_id, self.reader.mime_type)
            refresh_wait = max(self.mpd.minimumUpdatePeriod.total_seconds(),
                               self.mpd.periods[0].duration.total_seconds()) or 5
            with sleeper(refresh_wait * back_off_factor):
                if representation:
                    for segment in representation.segments(init=init):
                        if self.closed:
                            break
                        yield segment
                        # log.debug("Adding segment {0} to queue", segment.url)

                    if self.mpd.type == "dynamic":
                        if not self.reload():
                            back_off_factor = max(back_off_factor * 1.3, 10.0)
                        else:
                            back_off_factor = 1
                    else:
                        return
                    init = False

    def reload(self):
        if self.closed:
            return

        self.reader.buffer.wait_free()
        log.debug("Reloading manifest ({0}:{1})".format(self.reader.representation_id, self.reader.mime_type))
        res = self.session.http.get(self.mpd.url, exception=StreamError, **self.stream.args)

        new_mpd = MPD(self.session.http.xml(res, ignore_ns=True),
                      base_url=self.mpd.base_url,
                      url=self.mpd.url,
                      timelines=self.mpd.timelines)

        new_rep = self.get_representation(new_mpd, self.reader.representation_id, self.reader.mime_type)
        with freeze_timeline(new_mpd):
            changed = len(list(itertools.islice(new_rep.segments(), 1))) > 0

        if changed:
            self.mpd = new_mpd

        return changed


class DASHStreamReader(SegmentedStreamReader):
    __worker__ = DASHStreamWorker
    __writer__ = DASHStreamWriter

    def __init__(self, stream, representation_id, mime_type, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)
        self.mime_type = mime_type
        self.representation_id = representation_id
        log.debug("Opening DASH reader for: {0} ({1})".format(self.representation_id, self.mime_type))



class DASHStream(Stream):
    __shortname__ = "dash"

    def __init__(self,
                 session,
                 mpd,
                 video_representation=None,
                 audio_representation=None,
                 period=0,
                 **args):
        super(DASHStream, self).__init__(session)
        self.mpd = mpd
        self.video_representation = video_representation
        self.audio_representation = audio_representation
        self.period = period
        self.args = args

    def __json__(self):
        req = requests.Request(method="GET", url=self.mpd.url, **valid_args(self.args))
        req = req.prepare()

        headers = dict(map(normalize_key, req.headers.items()))
        return dict(type=type(self).shortname(), url=req.url, headers=headers)

    @classmethod
    def parse_manifest(cls, session, url_or_manifest, **args):
        """
        Attempt to parse a DASH manifest file and return its streams

        :param session: Streamlink session instance
        :param url_or_manifest: URL of the manifest file or an XML manifest string
        :return: a dict of name -> DASHStream instances
        """
        ret = {}

        if url_or_manifest.startswith('<?xml'):
            mpd = MPD(parse_xml(url_or_manifest, ignore_ns=True))
        else:
            res = session.http.get(url_or_manifest, **args)
            url = res.url

            urlp = list(urlparse(url))
            urlp[2], _ = urlp[2].rsplit("/", 1)

            mpd = MPD(session.http.xml(res, ignore_ns=True), base_url=urlunparse(urlp), url=url)

        video, audio = [], []

        # Search for suitable video and audio representations
        for aset in mpd.periods[0].adaptationSets:
            if aset.contentProtection:
                raise PluginError("{} is protected by DRM".format(url))
            for rep in aset.representations:
                if rep.mimeType.startswith("video"):
                    video.append(rep)
                elif rep.mimeType.startswith("audio"):
                    audio.append(rep)

        if not video:
            video = [None]

        if not audio:
            audio = [None]

        locale = session.localization
        locale_lang = locale.language
        lang = None
        available_languages = set()

        # if the locale is explicitly set, prefer that language over others
        for aud in audio:
            if aud and aud.lang:
                available_languages.add(aud.lang)
                try:
                    if locale.explicit and aud.lang and Language.get(aud.lang) == locale_lang:
                        lang = aud.lang
                except LookupError:
                    continue

        if not lang:
            # filter by the first language that appears
            lang = audio[0] and audio[0].lang

        log.debug("Available languages for DASH audio streams: {0} (using: {1})".format(", ".join(available_languages) or "NONE", lang or "n/a"))

        # if the language is given by the stream, filter out other languages that do not match
        if len(available_languages) > 1:
            audio = list(filter(lambda a: a.lang is None or a.lang == lang, audio))

        for vid, aud in itertools.product(video, audio):
            stream = DASHStream(session, mpd, vid, aud, **args)
            stream_name = []

            if vid:
                stream_name.append("{:0.0f}{}".format(vid.height or vid.bandwidth_rounded, "p" if vid.height else "k"))
            if audio and len(audio) > 1:
                stream_name.append("a{:0.0f}k".format(aud.bandwidth))
            ret['+'.join(stream_name)] = stream
        return ret

    def open(self):
        if self.video_representation:
            video = DASHStreamReader(self, self.video_representation.id, self.video_representation.mimeType)
            video.open()

        if self.audio_representation:
            audio = DASHStreamReader(self, self.audio_representation.id, self.audio_representation.mimeType)
            audio.open()

        if self.video_representation and self.audio_representation:
            return FFMPEGMuxer(self.session, video, audio, copyts=True).open()
        elif self.video_representation:
            return video
        elif self.audio_representation:
            return audio

    def to_url(self):
        return self.mpd.url
