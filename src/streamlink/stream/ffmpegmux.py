import os
import random
import threading

import subprocess

import sys
from streamlink.packages import pbs
from streamlink.packages.pbs import CommandNotFound
from streamlink.stream import Stream
from streamlink_cli.utils import NamedPipe
try:
    from subprocess import DEVNULL
    devnull = lambda: DEVNULL
except ImportError:
    devnull = lambda: open(os.path.devnull, 'w')


class MuxedStream(Stream):
    __shortname__ = "muxed-stream"

    def __init__(self, session, *substreams, **options):
        super(MuxedStream, self).__init__(session)
        self.substreams = substreams
        self.options = options

    def open(self):
        fds = []
        for substream in self.substreams:
            fds.append(substream.open())
        return FFMPEGMuxer(self.session, *fds, **self.options).open()

    @classmethod
    def is_usable(cls, session):
        return FFMPEGMuxer.is_usable(session)


class FFMPEGMuxer(object):
    __commands__ = ['ffmpeg', 'avconv']

    @staticmethod
    def copy_to_pipe(self, stream, pipe):
        self.logger.debug("Starting copy to pipe: {}".format(pipe.path))
        pipe.open("wb")
        while not stream.closed:
            try:
                data = stream.read(8192)
                if len(data):
                    pipe.write(data)
                else:
                    break
            except IOError:
                self.logger.error("Pipe copy aborted: {}".format(pipe.path))
                return
        try:
            pipe.close()
        except IOError:  # might fail closing, but that should be ok for the pipe
            pass
        self.logger.debug("Pipe copy complete: {}".format(pipe.path))

    def __init__(self, session, *streams, **options):
        if not self.is_usable(session):
            raise Exception("cannot use FFMPEG")

        self.session = session
        self.process = None
        self.logger = session.logger.new_module("stream.mp4mux-ffmpeg")
        self.streams = streams
        self.pipes = [NamedPipe("foo-{}-{}".format(os.getpid(), random.randint(0, 1000))) for _ in streams]
        self.pipe_threads = [threading.Thread(target=self.copy_to_pipe, args=(self, stream, np))
                             for stream, np in
                             zip(streams, self.pipes)]

        ofmt = options.pop("format", "matroska")
        outpath = options.pop("outpath", "pipe:1")
        videocodec = session.options.get("ffmpeg-video-transcode") or options.pop("vcodec", "copy")
        audiocodec = session.options.get("ffmpeg-audio-transcode") or options.pop("acodec", "copy")

        self._cmd = [self.command(session), '-nostats', '-y']
        for np in self.pipes:
            self._cmd.extend(["-i", np.path])

        self._cmd.extend(['-c:v', videocodec, '-c:a', audiocodec, '-f', ofmt, outpath])
        self.logger.debug("ffmpeg command: {}".format(' '.join(self._cmd)))
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
        self.process = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stderr=self.errorlog)

        return self

    @classmethod
    def is_usable(cls, session):
        return cls.command(session) is not None

    @classmethod
    def command(cls, session):
        command = [session.options.get("ffmpeg-ffmpeg")]
        for cmd in command or cls.__commands__:
            try:
                pbs.create_command(cmd)
                return cmd
            except CommandNotFound:
                continue

    def read(self, size=-1):
        data = self.process.stdout.read(size)
        return data

    def close(self):
        self.logger.debug("Closing ffmpeg thread")
        if self.process:
            # kill ffmpeg
            self.process.kill()
            self.process.stdout.close()

            # close the streams
            for stream in self.streams:
                if hasattr(stream, "close"):
                    stream.close()

            self.logger.debug("Closed all the substreams")
        if self.close_errorlog:
            self.errorlog.close()
            self.errorlog = None
