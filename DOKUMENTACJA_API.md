# Dokumentacja API Streamlink

Kompletna dokumentacja wszystkich publicznych funkcji i klas modułu Streamlink.

## Spis treści

- [Główne API](#główne-api)
  - [streamlink.streams()](#streamlinkstreams)
  - [Klasa Streamlink](#klasa-streamlink)
- [Wyjątki](#wyjątki)
- [Strumienie](#strumienie)
  - [Klasa Stream](#klasa-stream)
  - [HTTPStream](#httpstream)
  - [HLSStream](#hlsstream)
  - [DASHStream](#dashstream)
  - [MuxedStream](#muxedstream)
- [Pluginy](#pluginy)
  - [Klasa Plugin](#klasa-plugin)
- [Opcje](#opcje)

---

## Główne API

### streamlink.streams()

```python
streamlink.streams(url: str, **params) -> dict[str, Stream]
```

Funkcja pomocnicza do szybkiego pobierania strumieni z URL. Tworzy tymczasową sesję Streamlink, znajduje odpowiedni plugin i wyodrębnia strumienie.

**Parametry:**

- `url` (str): URL do przetworzenia
- `**params`: Dodatkowe argumenty przekazywane do metody `Plugin.streams()`

**Zwraca:**

- `dict[str, Stream]`: Słownik mapujący nazwy jakości na obiekty Stream

**Wyjątki:**

- `NoPluginError`: Gdy nie znaleziono pluginu dla podanego URL
- `NoStreamsError`: Gdy plugin nie znalazł strumieni
- `PluginError`: Gdy wystąpił błąd w pluginie

**Przykład:**

```python
import streamlink

streams = streamlink.streams("https://www.youtube.com/watch?v=...")
if "best" in streams:
    stream = streams["best"]
    with stream.open() as fd:
        data = fd.read(1024)
```

---

## Klasa Streamlink

```python
class streamlink.Streamlink(
    options: Mapping[str, Any] | Options | None = None,
    *,
    plugins_builtin: bool = True,
    plugins_lazy: bool = True
)
```

Główna klasa sesji Streamlink używana do ładowania i rozwiązywania pluginów oraz przechowywania opcji.

**Parametry:**

- `options` (Mapping | Options | None): Opcje niestandardowe
- `plugins_builtin` (bool): Czy ładować wbudowane pluginy (domyślnie: True)
- `plugins_lazy` (bool): Ładować pluginy w trybie lazy loading (domyślnie: True)

**Atrybuty:**

- `http` (HTTPSession): Instancja sesji HTTP używana do wszystkich żądań
- `options` (StreamlinkOptions): Opcje tej sesji
- `plugins` (StreamlinkPlugins): Pluginy załadowane w tej sesji

### Metody

#### set_option()

```python
Streamlink.set_option(key: str, value: Any) -> None
```

Ustawia ogólne opcje używane przez pluginy i strumienie.

**Parametry:**

- `key` (str): Nazwa opcji
- `value` (Any): Wartość opcji

**Przykład:**

```python
session = streamlink.Streamlink()
session.set_option("http-proxy", "http://proxy.example.com:8080")
session.set_option("http-timeout", 30.0)
```

#### get_option()

```python
Streamlink.get_option(key: str) -> Any
```

Zwraca aktualną wartość określonej opcji.

**Parametry:**

- `key` (str): Nazwa opcji

**Zwraca:**

- `Any`: Wartość opcji

**Przykład:**

```python
timeout = session.get_option("http-timeout")
```

#### resolve_url()

```python
Streamlink.resolve_url(
    url: str,
    follow_redirect: bool = True
) -> tuple[str, type[Plugin], str]
```

Próbuje znaleźć plugin, który może obsłużyć dany URL.

**Parametry:**

- `url` (str): URL do sprawdzenia
- `follow_redirect` (bool): Czy podążać za przekierowaniami (domyślnie: True)

**Zwraca:**

- `tuple[str, type[Plugin], str]`: Krotka (nazwa_pluginu, klasa_pluginu, rozwiązany_url)

**Wyjątki:**

- `NoPluginError`: Gdy nie znaleziono pluginu

**Przykład:**

```python
try:
    name, plugin_class, url = session.resolve_url("https://example.com/stream")
    print(f"Znaleziono plugin: {name}")
except NoPluginError:
    print("Brak pluginu dla tego URL")
```

#### resolve_url_no_redirect()

```python
Streamlink.resolve_url_no_redirect(url: str) -> tuple[str, type[Plugin], str]
```

Próbuje znaleźć plugin bez podążania za przekierowaniami. Równoważne `resolve_url(url, follow_redirect=False)`.

#### streams()

```python
Streamlink.streams(
    url: str,
    options: Options | None = None,
    **params
) -> dict[str, Stream]
```

Znajduje plugin i wyodrębnia strumienie z URL.

**Parametry:**

- `url` (str): URL do przetworzenia
- `options` (Options | None): Opcjonalne opcje przekazywane do pluginu
- `**params`: Dodatkowe argumenty przekazywane do `Plugin.streams()`

**Zwraca:**

- `dict[str, Stream]`: Słownik strumieni

**Wyjątki:**

- `NoPluginError`: Gdy nie znaleziono pluginu

**Przykład:**

```python
session = streamlink.Streamlink()
session.set_option("http-headers", {"User-Agent": "Custom"})
streams = session.streams("https://example.com/stream")
```

#### set_plugin_option()

```python
Streamlink.set_plugin_option(plugin: str, key: str, value: Any) -> None
```

Ustawia opcję specyficzną dla danego pluginu.

**Parametry:**

- `plugin` (str): Nazwa pluginu
- `key` (str): Nazwa opcji
- `value` (Any): Wartość opcji

**Przykład:**

```python
session.set_plugin_option("twitch", "disable-ads", True)
```

#### get_plugin_option()

```python
Streamlink.get_plugin_option(plugin: str, key: str) -> Any
```

Pobiera opcję specyficzną dla danego pluginu.

**Parametry:**

- `plugin` (str): Nazwa pluginu
- `key` (str): Nazwa opcji

**Zwraca:**

- `Any`: Wartość opcji

---

## Wyjątki

### StreamlinkError

```python
class streamlink.StreamlinkError(Exception)
```

Bazowy wyjątek dla wszystkich błędów Streamlink.

### PluginError

```python
class streamlink.PluginError(StreamlinkError)
```

Wyjątek związany z błędami pluginów.

### FatalPluginError

```python
class streamlink.FatalPluginError(PluginError)
```

Błąd pluginu, który nie może zostać naprawiony. Pluginy powinny używać tego wyjątku, gdy wystąpią nieodwracalne błędy.

### NoPluginError

```python
class streamlink.NoPluginError(StreamlinkError)
```

Wyjątek zgłaszany, gdy nie znaleziono pluginu dla danego URL.

**Przykład:**

```python
from streamlink.exceptions import NoPluginError

try:
    streams = session.streams("https://invalid-url.com")
except NoPluginError:
    print("Brak pluginu dla tego URL")
```

### NoStreamsError

```python
class streamlink.NoStreamsError(StreamlinkError)
```

Wyjątek, którego pluginy powinny używać w `_get_streams()`, gdy nie mogą zwrócić None ani pustego słownika.

### StreamError

```python
class streamlink.StreamError(StreamlinkError)
```

Wyjątek związany z błędami strumieni.

**Przykład:**

```python
from streamlink.exceptions import StreamError

try:
    with stream.open() as fd:
        data = fd.read(1024)
except StreamError as err:
    print(f"Błąd strumienia: {err}")
```

### StreamlinkWarning

```python
class streamlink.StreamlinkWarning(UserWarning)
```

Ostrzeżenie specyficzne dla Streamlink.

### StreamlinkDeprecationWarning

```python
class streamlink.StreamlinkDeprecationWarning(StreamlinkWarning)
```

Ostrzeżenie o przestarzałych funkcjach.

---

## Strumienie

### Klasa Stream

```python
class streamlink.Stream(session: Streamlink)
```

Bazowa klasa dla wszystkich typów strumieni.

#### Metody

##### open()

```python
Stream.open() -> StreamIO
```

Otwiera strumień i zwraca obiekt podobny do pliku.

**Zwraca:**

- `StreamIO`: Obiekt do czytania danych strumienia

**Wyjątki:**

- `StreamError`: Gdy nie można otworzyć strumienia

**Przykład:**

```python
stream = streams["best"]
with stream.open() as fd:
    data = fd.read(1024)
```

##### to_url()

```python
Stream.to_url() -> str | None
```

Zwraca URL strumienia, jeśli jest dostępny. Nie wszystkie typy strumieni to obsługują.

**Zwraca:**

- `str | None`: URL lub None

**Przykład:**

```python
if url := stream.to_url():
    print(f"URL strumienia: {url}")
```

##### to_manifest_url()

```python
Stream.to_manifest_url() -> str | None
```

Zwraca URL manifestu strumienia (dla HLS/DASH), jeśli jest dostępny.

**Zwraca:**

- `str | None`: URL manifestu lub None

---

### HTTPStream

```python
class streamlink.HTTPStream(
    session: Streamlink,
    url: str,
    **args
)
```

Strumień HTTP - najprostszy typ strumienia, pobiera dane bezpośrednio z URL HTTP.

**Parametry:**

- `session` (Streamlink): Sesja Streamlink
- `url` (str): URL strumienia HTTP
- `**args`: Dodatkowe argumenty przekazywane do żądania HTTP

**Atrybuty:**

- `url` (str): URL strumienia

**Przykład:**

```python
from streamlink import Streamlink
from streamlink.stream import HTTPStream

session = Streamlink()
stream = HTTPStream(session, "https://example.com/video.mp4")

with stream.open() as fd:
    data = fd.read(1024)
```

---

### HLSStream

```python
class streamlink.HLSStream(
    session: Streamlink,
    url: str,
    **args
)
```

Strumień HLS (HTTP Live Streaming) - obsługuje playlisty .m3u8.

**Parametry:**

- `session` (Streamlink): Sesja Streamlink
- `url` (str): URL playlisty HLS (.m3u8)
- `**args`: Dodatkowe argumenty

**Metody statyczne:**

##### parse_variant_playlist()

```python
@staticmethod
HLSStream.parse_variant_playlist(
    session: Streamlink,
    url: str,
    **kwargs
) -> dict[str, HLSStream]
```

Parsuje wariantową playlistę HLS i zwraca słownik strumieni.

**Parametry:**

- `session` (Streamlink): Sesja
- `url` (str): URL playlisty wariantowej
- `**kwargs`: Dodatkowe argumenty

**Zwraca:**

- `dict[str, HLSStream]`: Słownik strumieni według jakości

**Przykład:**

```python
from streamlink import Streamlink
from streamlink.stream import HLSStream

session = Streamlink()
streams = HLSStream.parse_variant_playlist(
    session,
    "https://example.com/master.m3u8"
)

# streams = {"720p": HLSStream(...), "1080p": HLSStream(...), ...}
```

---

### MuxedHLSStream

```python
class streamlink.MuxedHLSStream(
    session: Streamlink,
    video: HLSStream,
    audio: HLSStream,
    **args
)
```

Strumień HLS multipleksujący oddzielne strumienie video i audio.

**Parametry:**

- `session` (Streamlink): Sesja
- `video` (HLSStream): Strumień video
- `audio` (HLSStream): Strumień audio
- `**args`: Dodatkowe argumenty

**Wymaga:**

- FFmpeg zainstalowany w systemie

---

### DASHStream

```python
class streamlink.DASHStream(
    session: Streamlink,
    mpd_url: str,
    **args
)
```

Strumień DASH (Dynamic Adaptive Streaming over HTTP) - obsługuje manifesty MPD.

**Parametry:**

- `session` (Streamlink): Sesja
- `mpd_url` (str): URL manifestu MPD
- `**args`: Dodatkowe argumenty

**Metody statyczne:**

##### parse_manifest()

```python
@staticmethod
DASHStream.parse_manifest(
    session: Streamlink,
    url: str,
    **kwargs
) -> dict[str, DASHStream]
```

Parsuje manifest DASH i zwraca słownik strumieni.

**Przykład:**

```python
from streamlink import Streamlink
from streamlink.stream import DASHStream

session = Streamlink()
streams = DASHStream.parse_manifest(
    session,
    "https://example.com/manifest.mpd"
)
```

---

### MuxedStream

```python
class streamlink.MuxedStream(
    session: Streamlink,
    video: Stream,
    audio: Stream,
    **args
)
```

Multipleksuje oddzielne strumienie video i audio w jeden strumień używając FFmpeg.

**Parametry:**

- `session` (Streamlink): Sesja
- `video` (Stream): Strumień video
- `audio` (Stream): Strumień audio
- `**args`: Dodatkowe argumenty dla FFmpeg

**Wymaga:**

- FFmpeg zainstalowany w systemie

**Przykład:**

```python
from streamlink import Streamlink
from streamlink.stream import HTTPStream, MuxedStream

session = Streamlink()

video = HTTPStream(session, "https://example.com/video.mp4")
audio = HTTPStream(session, "https://example.com/audio.mp4")

muxed = MuxedStream(session, video, audio)

with muxed.open() as fd:
    # Czytaj multipleksowane dane
    data = fd.read(8192)
```

---

### StreamIO

```python
class streamlink.StreamIO
```

Interfejs podobny do pliku do czytania danych strumienia. Zwracany przez `Stream.open()`.

**Metody:**

##### read()

```python
StreamIO.read(size: int = -1) -> bytes
```

Czyta dane ze strumienia.

**Parametry:**

- `size` (int): Liczba bajtów do odczytania (-1 = wszystkie)

**Zwraca:**

- `bytes`: Odczytane dane

##### close()

```python
StreamIO.close() -> None
```

Zamyka strumień.

**Przykład:**

```python
fd = stream.open()
try:
    data = fd.read(1024)
finally:
    fd.close()

# Lub używając context managera:
with stream.open() as fd:
    data = fd.read(1024)
```

---

### StreamIOWrapper

```python
class streamlink.StreamIOWrapper(session: Streamlink, stream: Stream)
```

Wrapper dla StreamIO dodający dodatkową funkcjonalność.

---

### StreamIOIterWrapper

```python
class streamlink.StreamIOIterWrapper(session: Streamlink, stream: Stream)
```

Wrapper umożliwiający iterację po strumieniu.

**Przykład:**

```python
for chunk in StreamIOIterWrapper(session, stream):
    process(chunk)
```

---

### StreamIOThreadWrapper

```python
class streamlink.StreamIOThreadWrapper(
    session: Streamlink,
    stream: Stream,
    timeout: float | None = None
)
```

Wrapper uruchamiający czytanie strumienia w osobnym wątku.

---

## Pluginy

### Klasa Plugin

```python
class streamlink.Plugin(session: Streamlink, url: str, options: Options | None = None)
```

Bazowa klasa dla wszystkich pluginów Streamlink.

**Parametry:**

- `session` (Streamlink): Sesja Streamlink
- `url` (str): URL do przetworzenia
- `options` (Options | None): Opcje pluginu

**Atrybuty:**

- `session` (Streamlink): Sesja
- `url` (str): URL
- `options` (Options): Opcje

#### Metody

##### streams()

```python
Plugin.streams(**kwargs) -> dict[str, Stream]
```

Publiczna metoda do pobierania strumieni. Wywołuje wewnętrzną `_get_streams()`.

**Zwraca:**

- `dict[str, Stream]`: Słownik strumieni

**Przykład użycia:**

```python
plugin_name, plugin_class, url = session.resolve_url("https://example.com")
plugin = plugin_class(session, url)
streams = plugin.streams()
```

#### Metody do nadpisania

##### _get_streams()

```python
Plugin._get_streams() -> dict[str, Stream] | None
```

Metoda, którą musisz zaimplementować w swoim pluginie. Powinna zwrócić słownik strumieni lub None.

**Zwraca:**

- `dict[str, Stream] | None`: Słownik strumieni lub None

**Przykład:**

```python
import re
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream import HTTPStream

@pluginmatcher(re.compile(r"https?://example\.com/video/(\w+)"))
class MyPlugin(Plugin):

    def _get_streams(self):
        # Pobierz stronę
        res = self.session.http.get(self.url)

        # Wyodrębnij URL strumienia
        match = re.search(r'video_url":"(.*?)"', res.text)
        if not match:
            return None

        video_url = match.group(1)

        # Zwróć strumienie
        return {
            "720p": HTTPStream(self.session, video_url)
        }
```

#### Dekoratory

##### @pluginmatcher

```python
@pluginmatcher(pattern: re.Pattern)
```

Dekorator rejestrujący wzorzec URL, który plugin obsługuje.

**Parametry:**

- `pattern` (re.Pattern): Skompilowane wyrażenie regularne

**Przykład:**

```python
import re
from streamlink.plugin import pluginmatcher, Plugin

@pluginmatcher(re.compile(
    r"https?://(?:www\.)?example\.com/(?P<video_id>\w+)"
))
class ExamplePlugin(Plugin):
    pass
```

##### @pluginargument

```python
@pluginargument(
    name: str,
    required: bool = False,
    default: Any = None,
    metavar: str | None = None,
    help: str | None = None,
    **kwargs
)
```

Dekorator definiujący argument/opcję pluginu.

**Parametry:**

- `name` (str): Nazwa opcji
- `required` (bool): Czy opcja jest wymagana
- `default` (Any): Wartość domyślna
- `metavar` (str): Nazwa wyświetlana w help
- `help` (str): Opis opcji

**Przykład:**

```python
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
import re

@pluginmatcher(re.compile(r"https?://example\.com/"))
@pluginargument("api-key", required=True, help="API key")
@pluginargument("quality", default="best", help="Quality preference")
class ExamplePlugin(Plugin):

    def _get_streams(self):
        api_key = self.get_option("api-key")
        quality = self.get_option("quality")
        # ... użyj opcji
```

#### Pomocnicze metody

##### get_option()

```python
Plugin.get_option(key: str) -> Any
```

Pobiera wartość opcji pluginu.

##### set_option()

```python
Plugin.set_option(key: str, value: Any) -> None
```

Ustawia wartość opcji pluginu.

---

## Opcje

### Klasa Options

```python
class streamlink.Options(defaults: dict | None = None)
```

Kontener dla opcji pluginów i strumieni.

**Parametry:**

- `defaults` (dict | None): Domyślne wartości opcji

#### Metody

##### set()

```python
Options.set(key: str, value: Any) -> None
```

Ustawia opcję.

##### get()

```python
Options.get(key: str) -> Any
```

Pobiera wartość opcji.

##### update()

```python
Options.update(options: dict | Options) -> None
```

Aktualizuje wiele opcji naraz.

**Przykład:**

```python
from streamlink import Options

options = Options()
options.set("http-proxy", "http://proxy:8080")
options.set("http-timeout", 30.0)

# Lub
options.update({
    "http-proxy": "http://proxy:8080",
    "http-timeout": 30.0
})
```

---

## Dostępne opcje sesji

### Opcje HTTP

- `http-proxy` (str): Proxy HTTP
- `https-proxy` (str): Proxy HTTPS
- `http-cookies` (dict | CookieJar): Cookies
- `http-headers` (dict): Nagłówki HTTP
- `http-query-params` (dict): Parametry zapytania
- `http-timeout` (float): Timeout połączenia (sekundy)
- `http-ssl-verify` (bool): Weryfikacja certyfikatu SSL
- `http-ssl-cert` (str | tuple): Ścieżka do certyfikatu SSL
- `http-trust-env` (bool): Użyj zmiennych środowiskowych dla proxy

### Opcje strumieni

- `stream-timeout` (float): Timeout strumienia
- `stream-segment-timeout` (float): Timeout segmentu
- `stream-segment-threads` (int): Liczba wątków dla segmentów
- `stream-segment-attempts` (int): Liczba prób pobrania segmentu

### Opcje HLS

- `hls-live-edge` (int): Liczba segmentów od końca playlisty live
- `hls-segment-stream-data` (bool): Strumieniuj dane segmentów
- `hls-playlist-reload-attempts` (int): Liczba prób przeładowania playlisty
- `hls-playlist-reload-time` (float): Czas między próbami (sekundy)
- `hls-start-offset` (float): Offset początkowy w strumieniu
- `hls-duration` (float): Czas trwania do pobrania
- `hls-live-restart` (bool): Restart od początku dla streamów live

### Opcje DASH

- `dash-manifest-reload-attempts` (int): Liczba prób przeładowania manifestu

### Opcje FFmpeg

- `ffmpeg-ffmpeg` (str): Ścieżka do binarki ffmpeg
- `ffmpeg-verbose` (bool): Verbose output FFmpeg
- `ffmpeg-verbose-path` (str): Ścieżka do logu FFmpeg
- `ffmpeg-fout` (str): Format wyjściowy
- `ffmpeg-video-transcode` (str): Codec video (np. "copy")
- `ffmpeg-audio-transcode` (str): Codec audio (np. "copy")
- `ffmpeg-copyts` (bool): Kopiuj timestampy

### Opcje lokalizacji

- `locale` (str): Kod lokalizacji (np. "pl_PL", "en_US")

**Przykład użycia opcji:**

```python
from streamlink import Streamlink

session = Streamlink()

# Konfiguracja HTTP
session.set_option("http-proxy", "http://proxy.example.com:8080")
session.set_option("http-headers", {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://example.com"
})
session.set_option("http-timeout", 30.0)

# Konfiguracja strumieni
session.set_option("stream-segment-threads", 2)
session.set_option("stream-segment-attempts", 3)

# Konfiguracja HLS
session.set_option("hls-live-edge", 5)
session.set_option("hls-segment-stream-data", True)

# Pobierz strumienie
streams = session.streams("https://example.com/stream")
```

---

## Stałe

### Priorytety pluginów

```python
streamlink.plugin.NO_PRIORITY = 0
streamlink.plugin.LOW_PRIORITY = 10
streamlink.plugin.NORMAL_PRIORITY = 20
streamlink.plugin.HIGH_PRIORITY = 30
```

Używane przy definiowaniu priorytetów dopasowania pluginów, gdy wiele pluginów może obsługiwać ten sam URL.

**Przykład:**

```python
from streamlink.plugin import Plugin, pluginmatcher, HIGH_PRIORITY
import re

@pluginmatcher(
    re.compile(r"https?://example\.com/"),
    priority=HIGH_PRIORITY
)
class ExamplePlugin(Plugin):
    pass
```

---

## Informacje o wersji

```python
import streamlink

print(streamlink.__version__)  # np. "6.0.0"
print(streamlink.__title__)     # "streamlink"
print(streamlink.__license__)   # "Simplified BSD"
```

---

## Obsługa logowania

Streamlink używa standardowego modułu `logging` Pythona.

```python
import logging
import streamlink

# Włącz debug logging dla Streamlink
logging.basicConfig(level=logging.DEBUG)

# Lub bardziej szczegółowo
logger = logging.getLogger("streamlink")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Wszystkie operacje będą teraz logowane
session = streamlink.Streamlink()
streams = session.streams("https://example.com/stream")
```

---

## Przykłady zaawansowane

### Własny handler HTTP

```python
from streamlink import Streamlink
from requests.adapters import HTTPAdapter

session = Streamlink()

# Dodaj własny adapter HTTP
adapter = HTTPAdapter(max_retries=5)
session.http.mount("http://", adapter)
session.http.mount("https://", adapter)

streams = session.streams("https://example.com/stream")
```

### Użycie z async/await

Streamlink nie jest natywnie asynchroniczny, ale możesz używać go w kontekście asynchronicznym:

```python
import asyncio
import streamlink
from concurrent.futures import ThreadPoolExecutor

async def download_stream(url):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()

    def _download():
        streams = streamlink.streams(url)
        if "best" in streams:
            with streams["best"].open() as fd:
                return fd.read(1024)
        return None

    data = await loop.run_in_executor(executor, _download)
    return data

# Użycie
data = await download_stream("https://example.com/stream")
```

---

## Dodatkowe zasoby

- **Oficjalna dokumentacja**: https://streamlink.github.io/
- **API Reference (EN)**: https://streamlink.github.io/api.html
- **Kod źródłowy**: https://github.com/streamlink/streamlink
- **Zgłoszenia błędów**: https://github.com/streamlink/streamlink/issues

---

## Licencja

Streamlink jest dostępny na licencji BSD 2-Clause.

Copyright 2025 Streamlink

---

*Dokumentacja wygenerowana dla Streamlink jako moduł Python*
