# Przewodnik użycia Streamlink jako modułu Python

## Spis treści

1. [Instalacja](#instalacja)
2. [Podstawowe użycie](#podstawowe-użycie)
3. [Zaawansowane przykłady](#zaawansowane-przykłady)
4. [Konfiguracja sesji](#konfiguracja-sesji)
5. [Obsługa strumieni](#obsługa-strumieni)
6. [Obsługa błędów](#obsługa-błędów)
7. [Tworzenie własnych pluginów](#tworzenie-własnych-pluginów)

## Instalacja

### Instalacja z PyPI (rekomendowana)

```bash
pip install streamlink
```

### Instalacja z repozytorium Git

```bash
git clone https://github.com/streamlink/streamlink.git
cd streamlink
pip install -e .
```

### Instalacja z opcjonalnymi zależnościami

```bash
# Wsparcie dla dodatkowych formatów kompresji
pip install streamlink[decompress]
```

## Podstawowe użycie

### Szybki start - pobieranie strumieni

Najprostszy sposób na pobranie strumieni z URL:

```python
import streamlink

# Pobierz dostępne strumienie z URL
streams = streamlink.streams("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Sprawdź, jakie jakości są dostępne
print("Dostępne strumienie:", list(streams.keys()))
# Wyjście: ['audio_mp4a', '144p', '240p', '360p', '480p', '720p', 'best', 'worst']

# Pobierz strumień w najlepszej jakości
if "best" in streams:
    stream = streams["best"]

    # Otwórz strumień i czytaj dane
    with stream.open() as fd:
        # Czytaj pierwsze 1024 bajty
        data = fd.read(1024)
        print(f"Pobrano {len(data)} bajtów danych")
```

### Zapisywanie strumienia do pliku

```python
import streamlink

# Pobierz strumień
streams = streamlink.streams("https://twitch.tv/channelname")

if "best" in streams:
    stream = streams["best"]

    # Zapisz strumień do pliku
    with stream.open() as fd:
        with open("output.mp4", "wb") as output:
            while True:
                data = fd.read(8192)  # Czytaj w blokach 8KB
                if not data:
                    break
                output.write(data)

    print("Strumień zapisany do output.mp4")
```

### Strumieniowe przetwarzanie danych

```python
import streamlink

streams = streamlink.streams("https://example.com/stream")

if "best" in streams:
    stream = streams["best"]

    # Przetwarzaj dane w czasie rzeczywistym
    with stream.open() as fd:
        total_bytes = 0

        for chunk in iter(lambda: fd.read(8192), b''):
            # Przetwarzaj każdy chunk danych
            total_bytes += len(chunk)
            print(f"Pobrano: {total_bytes / 1024 / 1024:.2f} MB", end='\r')
```

## Zaawansowane przykłady

### Użycie sesji Streamlink

Obiekt `Streamlink` pozwala na lepszą kontrolę nad konfiguracją:

```python
import streamlink

# Utwórz sesję
session = streamlink.Streamlink()

# Ustaw opcje
session.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0 Custom",
    "Referer": "https://example.com"
})

# Ustaw proxy
session.set_option("http-proxy", "http://proxy.example.com:8080")

# Ustaw timeout
session.set_option("http-timeout", 30.0)

# Pobierz strumienie używając skonfigurowanej sesji
streams = session.streams("https://example.com/stream")
```

### Sprawdzanie dostępności pluginu dla URL

```python
import streamlink
from streamlink.exceptions import NoPluginError

session = streamlink.Streamlink()

url = "https://www.youtube.com/watch?v=..."

try:
    # Sprawdź, czy istnieje plugin dla tego URL
    plugin_name, plugin_class, resolved_url = session.resolve_url(url)
    print(f"Znaleziono plugin: {plugin_name}")
    print(f"Rozwiązany URL: {resolved_url}")

    # Teraz możesz pobrać strumienie
    streams = session.streams(url)

except NoPluginError:
    print(f"Brak pluginu dla URL: {url}")
```

### Filtrowanie strumieni po jakości

```python
import streamlink

streams = streamlink.streams("https://example.com/stream")

# Pobierz tylko strumienie video (bez audio-only)
video_streams = {
    name: stream for name, stream in streams.items()
    if not name.startswith('audio_')
}

# Pobierz strumienie o określonej rozdzielczości
hd_streams = {
    name: stream for name, stream in streams.items()
    if name in ['720p', '1080p', '1440p', '2160p']
}

# Wybierz najlepszy dostępny strumień HD
if hd_streams:
    best_hd = hd_streams[max(hd_streams.keys())]
    print(f"Używam strumienia: {max(hd_streams.keys())}")
```

### Obsługa strumieni HLS

```python
import streamlink
from streamlink.stream import HLSStream

streams = streamlink.streams("https://example.com/stream")

if "best" in streams:
    stream = streams["best"]

    # Sprawdź typ strumienia
    if isinstance(stream, HLSStream):
        print("To jest strumień HLS")

        # Otwórz strumień z dodatkowymi parametrami
        with stream.open() as fd:
            # Czytaj dane
            data = fd.read(1024)
```

### Pobieranie metadanych strumienia

```python
import streamlink

session = streamlink.Streamlink()
streams = session.streams("https://example.com/stream")

for name, stream in streams.items():
    print(f"\nStrumień: {name}")
    print(f"  Typ: {type(stream).__name__}")

    # Niektóre strumienie mają dodatkowe atrybuty
    if hasattr(stream, 'url'):
        print(f"  URL: {stream.url}")
```

## Konfiguracja sesji

### Dostępne opcje sesji

```python
import streamlink

session = streamlink.Streamlink()

# Opcje HTTP
session.set_option("http-proxy", "http://proxy:8080")
session.set_option("https-proxy", "https://proxy:8080")
session.set_option("http-cookies", {"cookie_name": "cookie_value"})
session.set_option("http-headers", {"User-Agent": "Custom"})
session.set_option("http-query-params", {"param": "value"})
session.set_option("http-timeout", 20.0)
session.set_option("http-ssl-verify", True)
session.set_option("http-ssl-cert", "/path/to/cert.pem")

# Opcje strumieni
session.set_option("stream-timeout", 60.0)
session.set_option("stream-segment-timeout", 10.0)
session.set_option("stream-segment-threads", 1)
session.set_option("stream-segment-attempts", 3)

# HLS specyficzne opcje
session.set_option("hls-live-edge", 3)
session.set_option("hls-segment-stream-data", True)
session.set_option("hls-playlist-reload-attempts", 3)

# DASH specyficzne opcje
session.set_option("dash-manifest-reload-attempts", 3)

# Opcje lokalizacji
session.set_option("locale", "pl_PL")

# Opcje FFmpeg (dla multipleksowanych strumieni)
session.set_option("ffmpeg-ffmpeg", "/usr/bin/ffmpeg")
session.set_option("ffmpeg-verbose", False)
session.set_option("ffmpeg-verbose-path", "/tmp/ffmpeg.log")
session.set_option("ffmpeg-fout", "mpegts")
session.set_option("ffmpeg-video-transcode", "copy")
session.set_option("ffmpeg-audio-transcode", "copy")

# Pobierz wartość opcji
timeout = session.get_option("http-timeout")
print(f"Timeout: {timeout}")
```

### Użycie cookies

```python
import streamlink
from http.cookiejar import MozillaCookieJar

session = streamlink.Streamlink()

# Opcja 1: Pojedyncze cookies jako słownik
session.set_option("http-cookies", {
    "session_id": "abc123",
    "user_token": "xyz789"
})

# Opcja 2: Użycie pliku cookies (format Netscape/Mozilla)
cookie_jar = MozillaCookieJar("/path/to/cookies.txt")
cookie_jar.load()
session.http.cookies = cookie_jar

streams = session.streams("https://example.com/stream")
```

### Konfiguracja SSL/TLS

```python
import streamlink

session = streamlink.Streamlink()

# Wyłącz weryfikację SSL (niezalecane w produkcji!)
session.set_option("http-ssl-verify", False)

# Użyj niestandardowego certyfikatu CA
session.set_option("http-ssl-cert", "/path/to/cert.pem")

# Lub użyj pary certyfikat + klucz
session.set_option("http-ssl-cert", ("/path/to/cert.pem", "/path/to/key.pem"))

streams = session.streams("https://example.com/stream")
```

## Obsługa strumieni

### Różne typy strumieni

```python
import streamlink
from streamlink.stream import (
    HTTPStream,
    HLSStream,
    DASHStream,
    MuxedStream
)

streams = streamlink.streams("https://example.com/stream")

for name, stream in streams.items():
    if isinstance(stream, HTTPStream):
        print(f"{name}: HTTP stream")
    elif isinstance(stream, HLSStream):
        print(f"{name}: HLS stream (Apple HTTP Live Streaming)")
    elif isinstance(stream, DASHStream):
        print(f"{name}: DASH stream (Dynamic Adaptive Streaming)")
    elif isinstance(stream, MuxedStream):
        print(f"{name}: Multipleksowany strumień (video + audio)")
```

### Ręczne tworzenie strumienia HTTP

```python
from streamlink.stream import HTTPStream
from streamlink import Streamlink

session = Streamlink()

# Utwórz strumień HTTP bezpośrednio z URL
stream = HTTPStream(session, "https://example.com/video.mp4")

# Otwórz i czytaj
with stream.open() as fd:
    data = fd.read(1024)
```

### Tworzenie strumienia HLS

```python
from streamlink.stream import HLSStream
from streamlink import Streamlink

session = Streamlink()

# Utwórz strumień HLS z URL playlisty
stream = HLSStream(session, "https://example.com/playlist.m3u8")

with stream.open() as fd:
    data = fd.read(1024)
```

### Praca z multipleksowanymi strumieniami

```python
from streamlink.stream import MuxedStream, HTTPStream
from streamlink import Streamlink

session = Streamlink()

# Utwórz oddzielne strumienie video i audio
video_stream = HTTPStream(session, "https://example.com/video.mp4")
audio_stream = HTTPStream(session, "https://example.com/audio.mp4")

# Połącz je w jeden multipleksowany strumień
muxed = MuxedStream(session, video_stream, audio_stream)

# Wymaga zainstalowanego FFmpeg
with muxed.open() as fd:
    # Czytaj zmultipleksowane dane
    data = fd.read(8192)
```

## Obsługa błędów

### Przechwytywanie wyjątków

```python
import streamlink
from streamlink.exceptions import (
    StreamlinkError,
    NoPluginError,
    NoStreamsError,
    PluginError,
    StreamError
)

url = "https://example.com/stream"

try:
    # Próbuj pobrać strumienie
    streams = streamlink.streams(url)

    if not streams:
        print("Brak dostępnych strumieni")
    else:
        stream = streams["best"]

        try:
            with stream.open() as fd:
                data = fd.read(1024)

        except StreamError as err:
            print(f"Błąd podczas otwierania strumienia: {err}")

except NoPluginError:
    print(f"Brak pluginu obsługującego ten URL: {url}")

except NoStreamsError:
    print("Plugin nie znalazł żadnych strumieni na tej stronie")

except PluginError as err:
    print(f"Błąd pluginu: {err}")

except StreamlinkError as err:
    print(f"Ogólny błąd Streamlink: {err}")

except Exception as err:
    print(f"Nieoczekiwany błąd: {err}")
```

### Timeout i retry

```python
import streamlink
from streamlink.exceptions import StreamError
import time

session = streamlink.Streamlink()
session.set_option("http-timeout", 10.0)
session.set_option("stream-segment-attempts", 3)

max_retries = 3
retry_delay = 5

for attempt in range(max_retries):
    try:
        streams = session.streams("https://example.com/stream")

        if "best" in streams:
            with streams["best"].open() as fd:
                data = fd.read(1024)
                print("Sukces!")
                break

    except StreamError as err:
        print(f"Próba {attempt + 1}/{max_retries} nieudana: {err}")

        if attempt < max_retries - 1:
            print(f"Ponawianie za {retry_delay} sekund...")
            time.sleep(retry_delay)
        else:
            print("Wszystkie próby wyczerpane")
```

### Logowanie i debugowanie

```python
import logging
import streamlink

# Włącz logowanie Streamlink
logging.basicConfig(level=logging.DEBUG)

# Lub bardziej szczegółowo
streamlink_logger = logging.getLogger("streamlink")
streamlink_logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(name)s][%(levelname)s] %(message)s'))
streamlink_logger.addHandler(handler)

# Teraz wszystkie operacje będą logowane
session = streamlink.Streamlink()
streams = session.streams("https://example.com/stream")
```

## Tworzenie własnych pluginów

### Podstawowy plugin

```python
import re
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HTTPStream

@pluginmatcher(re.compile(
    r"https?://(?:www\.)?example\.com/video/(\w+)"
))
class ExamplePlugin(Plugin):
    """
    Plugin dla example.com
    """

    def _get_streams(self):
        """
        Metoda wywoływana aby pobrać strumienie.
        Musi zwrócić słownik {nazwa: Stream} lub None.
        """

        # Pobierz stronę
        res = self.session.http.get(self.url)

        # Wyciągnij URL strumienia ze strony
        match = re.search(r'video_url":"(.*?)"', res.text)
        if not match:
            return None

        video_url = match.group(1)

        # Zwróć słownik strumieni
        return {
            "720p": HTTPStream(self.session, video_url)
        }
```

### Załadowanie własnego pluginu

```python
import streamlink
from streamlink.plugin import Plugin

# Zarejestruj plugin
session = streamlink.Streamlink()

# Załaduj pluginy z katalogu
session.plugins.load_path("/path/to/plugins/")

# Lub zarejestruj plugin bezpośrednio
from my_plugin import MyCustomPlugin
session.plugins.update({
    "mycustom": MyCustomPlugin
})

# Użyj pluginu
streams = session.streams("https://mycustom.com/stream")
```

### Plugin z opcjami

```python
import re
from streamlink.plugin import Plugin, pluginmatcher, pluginargument
from streamlink.stream import HLSStream

@pluginmatcher(re.compile(r"https?://example\.com/"))
@pluginargument(
    "api-key",
    required=True,
    metavar="KEY",
    help="Klucz API dla example.com"
)
@pluginargument(
    "quality",
    default="best",
    metavar="QUALITY",
    help="Preferowana jakość (best, 1080p, 720p, etc.)"
)
class ExamplePlugin(Plugin):

    def _get_streams(self):
        # Pobierz opcje
        api_key = self.get_option("api-key")
        quality = self.get_option("quality")

        # Użyj opcji do pobrania strumieni
        headers = {"Authorization": f"Bearer {api_key}"}

        res = self.session.http.get(
            "https://api.example.com/stream",
            headers=headers
        )

        data = res.json()

        return {
            quality: HLSStream(self.session, data["playlist_url"])
        }
```

### Użycie pluginu z opcjami

```python
import streamlink

session = streamlink.Streamlink()

# Ustaw opcje pluginu
session.set_plugin_option("example", "api-key", "your-api-key-here")
session.set_plugin_option("example", "quality", "1080p")

# Pobierz strumienie
streams = session.streams("https://example.com/stream")
```

## Pełny przykład aplikacji

```python
#!/usr/bin/env python3
"""
Przykładowa aplikacja: Pobieracz strumieni
"""

import streamlink
from streamlink.exceptions import StreamlinkError, NoPluginError
import sys
import argparse

def download_stream(url, output_file, quality="best"):
    """
    Pobiera strumień z URL i zapisuje do pliku.

    Args:
        url: URL strumienia
        output_file: Ścieżka do pliku wyjściowego
        quality: Jakość strumienia (domyślnie 'best')
    """
    try:
        # Utwórz sesję
        session = streamlink.Streamlink()

        # Opcjonalne: ustaw własny User-Agent
        session.set_option("http-headers", {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

        print(f"Pobieranie strumieni z: {url}")
        streams = session.streams(url)

        if not streams:
            print("Brak dostępnych strumieni")
            return False

        print(f"Dostępne jakości: {', '.join(streams.keys())}")

        # Wybierz strumień
        if quality not in streams:
            print(f"Jakość '{quality}' niedostępna, używam 'best'")
            quality = "best"

        stream = streams[quality]
        print(f"Pobieranie strumienia: {quality}")

        # Pobierz i zapisz
        with stream.open() as fd:
            with open(output_file, "wb") as out:
                bytes_downloaded = 0

                while True:
                    data = fd.read(8192)
                    if not data:
                        break

                    out.write(data)
                    bytes_downloaded += len(data)

                    # Pokaż postęp
                    mb = bytes_downloaded / (1024 * 1024)
                    print(f"\rPobrano: {mb:.2f} MB", end="", flush=True)

        print(f"\n✓ Zapisano do: {output_file}")
        return True

    except NoPluginError:
        print(f"✗ Brak pluginu obsługującego URL: {url}")
        return False

    except StreamlinkError as err:
        print(f"✗ Błąd Streamlink: {err}")
        return False

    except Exception as err:
        print(f"✗ Nieoczekiwany błąd: {err}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Pobieracz strumieni używający Streamlink"
    )
    parser.add_argument("url", help="URL strumienia")
    parser.add_argument("-o", "--output", required=True, help="Plik wyjściowy")
    parser.add_argument("-q", "--quality", default="best", help="Jakość (domyślnie: best)")

    args = parser.parse_args()

    success = download_stream(args.url, args.output, args.quality)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

Użycie:

```bash
python downloader.py "https://www.youtube.com/watch?v=..." -o video.mp4 -q 720p
```

## Dodatkowe zasoby

- **Oficjalna dokumentacja**: https://streamlink.github.io/
- **API Reference**: https://streamlink.github.io/api.html
- **Lista pluginów**: https://streamlink.github.io/plugins.html
- **GitHub**: https://github.com/streamlink/streamlink
- **Discord**: https://discord.gg/UJN3Bhd

## Wymagania systemowe

- Python 3.10 lub nowszy
- FFmpeg (opcjonalnie, dla multipleksowanych strumieni)

## Licencja

Streamlink jest dostępny na licencji BSD 2-Clause. Zobacz plik LICENSE w repozytorium.
