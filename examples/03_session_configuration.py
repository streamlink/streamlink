#!/usr/bin/env python3
"""
Przykład 3: Konfiguracja sesji Streamlink

Pokazuje jak konfigurować sesję z opcjami HTTP, proxy, cookies, itp.
"""

import streamlink
import logging

def example_basic_configuration():
    """Podstawowa konfiguracja sesji"""
    print("=== Podstawowa konfiguracja ===\n")

    session = streamlink.Streamlink()

    # Ustaw timeout
    session.set_option("http-timeout", 30.0)
    print(f"HTTP timeout: {session.get_option('http-timeout')}s")

    # Ustaw niestandardowe nagłówki
    session.set_option("http-headers", {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://example.com"
    })
    print("Nagłówki HTTP: ustawione")

    # Ustaw cookies
    session.set_option("http-cookies", {
        "session_id": "abc123",
        "preferences": "quality=high"
    })
    print("Cookies: ustawione")

    return session

def example_proxy_configuration():
    """Konfiguracja proxy"""
    print("\n=== Konfiguracja Proxy ===\n")

    session = streamlink.Streamlink()

    # HTTP proxy
    session.set_option("http-proxy", "http://proxy.example.com:8080")
    print("HTTP proxy: http://proxy.example.com:8080")

    # HTTPS proxy (może być inny niż HTTP)
    session.set_option("https-proxy", "https://proxy.example.com:8443")
    print("HTTPS proxy: https://proxy.example.com:8443")

    # Proxy z uwierzytelnieniem
    session.set_option("http-proxy", "http://user:pass@proxy.example.com:8080")
    print("Proxy z uwierzytelnieniem: ustawione")

    # SOCKS proxy
    session.set_option("http-proxy", "socks5://localhost:1080")
    print("SOCKS proxy: socks5://localhost:1080")

    return session

def example_ssl_configuration():
    """Konfiguracja SSL/TLS"""
    print("\n=== Konfiguracja SSL/TLS ===\n")

    session = streamlink.Streamlink()

    # Weryfikacja SSL (domyślnie włączona)
    session.set_option("http-ssl-verify", True)
    print("Weryfikacja SSL: włączona")

    # Wyłączenie weryfikacji SSL (NIEZALECANE w produkcji!)
    # session.set_option("http-ssl-verify", False)
    # print("⚠ Weryfikacja SSL: wyłączona")

    # Użycie niestandardowego certyfikatu CA
    # session.set_option("http-ssl-cert", "/path/to/cert.pem")
    # print("Certyfikat CA: /path/to/cert.pem")

    return session

def example_stream_options():
    """Konfiguracja opcji strumieni"""
    print("\n=== Opcje strumieni ===\n")

    session = streamlink.Streamlink()

    # Timeout dla strumienia
    session.set_option("stream-timeout", 60.0)
    print("Stream timeout: 60s")

    # Timeout dla segmentów
    session.set_option("stream-segment-timeout", 10.0)
    print("Segment timeout: 10s")

    # Liczba wątków dla pobierania segmentów
    session.set_option("stream-segment-threads", 2)
    print("Wątki segmentów: 2")

    # Liczba prób pobrania segmentu
    session.set_option("stream-segment-attempts", 3)
    print("Próby pobrania segmentu: 3")

    return session

def example_hls_options():
    """Konfiguracja opcji HLS"""
    print("\n=== Opcje HLS ===\n")

    session = streamlink.Streamlink()

    # Ile segmentów od końca playlisty live startować
    session.set_option("hls-live-edge", 3)
    print("HLS live edge: 3 segmenty")

    # Strumieniowanie danych segmentów
    session.set_option("hls-segment-stream-data", True)
    print("HLS segment streaming: włączone")

    # Próby przeładowania playlisty
    session.set_option("hls-playlist-reload-attempts", 3)
    print("HLS playlist reload attempts: 3")

    # Restart streamów live od początku
    session.set_option("hls-live-restart", False)
    print("HLS live restart: wyłączone")

    return session

def example_plugin_options():
    """Konfiguracja opcji pluginów"""
    print("\n=== Opcje pluginów ===\n")

    session = streamlink.Streamlink()

    # Opcje specyficzne dla pluginu Twitch (przykład)
    session.set_plugin_option("twitch", "disable-ads", True)
    print("Twitch: disable-ads = True")

    session.set_plugin_option("twitch", "low-latency", True)
    print("Twitch: low-latency = True")

    # Opcje dla innych pluginów można ustawiać podobnie
    # session.set_plugin_option("youtube", "api-key", "your-key")

    return session

def example_logging():
    """Konfiguracja logowania"""
    print("\n=== Konfiguracja logowania ===\n")

    # Włącz logowanie na poziomie DEBUG
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    print("Logowanie włączone na poziomie DEBUG")

    # Lub bardziej szczegółowo dla konkretnych modułów
    streamlink_logger = logging.getLogger("streamlink")
    streamlink_logger.setLevel(logging.INFO)

    print("Logger Streamlink ustawiony na INFO")

def example_complete_configuration():
    """Kompletny przykład konfiguracji"""
    print("\n=== Kompletna konfiguracja ===\n")

    # Utwórz sesję
    session = streamlink.Streamlink()

    # HTTP opcje
    session.set_option("http-timeout", 30.0)
    session.set_option("http-headers", {
        "User-Agent": "Mozilla/5.0 Custom Stream Downloader",
        "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8"
    })

    # Proxy (jeśli potrzebne)
    # session.set_option("http-proxy", "http://proxy:8080")

    # Stream opcje
    session.set_option("stream-segment-threads", 2)
    session.set_option("stream-segment-attempts", 3)
    session.set_option("stream-timeout", 60.0)

    # HLS opcje
    session.set_option("hls-live-edge", 3)
    session.set_option("hls-segment-stream-data", True)

    print("✓ Sesja w pełni skonfigurowana")
    print("\nAktualne opcje:")
    print(f"  HTTP timeout: {session.get_option('http-timeout')}s")
    print(f"  Stream timeout: {session.get_option('stream-timeout')}s")
    print(f"  Segment threads: {session.get_option('stream-segment-threads')}")
    print(f"  HLS live edge: {session.get_option('hls-live-edge')}")

    # Przykładowe użycie
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    try:
        print(f"\nTestowanie konfiguracji z URL: {url}")
        streams = session.streams(url)

        if streams:
            print(f"✓ Znaleziono {len(streams)} strumieni")
            print(f"  Dostępne: {', '.join(streams.keys())}")
        else:
            print("  Brak strumieni")

    except Exception as err:
        print(f"✗ Błąd: {err}")

    return session

def main():
    """Uruchom wszystkie przykłady"""
    print("=" * 60)
    print("Przykłady konfiguracji sesji Streamlink")
    print("=" * 60)

    example_basic_configuration()
    example_proxy_configuration()
    example_ssl_configuration()
    example_stream_options()
    example_hls_options()
    example_plugin_options()
    example_logging()
    example_complete_configuration()

    print("\n" + "=" * 60)
    print("✓ Wszystkie przykłady zakończone")
    print("=" * 60)

if __name__ == "__main__":
    main()
