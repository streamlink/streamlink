#!/usr/bin/env python3
import logging
import sys
import streamlink
import os.path

try:
    import cv2
except ImportError:
    sys.stderr.write("This example requires opencv-python is installed")
    raise

log = logging.getLogger(__name__)
GREEN = (0, 255, 0)


def stream_to_url(url, quality='best'):
    streams = streamlink.streams(url)
    if streams:
        return streams[quality].to_url()
    else:
        raise ValueError("No streams were available")


def detect_faces(cascade, frame, scale_factor=1.1, min_neighbors=5):
    frame_copy = frame.copy()
    frame_gray = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2GRAY)

    faces = cascade.detectMultiScale(frame_gray, scaleFactor=scale_factor, minNeighbors=min_neighbors)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame_copy, (x, y), (x + w, y + h), GREEN, 1)

    return frame_copy


def main(url, quality='best', fps=30.0):
    face_cascade = cv2.CascadeClassifier(os.path.join(cv2.haarcascades, 'haarcascade_frontalface_default.xml'))

    stream_url = stream_to_url(url, quality)
    log.info("Loading stream {0}".format(stream_url))
    cap = cv2.VideoCapture(stream_url)

    frame_time = int((1.0 / fps) * 1000.0)

    while True:
        try:
            ret, frame = cap.read()
            if ret:
                frame_f = detect_faces(face_cascade, frame, scale_factor=1.2)
                cv2.imshow('frame', frame_f)
                if cv2.waitKey(frame_time) & 0xFF == ord('q'):
                    break
            else:
                break
        except KeyboardInterrupt:
            break

    cv2.destroyAllWindows()
    cap.release()


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Face detection on streams via Streamlink")
    parser.add_argument("url", help="Stream to play")
    parser.add_argument("--stream-quality", help="Requested stream quality [default=best]",
                        default="best", dest="quality")
    parser.add_argument("--fps", help="Play back FPS for opencv [default=30]",
                        default=30.0, type=float)

    opts = parser.parse_args()

    main(opts.url, opts.quality, opts.fps)

