#!/usr/bin/env python3
"""
Przykład 2: Pobieranie strumienia do pliku

Pokazuje jak zapisać cały strumień do pliku lokalnego.
"""

import streamlink
import sys
import os

def download_stream(url, output_file, quality="best", max_size_mb=None):
    """
    Pobiera strumień i zapisuje do pliku.

    Args:
        url: URL strumienia
        output_file: Ścieżka do pliku wyjściowego
        quality: Jakość strumienia (domyślnie 'best')
        max_size_mb: Maksymalny rozmiar do pobrania w MB (None = bez limitu)

    Returns:
        bool: True jeśli sukces, False w przeciwnym razie
    """
    try:
        print(f"Pobieranie strumieni z: {url}")

        # Pobierz strumienie
        streams = streamlink.streams(url)

        if not streams:
            print("✗ Brak dostępnych strumieni")
            return False

        print(f"Dostępne jakości: {', '.join(streams.keys())}")

        # Wybierz strumień
        if quality not in streams:
            print(f"⚠ Jakość '{quality}' niedostępna, używam 'best'")
            quality = "best"

        stream = streams[quality]
        print(f"Pobieranie strumienia: {quality} ({type(stream).__name__})")

        # Oblicz limit bajtów
        max_bytes = None
        if max_size_mb:
            max_bytes = max_size_mb * 1024 * 1024
            print(f"Limit rozmiaru: {max_size_mb} MB")

        # Otwórz strumień i zapisz do pliku
        bytes_written = 0
        chunk_size = 8192  # 8 KB na chunk

        with stream.open() as fd:
            with open(output_file, "wb") as out:
                print(f"Zapisywanie do: {output_file}")
                print("Pobieranie...")

                while True:
                    # Sprawdź limit
                    if max_bytes and bytes_written >= max_bytes:
                        print(f"\n✓ Osiągnięto limit {max_size_mb} MB")
                        break

                    # Czytaj chunk
                    data = fd.read(chunk_size)
                    if not data:
                        break

                    # Zapisz
                    out.write(data)
                    bytes_written += len(data)

                    # Wyświetl postęp
                    mb = bytes_written / (1024 * 1024)
                    print(f"\rPobrano: {mb:.2f} MB", end="", flush=True)

        print(f"\n✓ Zapisano {bytes_written / (1024 * 1024):.2f} MB do: {output_file}")
        return True

    except streamlink.NoPluginError:
        print(f"✗ Brak pluginu dla URL: {url}")
        return False
    except streamlink.StreamError as err:
        print(f"✗ Błąd strumienia: {err}")
        return False
    except IOError as err:
        print(f"✗ Błąd zapisu do pliku: {err}")
        return False
    except Exception as err:
        print(f"✗ Nieoczekiwany błąd: {err}")
        return False

def main():
    if len(sys.argv) < 3:
        print("Użycie: python 02_download_to_file.py <URL> <plik_wyjściowy> [jakość] [max_MB]")
        print("\nPrzykład:")
        print("  python 02_download_to_file.py 'https://example.com/stream' output.mp4 720p 100")
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2]
    quality = sys.argv[3] if len(sys.argv) > 3 else "best"
    max_size_mb = float(sys.argv[4]) if len(sys.argv) > 4 else None

    # Sprawdź czy plik już istnieje
    if os.path.exists(output_file):
        response = input(f"Plik '{output_file}' już istnieje. Nadpisać? (t/n): ")
        if response.lower() not in ['t', 'tak', 'y', 'yes']:
            print("Anulowano.")
            sys.exit(0)

    # Pobierz
    success = download_stream(url, output_file, quality, max_size_mb)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
