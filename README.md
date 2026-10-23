# Monitor cen konkurencji 📉📈

Automatyzacja dla sklepów internetowych: **codziennie sprawdza ceny produktów u konkurencji**, zapisuje ich historię i **wysyła alert** (Discord lub e-mail), gdy ktoś zmieni cenę.

Działa **sama, w chmurze, za darmo**: GitHub Actions uruchamia ją każdego ranka, a wyniki trafiają na stronę z wykresami.

👉 **[Zobacz działającą stronę z cenami](https://mikolajskorupka-cpu.github.io/monitor-cen/)**

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Testy](https://img.shields.io/badge/testy-pytest-green) ![GitHub Actions](https://img.shields.io/badge/uruchamianie-GitHub%20Actions-black)

## Problem biznesowy

Właściciel sklepu, który chce mieć konkurencyjne ceny, musi codziennie ręcznie zaglądać do kilku sklepów. Nikt tego nie robi regularnie, więc o obniżce u konkurencji dowiaduje się wtedy, gdy spada mu sprzedaż.

Monitor robi to automatycznie i daje znać tylko wtedy, gdy coś się zmieniło:

```
Zmiany cen u konkurencji (1):
📉 obniżka: Box of Chocolate Candy: 12.49 USD → 9.99 USD (-20.0%)
https://web-scraping.dev/product/1
```

## Jak to działa

```
produkty.json ──► pobranie stron ──► odczyt ceny ──► porównanie z historią ──► alert (Discord / e-mail)
                                                          │
                                                          ▼
                                              dane/historia.csv ──► docs/index.html (wykresy)
```

1. **Lista produktów** ([produkty.json](produkty.json)): nazwa, adres strony i opcjonalnie selektor CSS ceny.
2. **Odczyt ceny** ([ceny.py](monitor_cen/ceny.py)): program próbuje po kolei:
   - selektora CSS podanego dla produktu,
   - danych strukturalnych schema.org (JSON-LD), które ma większość sklepów na WooCommerce, Shopify, PrestaShop czy Shoperze,
   - znaczników `product:price:amount` / `og:price:amount`,
   - mikrodanych `itemprop="price"`.

   Rozumie różne formaty zapisu: `1 299,99 zł`, `£51.77`, `$1,299.99`, `1.299,99 €`.
3. **Historia** ([historia.py](monitor_cen/historia.py)): każdy pomiar trafia do pliku CSV. Da się go otworzyć w Excelu, a na GitHubie widać, kiedy zmieniła się cena.
4. **Alerty** ([alerty.py](monitor_cen/alerty.py)): porównanie z ostatnią znaną ceną. Alert dostajesz też wtedy, gdy ceny nie udało się odczytać, bo zwykle oznacza to, że sklep zmienił wygląd strony.
5. **Raport** ([raport.py](monitor_cen/raport.py)): strona HTML z aktualnymi cenami, ostatnią zmianą, zakresem cen i wykresem historii (czyste SVG, bez bibliotek).
6. **Harmonogram** ([.github/workflows/monitor.yml](.github/workflows/monitor.yml)): GitHub Actions uruchamia monitor codziennie o 6:00 UTC i zapisuje wyniki w repozytorium.

## Uruchomienie u siebie

Wymagany Python 3.10 lub nowszy.

```bash
git clone https://github.com/mikolajskorupka-cpu/monitor-cen.git
cd monitor-cen
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python -m monitor_cen
```

Swoje produkty dopisz do `produkty.json`:

```json
[
  { "nazwa": "Kubek 350 ml - konkurent A", "url": "https://sklep-a.pl/kubek-350" },
  { "nazwa": "Kubek 350 ml - konkurent B", "url": "https://sklep-b.pl/p/123", "selektor": ".product-price" }
]
```

`selektor` jest potrzebny tylko wtedy, gdy sklep nie ma danych schema.org. Znajdziesz go w przeglądarce: prawy klik na cenie → **Zbadaj**.

## Alerty

Skopiuj `.env.przyklad` jako `.env` i uzupełnij wybrany kanał:
- **Discord**: adres webhooka kanału (`DISCORD_WEBHOOK_URL`),
- **e-mail**: dane serwera poczty (`SMTP_*`, `ALERT_EMAIL_DO`).

Na GitHubie te same wartości wpisuje się jako **sekrety** (Settings → Secrets and variables → Actions), więc nikt ich nie zobaczy w kodzie.

## Testy

```bash
pip install -r requirements-dev.txt
python -m pytest
```

25 testów sprawdza odczyt cen z różnych formatów, zapis historii, wykrywanie zmian i raport. Testy nie łączą się z internetem.

## Plany rozwoju

- [ ] porównanie z cenami **własnego** sklepu („jesteś droższy o 12%”)
- [ ] śledzenie dostępności produktu (brak w magazynie u konkurencji = okazja)
- [ ] monitorowanie ofert na Allegro
- [ ] cotygodniowe podsumowanie rynku napisane przez AI (Claude)
