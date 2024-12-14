from __future__ import annotations

import copy
import itertools
import logging
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager, suppress
from datetime import datetime
from time import time
from typing import Any

from requests import Response

from streamlink.exceptions import PluginError, StreamError
from streamlink.session import Streamlink
from streamlink.stream.dash.manifest import MPD, Representation, freeze_timeline
from streamlink.stream.dash.segment import DASHSegment
from streamlink.stream.ffmpegmux import FFMPEGMuxer
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.stream.stream import Stream
from streamlink.utils.l10n import Language
from streamlink.utils.parse import parse_xml
from streamlink.utils.times import now


log = logging.getLogger(".".join(__name__.split(".")[:-1]))


class DASHStreamWriter(SegmentedStreamWriter[DASHSegment, Response]):
    reader: DASHStreamReader
    stream: DASHStream

    def fetch(self, segment: DASHSegment):
        if self.closed:
            return

        name = segment.name
        available_in = segment.available_in
        if available_in > 0:
            log.debug(f"{self.reader.mime_type} segment {name}: waiting {available_in:.01f}s ({segment.availability})")
            if not self.wait(available_in):
                log.debug(f"{self.reader.mime_type} segment {name}: cancelled")
                return
        log.debug(f"{self.reader.mime_type} segment {name}: downloading ({segment.availability})")

        request_args = copy.deepcopy(self.reader.stream.args)
        headers = request_args.pop("headers", {})

        if segment.byterange:
            start, length = segment.byterange
            end = str(start + length - 1) if length else ""
            headers["Range"] = f"bytes={start}-{end}"

        try:
            return self.session.http.get(
                segment.uri,
                timeout=self.timeout,
                exception=StreamError,
                headers=headers,
                retries=self.retries,
                **request_args,
            )
        except StreamError as err:
            log.error(f"{self.reader.mime_type} segment {name}: failed ({err})")

    def write(self, segment, res, chunk_size=8192):
        for chunk in res.iter_content(chunk_size):
            if self.closed:
                log.warning(f"{self.reader.mime_type} segment {segment.name}: aborted")
                return
            self.reader.buffer.write(chunk)

        log.debug(f"{self.reader.mime_type} segment {segment.name}: completed")


class DASHStreamWorker(SegmentedStreamWorker[DASHSegment, Response]):
    reader: DASHStreamReader
    writer: DASHStreamWriter
    stream: DASHStream

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mpd = self.stream.mpd

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

    def iter_segments(self):
        init = True
        back_off_factor = 1
        while not self.closed:
            # find the representation by ID
            representation = self.mpd.get_representation(self.reader.ident)

            if self.mpd.type == "static":
                refresh_wait = 5
            else:
                refresh_wait = (
                    max(
                        self.mpd.minimumUpdatePeriod.total_seconds(),
                        representation.period.duration.total_seconds() if representation else 0,
                    )
                    or 5
                )

            with self.sleeper(refresh_wait * back_off_factor):
                if not representation:
                    continue

                iter_segments = representation.segments(
                    init=init,
                    # sync initial timeline generation between audio and video threads
                    timestamp=self.reader.timestamp if init else None,
                )
                for segment in iter_segments:
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

        new_rep = new_mpd.get_representation(self.reader.ident)
        with freeze_timeline(new_mpd):
            changed = len(list(itertools.islice(new_rep.segments(), 1))) > 0

        if changed:
            self.mpd = new_mpd

        return changed


class DASHStreamReader(SegmentedStreamReader[DASHSegment, Response]):
    __worker__ = DASHStreamWorker
    __writer__ = DASHStreamWriter

    worker: DASHStreamWorker
    writer: DASHStreamWriter
    stream: DASHStream

    def __init__(
        self,
        stream: DASHStream,
        representation: Representation,
        timestamp: datetime,
    ):
        super().__init__(stream)
        self.ident = representation.ident
        self.mime_type = representation.mimeType
        self.timestamp = timestamp


class DASHStream(Stream):
    """
    Implementation of the "Dynamic Adaptive Streaming over HTTP" protocol (MPEG-DASH)
    """

    __shortname__ = "dash"

    def __init__(
        self,
        session: Streamlink,
        mpd: MPD,
        video_representation: Representation | None = None,
        audio_representation: Representation | None = None,
        **kwargs,
    ):
        """
        :param session: Streamlink session instance
        :param mpd: Parsed MPD manifest
        :param video_representation: Video representation
        :param audio_representation: Audio representation
        :param kwargs: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session)
        self.mpd = mpd
        self.video_representation = video_representation
        self.audio_representation = audio_representation
        self.args = session.http.valid_request_args(**kwargs)

    def __json__(self):  # noqa: PLW3201
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

    @staticmethod
    def fetch_manifest(session: Streamlink, url_or_manifest: str, **request_args) -> tuple[str, dict[str, Any]]:
        if url_or_manifest.startswith("<?xml"):
            return url_or_manifest, {}

        retries = session.options.get("dash-manifest-reload-attempts")
        args = session.http.valid_request_args(**request_args)
        res = session.http.get(url_or_manifest, retries=retries, **args)
        manifest: str = res.text
        url: str = res.url

        return manifest, dict(url=url, base_url=url)

    @staticmethod
    def parse_mpd(manifest: str, mpd_params: Mapping[str, Any]) -> MPD:
        node = parse_xml(manifest, ignore_ns=True)

        return MPD(node, **mpd_params)

    @classmethod
    def parse_manifest(
        cls,
        session: Streamlink,
        url_or_manifest: str,
        period: int = 0,
        with_video_only: bool = False,
        with_audio_only: bool = False,
        **kwargs,
    ) -> dict[str, DASHStream]:
        """
        Parse a DASH manifest file and return its streams.

        :param session: Streamlink session instance
        :param url_or_manifest: URL of the manifest file or an XML manifest string
        :param period: Which MPD period to use (index number) for finding representations
        :param with_video_only: Also return video-only streams, otherwise only return muxed streams
        :param with_audio_only: Also return audio-only streams, otherwise only return muxed streams
        :param kwargs: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        manifest, mpd_params = cls.fetch_manifest(session, url_or_manifest, **kwargs)

        try:
            mpd = cls.parse_mpd(manifest, mpd_params)
        except Exception as err:
            raise PluginError(f"Failed to parse MPD manifest: {err}") from err

        source = mpd_params.get("url", "MPD manifest")
        video: list[Representation | None] = [None] if with_audio_only else []
        audio: list[Representation | None] = [None] if with_video_only else []

        # Search for suitable video and audio representations
        for aset in mpd.periods[period].adaptationSets:
            if aset.contentProtections:
                raise PluginError(f"{source} is protected by DRM")
            for rep in aset.representations:
                if rep.contentProtections:
                    raise PluginError(f"{source} is protected by DRM")
                if rep.mimeType.startswith("video"):
                    video.append(rep)
                elif rep.mimeType.startswith("audio"):  # pragma: no branch
                    audio.append(rep)

        if not video:
            video.append(None)
        if not audio:
            audio.append(None)

        locale = session.localization
        locale_lang = locale.language
        lang = None
        available_languages = set()

        # if the locale is explicitly set, prefer that language over others
        for aud in audio:
            if aud and aud.lang:
                available_languages.add(aud.lang)
                with suppress(LookupError):
                    if locale.explicit and aud.lang and Language.get(aud.lang) == locale_lang:
                        lang = aud.lang

        if not lang:
            # filter by the first language that appears
            lang = audio[0].lang if audio[0] else None

        log.debug(
            f"Available languages for DASH audio streams: {', '.join(available_languages) or 'NONE'} (using: {lang or 'n/a'})",
        )

        # if the language is given by the stream, filter out other languages that do not match
        if len(available_languages) > 1:
            audio = [a for a in audio if a and (a.lang is None or a.lang == lang)]

        ret = []
        for vid, aud in itertools.product(video, audio):
            if not vid and not aud:
                continue

            stream = DASHStream(session, mpd, vid, aud, **kwargs)
            stream_name = []

            if vid:
                stream_name.append(f"{vid.height or vid.bandwidth_rounded:0.0f}{'p' if vid.height else 'k'}")
            if aud and len(audio) > 1:
                stream_name.append(f"a{aud.bandwidth:0.0f}k")
            ret.append(("+".join(stream_name), stream))

        # rename duplicate streams
        dict_value_list = defaultdict(list)
        for k, v in ret:
            dict_value_list[k].append(v)

        def sortby_bandwidth(dash_stream: DASHStream) -> float:
            if dash_stream.video_representation:
                return dash_stream.video_representation.bandwidth
            if dash_stream.audio_representation:
                return dash_stream.audio_representation.bandwidth
            return 0  # pragma: no cover

        ret_new = {}
        for q in dict_value_list:
            items = dict_value_list[q]

            with suppress(AttributeError):
                items = sorted(items, key=sortby_bandwidth, reverse=True)

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

        timestamp = now()

        if rep_video:
            video = DASHStreamReader(self, rep_video, timestamp)
            log.debug(f"Opening DASH reader for: {rep_video.ident!r} - {rep_video.mimeType}")

        if rep_audio:
            audio = DASHStreamReader(self, rep_audio, timestamp)
            log.debug(f"Opening DASH reader for: {rep_audio.ident!r} - {rep_audio.mimeType}")

        if video and audio and FFMPEGMuxer.is_usable(self.session):
            video.open()
            audio.open()
            return FFMPEGMuxer(self.session, video, audio, copyts=True).open()
        elif video:
            video.open()
            return video
        elif audio:
            audio.open()
            return audio
