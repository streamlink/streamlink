#!/usr/bin/env python3
"""
Przykład 1: Podstawowe użycie Streamlink jako modułu

Pokazuje najprostszy sposób pobierania strumieni z URL.
"""

import streamlink

def main():
    # URL do przetestowania (zmień na prawdziwy URL)
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    print(f"Pobieranie strumieni z: {url}\n")

    try:
        # Pobierz dostępne strumienie
        streams = streamlink.streams(url)

        if not streams:
            print("Brak dostępnych strumieni dla tego URL")
            return

        # Wyświetl wszystkie dostępne jakości
        print("Dostępne strumienie:")
        for quality, stream in streams.items():
            print(f"  - {quality}: {type(stream).__name__}")

        # Wybierz strumień w najlepszej jakości
        if "best" in streams:
            stream = streams["best"]
            print(f"\nWybrano strumień: best")
            print(f"Typ strumienia: {type(stream).__name__}")

            # Otwórz strumień i odczytaj pierwsze 1024 bajty
            print("\nOtwieranie strumienia...")
            with stream.open() as fd:
                data = fd.read(1024)
                print(f"✓ Pomyślnie odczytano {len(data)} bajtów danych")

                # Wyświetl pierwsze kilka bajtów (hex)
                hex_preview = ' '.join(f'{b:02x}' for b in data[:16])
                print(f"Podgląd danych (pierwsze 16 bajtów): {hex_preview}")

    except streamlink.NoPluginError:
        print(f"✗ Brak pluginu obsługującego URL: {url}")
    except streamlink.PluginError as err:
        print(f"✗ Błąd pluginu: {err}")
    except streamlink.StreamError as err:
        print(f"✗ Błąd strumienia: {err}")
    except Exception as err:
        print(f"✗ Nieoczekiwany błąd: {err}")

if __name__ == "__main__":
    main()
