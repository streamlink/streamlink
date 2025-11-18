#!/usr/bin/env python3
"""
Przykład 4: Informacje o strumieniach

Pokazuje jak wydobyć szczegółowe informacje o dostępnych strumieniach.
"""

import streamlink
from streamlink.stream import HTTPStream, HLSStream, DASHStream, MuxedStream
import sys

def analyze_stream(name, stream):
    """Analizuje i wyświetla informacje o strumieniu"""
    print(f"\n  Strumień: {name}")
    print(f"  Typ: {type(stream).__name__}")

    # Informacje specyficzne dla typu
    if isinstance(stream, HTTPStream):
        if hasattr(stream, 'url'):
            print(f"  URL: {stream.url}")

    elif isinstance(stream, HLSStream):
        print(f"  Typ: HLS (HTTP Live Streaming)")
        if hasattr(stream, 'url'):
            print(f"  Playlist URL: {stream.url}")

    elif isinstance(stream, DASHStream):
        print(f"  Typ: DASH (Dynamic Adaptive Streaming)")
        if hasattr(stream, 'mpd_url'):
            print(f"  MPD URL: {stream.mpd_url}")

    elif isinstance(stream, MuxedStream):
        print(f"  Typ: Multipleksowany (video + audio)")

    # Spróbuj uzyskać URL
    try:
        url = stream.to_url()
        if url:
            print(f"  Direct URL: {url[:80]}...")
    except:
        pass

    # Spróbuj uzyskać URL manifestu
    try:
        manifest = stream.to_manifest_url()
        if manifest:
            print(f"  Manifest URL: {manifest[:80]}...")
    except:
        pass

def get_stream_info(url):
    """
    Pobiera i wyświetla informacje o strumieniach dla danego URL.

    Args:
        url: URL do analizy
    """
    print(f"Analizowanie: {url}")
    print("=" * 60)

    try:
        # Utwórz sesję
        session = streamlink.Streamlink()

        # Najpierw sprawdź, czy możemy rozwiązać plugin
        print("\n1. Rozwiązywanie pluginu...")
        try:
            plugin_name, plugin_class, resolved_url = session.resolve_url(url)
            print(f"   ✓ Znaleziono plugin: {plugin_name}")
            print(f"   ✓ Klasa pluginu: {plugin_class.__name__}")
            if resolved_url != url:
                print(f"   ✓ Rozwiązany URL: {resolved_url}")
        except streamlink.NoPluginError:
            print(f"   ✗ Brak pluginu dla tego URL")
            return

        # Pobierz strumienie
        print("\n2. Pobieranie strumieni...")
        streams = session.streams(url)

        if not streams:
            print("   ✗ Brak dostępnych strumieni")
            return

        print(f"   ✓ Znaleziono {len(streams)} strumieni")

        # Wyświetl podsumowanie
        print("\n3. Podsumowanie strumieni:")

        # Grupuj według typu
        by_type = {}
        for name, stream in streams.items():
            stream_type = type(stream).__name__
            if stream_type not in by_type:
                by_type[stream_type] = []
            by_type[stream_type].append(name)

        for stream_type, names in by_type.items():
            print(f"   {stream_type}: {', '.join(names)}")

        # Szczegółowe informacje o każdym strumieniu
        print("\n4. Szczegółowe informacje:")

        for name, stream in streams.items():
            analyze_stream(name, stream)

        # Rekomendacje
        print("\n5. Rekomendacje:")

        if "best" in streams:
            print("   • Użyj 'best' dla najlepszej jakości")
        if "worst" in streams:
            print("   • Użyj 'worst' dla najniższej jakości")

        # Znajdź strumienie HD
        hd_streams = [name for name in streams.keys()
                      if any(res in name for res in ['720p', '1080p', '1440p', '2160p', '4k'])]
        if hd_streams:
            print(f"   • Dostępne strumienie HD: {', '.join(hd_streams)}")

        # Znajdź strumienie tylko audio
        audio_streams = [name for name in streams.keys() if 'audio' in name.lower()]
        if audio_streams:
            print(f"   • Dostępne strumienie audio: {', '.join(audio_streams)}")

        # Test otwarcia najlepszego strumienia
        print("\n6. Test otwarcia strumienia...")

        if "best" in streams:
            try:
                stream = streams["best"]
                with stream.open() as fd:
                    # Spróbuj odczytać kilka bajtów
                    data = fd.read(1024)
                    print(f"   ✓ Pomyślnie otwarto strumień 'best'")
                    print(f"   ✓ Odczytano {len(data)} bajtów")

                    # Analiza typu danych
                    if data[:4] == b'\x00\x00\x00\x1c':
                        print(f"   ℹ Prawdopodobnie strumień MP4")
                    elif data[:3] == b'ID3':
                        print(f"   ℹ Prawdopodobnie strumień MP3/AAC")
                    elif data[:4] == b'#EXC':
                        print(f"   ℹ Prawdopodobnie playlista M3U")
                    elif data[:2] == b'\xff\xfb' or data[:2] == b'\xff\xf3':
                        print(f"   ℹ Prawdopodobnie strumień MPEG")

            except Exception as err:
                print(f"   ✗ Błąd podczas otwierania: {err}")

    except streamlink.PluginError as err:
        print(f"\n✗ Błąd pluginu: {err}")
    except streamlink.StreamError as err:
        print(f"\n✗ Błąd strumienia: {err}")
    except Exception as err:
        print(f"\n✗ Nieoczekiwany błąd: {err}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Użycie: python 04_stream_information.py <URL>")
        print("\nPrzykład:")
        print("  python 04_stream_information.py 'https://www.youtube.com/watch?v=...'")
        sys.exit(1)

    url = sys.argv[1]
    get_stream_info(url)

if __name__ == "__main__":
    main()
