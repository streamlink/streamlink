#!/usr/bin/env python3
"""
Przykład 5: Tworzenie własnego pluginu

Pokazuje jak stworzyć własny plugin dla niestandardowej strony ze strumieniami.
"""

import re
import streamlink
from streamlink.plugin import Plugin, pluginmatcher, pluginargument
from streamlink.stream import HTTPStream, HLSStream
import json

# Przykładowy plugin dla hipotetycznej strony "example.com"
@pluginmatcher(re.compile(
    r"https?://(?:www\.)?example\.com/video/(?P<video_id>\w+)"
))
@pluginargument(
    "api-key",
    required=False,
    metavar="KEY",
    help="Opcjonalny klucz API dla example.com"
)
@pluginargument(
    "quality",
    default="best",
    metavar="QUALITY",
    help="Preferowana jakość (best, 1080p, 720p, 480p)"
)
class ExamplePlugin(Plugin):
    """
    Plugin dla example.com

    Obsługuje URLs w formacie:
    - https://example.com/video/VIDEO_ID
    - https://www.example.com/video/VIDEO_ID
    """

    def _get_streams(self):
        """
        Główna metoda pobierająca strumienie.
        W prawdziwym pluginie tutaj byłby kod do:
        1. Pobrania strony HTML
        2. Wyodrębnienia URLi strumieni (regex, JSON, API, itp.)
        3. Stworzenia obiektów Stream

        Returns:
            dict: Słownik {nazwa: Stream} lub None
        """

        # Wyciągnij ID video z URL
        match = self.match
        video_id = match.group("video_id")

        print(f"[ExamplePlugin] Przetwarzanie video ID: {video_id}")

        # Pobierz opcje pluginu
        api_key = self.get_option("api-key")
        quality_pref = self.get_option("quality")

        print(f"[ExamplePlugin] Preferencja jakości: {quality_pref}")

        # PRZYKŁAD 1: Bezpośrednie URLe HTTP (najprostsze)
        # W prawdziwym pluginie pobierz stronę i wyciągnij URLe
        streams = {}

        # Symulacja różnych jakości
        # W prawdziwości byś parsował HTML/JSON i wyciągał prawdziwe URLe
        quality_urls = {
            "1080p": f"https://cdn.example.com/videos/{video_id}_1080.mp4",
            "720p": f"https://cdn.example.com/videos/{video_id}_720.mp4",
            "480p": f"https://cdn.example.com/videos/{video_id}_480.mp4",
        }

        for quality, url in quality_urls.items():
            streams[quality] = HTTPStream(self.session, url)

        # PRZYKŁAD 2: Strumień HLS
        # Jeśli strona używa HLS, użyj HLSStream
        hls_url = f"https://cdn.example.com/videos/{video_id}/playlist.m3u8"
        # streams["hls"] = HLSStream(self.session, hls_url)

        # Dodaj aliasy 'best' i 'worst'
        if streams:
            # 'best' to najwyższa jakość
            streams["best"] = streams.get("1080p") or streams.get("720p") or streams.get("480p")

            # 'worst' to najniższa jakość
            streams["worst"] = streams.get("480p") or streams.get("720p") or streams.get("1080p")

        return streams


# Bardziej zaawansowany przykład z API
@pluginmatcher(re.compile(
    r"https?://(?:www\.)?mystream\.tv/watch/(?P<stream_id>\d+)"
))
@pluginargument(
    "username",
    required=False,
    metavar="USERNAME",
    help="Nazwa użytkownika (dla treści premium)"
)
@pluginargument(
    "password",
    required=False,
    sensitive=True,
    metavar="PASSWORD",
    help="Hasło (dla treści premium)"
)
class MyStreamPlugin(Plugin):
    """
    Zaawansowany plugin z API i uwierzytelnianiem
    """

    API_URL = "https://api.mystream.tv/v1"

    def _login(self):
        """Logowanie do serwisu"""
        username = self.get_option("username")
        password = self.get_option("password")

        if not username or not password:
            return None

        # W prawdziwym pluginie wysłałbyś żądanie POST do API
        # res = self.session.http.post(
        #     f"{self.API_URL}/login",
        #     data={"username": username, "password": password}
        # )
        # return res.json().get("token")

        print(f"[MyStreamPlugin] Logowanie jako: {username}")
        return "fake_token_12345"

    def _get_stream_data(self, stream_id, token=None):
        """Pobiera dane strumienia z API"""

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # W prawdziwym pluginie:
        # res = self.session.http.get(
        #     f"{self.API_URL}/streams/{stream_id}",
        #     headers=headers
        # )
        # return res.json()

        # Symulacja odpowiedzi API
        return {
            "stream_id": stream_id,
            "title": "Example Stream",
            "formats": [
                {"quality": "1080p", "url": f"https://cdn.mystream.tv/{stream_id}_1080.mp4"},
                {"quality": "720p", "url": f"https://cdn.mystream.tv/{stream_id}_720.mp4"},
                {"quality": "480p", "url": f"https://cdn.mystream.tv/{stream_id}_480.mp4"},
            ],
            "hls_url": f"https://cdn.mystream.tv/{stream_id}/master.m3u8"
        }

    def _get_streams(self):
        """Pobiera strumienie"""

        # Wyciągnij ID ze strumienia
        stream_id = self.match.group("stream_id")
        print(f"[MyStreamPlugin] Przetwarzanie strumienia: {stream_id}")

        # Logowanie (jeśli podano dane)
        token = self._login()

        # Pobierz dane strumienia
        stream_data = self._get_stream_data(stream_id, token)

        print(f"[MyStreamPlugin] Tytuł: {stream_data.get('title')}")

        # Stwórz strumienie
        streams = {}

        # HTTP strumienie dla różnych jakości
        for fmt in stream_data.get("formats", []):
            quality = fmt["quality"]
            url = fmt["url"]
            streams[quality] = HTTPStream(self.session, url)

        # HLS strumień
        if hls_url := stream_data.get("hls_url"):
            # Możesz parsować HLS playlist, żeby uzyskać wszystkie warianty
            try:
                hls_streams = HLSStream.parse_variant_playlist(
                    self.session,
                    hls_url
                )
                streams.update(hls_streams)
            except Exception as err:
                print(f"[MyStreamPlugin] Błąd parsowania HLS: {err}")

        return streams


def demo_custom_plugin():
    """Demonstracja użycia własnego pluginu"""

    print("=" * 60)
    print("Demonstracja własnego pluginu")
    print("=" * 60)

    # Utwórz sesję
    session = streamlink.Streamlink()

    # Zarejestruj własny plugin
    # W prawdziwej aplikacji pluginy byłyby w osobnych plikach
    # i ładowane przez session.plugins.load_path("/path/to/plugins/")

    session.plugins.update({
        "example": ExamplePlugin,
        "mystream": MyStreamPlugin,
    })

    print("\n✓ Zarejestrowano własne pluginy: example, mystream")

    # Test 1: ExamplePlugin
    print("\n" + "-" * 60)
    print("Test 1: ExamplePlugin")
    print("-" * 60)

    url1 = "https://example.com/video/abc123"

    # Ustaw opcje pluginu
    session.set_plugin_option("example", "quality", "720p")

    try:
        plugin_name, plugin_class, _ = session.resolve_url(url1)
        print(f"✓ Rozwiązano plugin: {plugin_name}")

        streams = session.streams(url1)
        print(f"✓ Znaleziono {len(streams)} strumieni")
        print(f"  Dostępne: {', '.join(streams.keys())}")

        # Wyświetl URLe (w tym przypadku fikcyjne)
        for name, stream in streams.items():
            if hasattr(stream, 'url'):
                print(f"  {name}: {stream.url}")

    except Exception as err:
        print(f"✗ Błąd: {err}")

    # Test 2: MyStreamPlugin
    print("\n" + "-" * 60)
    print("Test 2: MyStreamPlugin (z logowaniem)")
    print("-" * 60)

    url2 = "https://mystream.tv/watch/98765"

    # Ustaw dane logowania
    session.set_plugin_option("mystream", "username", "testuser")
    session.set_plugin_option("mystream", "password", "testpass")

    try:
        plugin_name, plugin_class, _ = session.resolve_url(url2)
        print(f"✓ Rozwiązano plugin: {plugin_name}")

        streams = session.streams(url2)
        print(f"✓ Znaleziono {len(streams)} strumieni")
        print(f"  Dostępne: {', '.join(streams.keys())}")

    except Exception as err:
        print(f"✗ Błąd: {err}")

    print("\n" + "=" * 60)

def main():
    """Main function"""
    print(__doc__)
    demo_custom_plugin()

    print("\nℹ UWAGA:")
    print("  To są przykładowe pluginy dla demonstracji.")
    print("  W prawdziwych pluginach należy:")
    print("  - Pobierać prawdziwe strony HTML/JSON")
    print("  - Parsować je, aby wydobyć URLe strumieni")
    print("  - Obsługiwać błędy i edge cases")
    print("  - Testować z prawdziwymi serwisami")

if __name__ == "__main__":
    main()
