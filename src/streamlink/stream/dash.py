import copy
import datetime
import itertools
import logging
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from time import time
from typing import Dict, Optional
from urllib.parse import urlparse, urlunparse

from streamlink import PluginError, StreamError
from streamlink.stream.dash_manifest import MPD, Representation, Segment, freeze_timeline
from streamlink.stream.ffmpegmux import FFMPEGMuxer
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.stream.stream import Stream
from streamlink.utils.l10n import Language
from streamlink.utils.parse import parse_xml


log = logging.getLogger(__name__)

UTC = datetime.timezone.utc


class DASHStreamWriter(SegmentedStreamWriter):
    reader: "DASHStreamReader"
    stream: "DASHStream"

    @staticmethod
    def _get_segment_name(segment: Segment) -> str:
        return Path(urlparse(segment.url).path).resolve().name

    def fetch(self, segment: Segment, retries: Optional[int] = None):
        if self.closed or not retries:
            return

        try:
            request_args = copy.deepcopy(self.reader.stream.args)
            headers = request_args.pop("headers", {})
            now = datetime.datetime.now(tz=UTC)
            if segment.available_at > now:
                time_to_wait = (segment.available_at - now).total_seconds()
                fname = self._get_segment_name(segment)
                log.debug(f"Waiting for {self.reader.mime_type} segment: {fname} ({time_to_wait:.01f}s)")
                if not self.wait(time_to_wait):
                    log.debug(f"Waiting for {self.reader.mime_type} segment: {fname} aborted")
                    return

            if segment.byterange:
                start, length = segment.byterange
                end = str(start + length - 1) if length else ""
                headers["Range"] = f"bytes={start}-{end}"

            return self.session.http.get(
                segment.url,
                timeout=self.timeout,
                exception=StreamError,
                headers=headers,
                **request_args,
            )
        except StreamError as err:
            log.error(f"Failed to open {self.reader.mime_type} segment {segment.url}: {err}")
            return self.fetch(segment, retries - 1)

    def write(self, segment, res, chunk_size=8192):
        name = self._get_segment_name(segment)
        for chunk in res.iter_content(chunk_size):
            if self.closed:
                log.warning(f"Download of {self.reader.mime_type} segment: {name} aborted")
                return
            self.reader.buffer.write(chunk)

        log.debug(f"Download of {self.reader.mime_type} segment: {name} complete")


class DASHStreamWorker(SegmentedStreamWorker):
    reader: "DASHStreamReader"
    writer: "DASHStreamWriter"
    stream: "DASHStream"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mpd = self.stream.mpd
        self.period = self.stream.period

        self.manifest_reload_retries = self.session.options.get("dash-manifest-reload-attempts")

    @contextmanager
    def sleeper(self, duration):
        """
        Do something and then wait for a given duration minus the time it took doing something
        """
        s = time()
        yield
        time_to_sleep = duration - (time() - s)
        if time_to_sleep > 0:
            self.wait(time_to_sleep)

    def get_representation(self, mpd, ident):
        for aset in mpd.periods[self.period].adaptationSets:
            for rep in aset.representations:
                if rep.ident == ident:
                    return rep

    def iter_segments(self):
        init = True
        back_off_factor = 1
        while not self.closed:
            # find the representation by ID
            representation = self.get_representation(self.mpd, self.reader.ident)

            if self.mpd.type == "static":
                refresh_wait = 5
            else:
                refresh_wait = max(
                    self.mpd.minimumUpdatePeriod.total_seconds(),
                    self.mpd.periods[self.period].duration.total_seconds(),
                ) or 5

            with self.sleeper(refresh_wait * back_off_factor):
                if not representation:
                    continue

                for segment in representation.segments(init=init):
                    if self.closed:
                        break
                    yield segment

                # close worker if type is not dynamic (all segments were put into writer queue)
                if self.mpd.type != "dynamic":
                    self.close()
                    return

                if not self.reload():
                    back_off_factor = max(back_off_factor * 1.3, 10.0)
                else:
                    back_off_factor = 1

                init = False

    def reload(self):
        if self.closed:
            return

        self.reader.buffer.wait_free()
        log.debug(f"Reloading manifest {self.reader.ident!r}")
        res = self.session.http.get(
            self.mpd.url,
            exception=StreamError,
            retries=self.manifest_reload_retries,
            **self.stream.args,
        )

        new_mpd = MPD(
            self.session.http.xml(res, ignore_ns=True),
            base_url=self.mpd.base_url,
            url=self.mpd.url,
            timelines=self.mpd.timelines,
        )

        new_rep = self.get_representation(new_mpd, self.reader.ident)
        with freeze_timeline(new_mpd):
            changed = len(list(itertools.islice(new_rep.segments(), 1))) > 0

        if changed:
            self.mpd = new_mpd

        return changed


class DASHStreamReader(SegmentedStreamReader):
    __worker__ = DASHStreamWorker
    __writer__ = DASHStreamWriter

    worker: "DASHStreamWorker"
    writer: "DASHStreamWriter"
    stream: "DASHStream"

    def __init__(self, stream: "DASHStream", representation: Representation, *args, **kwargs):
        super().__init__(stream, *args, **kwargs)
        self.ident = representation.ident
        self.mime_type = representation.mimeType


class DASHStream(Stream):
    """
    Implementation of the "Dynamic Adaptive Streaming over HTTP" protocol (MPEG-DASH)
    """

    __shortname__ = "dash"

    def __init__(
        self,
        session,
        mpd: MPD,
        video_representation: Optional[Representation] = None,
        audio_representation: Optional[Representation] = None,
        period: float = 0,
        **args,
    ):
        """
        :param streamlink.Streamlink session: Streamlink session instance
        :param mpd: Parsed MPD manifest
        :param video_representation: Video representation
        :param audio_representation: Audio representation
        :param period: Update period
        :param args: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session)
        self.mpd = mpd
        self.video_representation = video_representation
        self.audio_representation = audio_representation
        self.period = period
        self.args = args

    def __json__(self):
        json = dict(type=self.shortname())

        if self.mpd.url:
            args = self.args.copy()
            args.update(url=self.mpd.url)
            req = self.session.http.prepare_new_request(**args)
            json.update(
                # the MPD URL has already been prepared by the initial request in `parse_manifest`
                url=self.mpd.url,
                headers=dict(req.headers),
            )

        return json

    def to_url(self):
        if self.mpd.url is None:
            return super().to_url()

        # the MPD URL has already been prepared by the initial request in `parse_manifest`
        return self.mpd.url

    @classmethod
    def parse_manifest(
        cls,
        session,
        url_or_manifest: str,
        **args,
    ) -> Dict[str, "DASHStream"]:
        """
        Parse a DASH manifest file and return its streams.

        :param streamlink.Streamlink session: Streamlink session instance
        :param url_or_manifest: URL of the manifest file or an XML manifest string
        :param args: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        if url_or_manifest.startswith("<?xml"):
            mpd = MPD(parse_xml(url_or_manifest, ignore_ns=True))
        else:
            retries = session.options.get("dash-manifest-reload-attempts")
            res = session.http.get(
                url_or_manifest,
                retries=retries,
                **session.http.valid_request_args(**args),
            )
            url = res.url

            urlp = list(urlparse(url))
            urlp[2], _ = urlp[2].rsplit("/", 1)

            mpd = MPD(session.http.xml(res, ignore_ns=True), base_url=urlunparse(urlp), url=url)

        video, audio = [], []

        # Search for suitable video and audio representations
        for aset in mpd.periods[0].adaptationSets:
            if aset.contentProtection:
                raise PluginError(f"{url} is protected by DRM")
            for rep in aset.representations:
                if rep.contentProtection:
                    raise PluginError(f"{url} is protected by DRM")
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

        log.debug("Available languages for DASH audio streams: {0} (using: {1})".format(
            ", ".join(available_languages) or "NONE",
            lang or "n/a",
        ))

        # if the language is given by the stream, filter out other languages that do not match
        if len(available_languages) > 1:
            audio = list(filter(lambda a: a.lang is None or a.lang == lang, audio))

        ret = []
        for vid, aud in itertools.product(video, audio):
            stream = DASHStream(session, mpd, vid, aud, **args)
            stream_name = []

            if vid:
                stream_name.append("{:0.0f}{}".format(vid.height or vid.bandwidth_rounded, "p" if vid.height else "k"))
            if audio and len(audio) > 1:
                stream_name.append("a{:0.0f}k".format(aud.bandwidth))
            ret.append(("+".join(stream_name), stream))

        # rename duplicate streams
        dict_value_list = defaultdict(list)
        for k, v in ret:
            dict_value_list[k].append(v)

        def sortby_bandwidth(dash_stream: DASHStream) -> int:
            if dash_stream.video_representation:
                return dash_stream.video_representation.bandwidth
            if dash_stream.audio_representation:
                return dash_stream.audio_representation.bandwidth
            return 0  # pragma: no cover

        ret_new = {}
        for q in dict_value_list:
            items = dict_value_list[q]

            try:
                items = sorted(items, key=sortby_bandwidth, reverse=True)
            except AttributeError:
                pass

            for n in range(len(items)):
                if n == 0:
                    ret_new[q] = items[n]
                elif n == 1:
                    ret_new[f"{q}_alt"] = items[n]
                else:
                    ret_new[f"{q}_alt{n}"] = items[n]
        return ret_new

    def open(self):
        video, audio = None, None
        rep_video, rep_audio = self.video_representation, self.audio_representation

        if rep_video:
            video = DASHStreamReader(self, rep_video)
            log.debug(f"Opening DASH reader for: {rep_video.ident!r} - {rep_video.mimeType}")
            video.open()

        if rep_audio:
            audio = DASHStreamReader(self, rep_audio)
            log.debug(f"Opening DASH reader for: {rep_audio.ident!r} - {rep_audio.mimeType}")
            audio.open()

        if video and audio:
            return FFMPEGMuxer(self.session, video, audio, copyts=True).open()
        elif video:
            return video
        elif audio:
            return audio
