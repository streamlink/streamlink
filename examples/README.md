# Przykłady użycia Streamlink jako modułu Python

Ten katalog zawiera praktyczne przykłady pokazujące jak używać Streamlink jako biblioteki Python w swoich aplikacjach.

## Lista przykładów

### 01_basic_usage.py
**Podstawowe użycie**

Najprostszy sposób na rozpoczęcie pracy ze Streamlink. Pokazuje jak:
- Pobrać listę dostępnych strumieni z URL
- Wybrać strumień w określonej jakości
- Otworzyć i odczytać dane ze strumienia

```bash
python 01_basic_usage.py
```

### 02_download_to_file.py
**Pobieranie strumienia do pliku**

Pokazuje jak zapisać cały strumień do pliku lokalnego. Funkcje:
- Pobieranie z postępem (progress indicator)
- Limit rozmiaru pobierania
- Obsługa różnych jakości
- Sprawdzanie czy plik już istnieje

```bash
python 02_download_to_file.py <URL> <plik_wyjściowy> [jakość] [max_MB]

# Przykłady:
python 02_download_to_file.py "https://example.com/stream" output.mp4
python 02_download_to_file.py "https://example.com/stream" output.mp4 720p
python 02_download_to_file.py "https://example.com/stream" output.mp4 best 100
```

### 03_session_configuration.py
**Konfiguracja sesji**

Kompleksowy przewodnik po wszystkich opcjach konfiguracyjnych. Pokazuje jak ustawić:
- Niestandardowe nagłówki HTTP
- Proxy (HTTP, HTTPS, SOCKS)
- Cookies i uwierzytelnianie
- SSL/TLS opcje
- Opcje strumieni (timeouty, wątki)
- Opcje HLS i DASH
- Opcje specyficzne dla pluginów
- Logowanie i debugging

```bash
python 03_session_configuration.py
```

### 04_stream_information.py
**Informacje o strumieniach**

Narzędzie do analizy dostępnych strumieni. Wyświetla:
- Informacje o pluginie obsługującym URL
- Listę wszystkich dostępnych jakości
- Typy strumieni (HTTP, HLS, DASH, itp.)
- URLe strumieni i manifestów
- Grupowanie według typu
- Test otwarcia strumienia
- Rekomendacje jakości

```bash
python 04_stream_information.py <URL>

# Przykład:
python 04_stream_information.py "https://www.youtube.com/watch?v=..."
```

### 05_custom_plugin.py
**Tworzenie własnych pluginów**

Zaawansowany przykład pokazujący jak tworzyć własne pluginy. Zawiera:
- Podstawowy plugin z dopasowaniem URL (regex)
- Plugin z opcjami konfiguracyjnymi
- Plugin z API i uwierzytelnianiem
- Obsługa różnych typów strumieni
- Rejestracja i użycie własnych pluginów

```bash
python 05_custom_plugin.py
```

## Wymagania

Wszystkie przykłady wymagają zainstalowanego Streamlink:

```bash
# Instalacja z PyPI
pip install streamlink

# Lub instalacja z repozytorium (tryb deweloperski)
pip install -e .
```

## Dodatkowe zasoby

- **Przewodnik modułu**: `../PRZEWODNIK_MODULU.md` - Kompletny przewodnik użycia
- **Dokumentacja API**: `../DOKUMENTACJA_API.md` - Szczegółowa dokumentacja wszystkich funkcji
- **Oficjalna dokumentacja**: https://streamlink.github.io/
- **GitHub**: https://github.com/streamlink/streamlink

## Uwagi

1. **Przykłady 01-04** działają z prawdziwymi URLami, ale mogą wymagać działającego połączenia internetowego i dostępu do serwisów streamingowych.

2. **Przykład 05** (custom plugin) używa fikcyjnych URLi do demonstracji - nie będzie działał z prawdziwymi serwisami bez modyfikacji.

3. Niektóre serwisy mogą wymagać:
   - Uwierzytelnienia (cookies, tokeny)
   - Niestandardowych nagłówków HTTP
   - Specyficznych opcji pluginów

4. Pamiętaj o przestrzeganiu warunków użytkowania serwisów, z których pobierasz strumienie.

## Licencja

Przykłady są częścią projektu Streamlink i dostępne na tej samej licencji BSD 2-Clause.
