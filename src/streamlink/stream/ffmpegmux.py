import os
import random
import threading

import subprocess

import sys

from streamlink import StreamError
from streamlink.stream import Stream
from streamlink.stream.stream import StreamIO
from streamlink.utils import NamedPipe
from streamlink.compat import devnull, which
import logging

log = logging.getLogger(__name__)


class MuxedStream(Stream):
    __shortname__ = "muxed-stream"

    def __init__(self, session, *substreams, **options):
        super(MuxedStream, self).__init__(session)
        self.substreams = substreams
        self.subtitles = options.pop("subtitles", {})
        self.options = options

    def open(self):
        fds = []
        metadata = self.options.get("metadata", {})
        maps = self.options.get("maps", [])
        # only update the maps values if they haven't been set
        update_maps = not maps
        for i, substream in enumerate(self.substreams):
            log.debug("Opening {0} substream".format(substream.shortname()))
            if update_maps:
                maps.append(len(fds))
            fds.append(substream and substream.open())

        for i, subtitle in enumerate(self.subtitles.items()):
            language, substream = subtitle
            log.debug("Opening {0} subtitle stream".format(substream.shortname()))
            if update_maps:
                maps.append(len(fds))
            fds.append(substream and substream.open())
            metadata["s:s:{0}".format(i)] = ["language={0}".format(language)]

        self.options["metadata"] = metadata
        self.options["maps"] = maps

        return FFMPEGMuxer(self.session, *fds, **self.options).open()

    @classmethod
    def is_usable(cls, session):
        return FFMPEGMuxer.is_usable(session)


class FFMPEGMuxer(StreamIO):
    __commands__ = ['ffmpeg', 'ffmpeg.exe', 'avconv', 'avconv.exe']

    @staticmethod
    def copy_to_pipe(self, stream, pipe):
        log.debug("Starting copy to pipe: {0}".format(pipe.path))
        pipe.open("wb")
        while not stream.closed:
            try:
                data = stream.read(8192)
                if len(data):
                    pipe.write(data)
                else:
                    break
            except IOError:
                log.error("Pipe copy aborted: {0}".format(pipe.path))
                return
        try:
            pipe.close()
        except IOError:  # might fail closing, but that should be ok for the pipe
            pass
        log.debug("Pipe copy complete: {0}".format(pipe.path))

    def __init__(self, session, *streams, **options):
        if not self.is_usable(session):
            raise StreamError("cannot use FFMPEG")

        self.session = session
        self.process = None
        log = logging.getLogger("streamlink.stream.mp4mux-ffmpeg")
        self.streams = streams

        self.pipes = [NamedPipe("ffmpeg-{0}-{1}".format(os.getpid(), random.randint(0, 1000))) for _ in self.streams]
        self.pipe_threads = [threading.Thread(target=self.copy_to_pipe, args=(self, stream, np))
                             for stream, np in
                             zip(self.streams, self.pipes)]

        ofmt = options.pop("format", "matroska")
        outpath = options.pop("outpath", "pipe:1")
        videocodec = session.options.get("ffmpeg-video-transcode") or options.pop("vcodec", "copy")
        audiocodec = session.options.get("ffmpeg-audio-transcode") or options.pop("acodec", "copy")
        metadata = options.pop("metadata", {})
        maps = options.pop("maps", [])
        copyts = options.pop("copyts", False)

        self._cmd = [self.command(session), '-nostats', '-y']
        for np in self.pipes:
            self._cmd.extend(["-i", np.path])

        self._cmd.extend(['-c:v', videocodec])
        self._cmd.extend(['-c:a', audiocodec])

        for m in maps:
            self._cmd.extend(["-map", str(m)])

        if copyts:
            self._cmd.extend(["-copyts"])

        for stream, data in metadata.items():
            for datum in data:
                self._cmd.extend(["-metadata:{0}".format(stream), datum])

        self._cmd.extend(['-f', ofmt, outpath])
        log.debug("ffmpeg command: {0}".format(' '.join(self._cmd)))
        self.close_errorlog = False

        if session.options.get("ffmpeg-verbose"):
            self.errorlog = sys.stderr
        elif session.options.get("ffmpeg-verbose-path"):
            self.errorlog = open(session.options.get("ffmpeg-verbose-path"), "w")
            self.close_errorlog = True
        else:
            self.errorlog = devnull()

    def open(self):
        for t in self.pipe_threads:
            t.daemon = True
            t.start()
        self.process = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=self.errorlog)

        return self

    @classmethod
    def is_usable(cls, session):
        return cls.command(session) is not None

    @classmethod
    def command(cls, session):
        command = []
        if session.options.get("ffmpeg-ffmpeg"):
            command.append(session.options.get("ffmpeg-ffmpeg"))
        for cmd in command or cls.__commands__:
            if which(cmd):
                return cmd

    def read(self, size=-1):
        data = self.process.stdout.read(size)
        return data

    def close(self):
        log.debug("Closing ffmpeg thread")
        if self.process:
            # kill ffmpeg
            self.process.kill()
            self.process.stdout.close()

            # close the streams
            for stream in self.streams:
                if hasattr(stream, "close"):
                    stream.close()

            log.debug("Closed all the substreams")
        if self.close_errorlog:
            self.errorlog.close()
            self.errorlog = None
