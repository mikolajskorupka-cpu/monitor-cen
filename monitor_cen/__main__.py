"""Uruchamianie z terminala:  python -m monitor_cen"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

from . import __version__
from .alerty import tresc_alertu, wykryj_zmiany, wyslij
from .ceny import znajdz_cene
from .historia import Pomiar, dopisz, ostatnie_ceny, wczytaj
from .raport import render_html

USER_AGENT = f"MonitorCen/{__version__} (+https://github.com/mikolajskorupka-cpu/monitor-cen)"


def wczytaj_env(sciezka: str = ".env") -> None:
    """Wczytuje sekrety z pliku .env do zmiennych środowiskowych (jeśli plik istnieje)."""
    if not os.path.exists(sciezka):
        return
    with open(sciezka, encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if linia and not linia.startswith("#") and "=" in linia:
                klucz, wartosc = linia.split("=", 1)
                os.environ.setdefault(klucz.strip(), wartosc.strip())


def sprawdz_produkty(produkty: list[dict], przerwa: float) -> tuple[list[Pomiar], list[str]]:
    sesja = requests.Session()
    sesja.headers["User-Agent"] = USER_AGENT
    teraz = datetime.now(timezone.utc)
    pomiary, bledy = [], []
    for produkt in produkty:
        nazwa, url = produkt["nazwa"], produkt["url"]
        try:
            odp = sesja.get(url, timeout=20)
            odp.raise_for_status()
        except requests.RequestException as e:
            bledy.append(f"{nazwa}: błąd pobierania ({e.__class__.__name__})")
            print(f"  ✗ {nazwa}: błąd pobierania")
            continue
        cena = znajdz_cene(odp.text, produkt.get("selektor"))
        if cena is None:
            bledy.append(f"{nazwa}: nie znaleziono ceny na stronie")
            print(f"  ✗ {nazwa}: nie znaleziono ceny")
        else:
            waluta = produkt.get("waluta") or cena.waluta
            pomiary.append(Pomiar(teraz, nazwa, url, cena.kwota, waluta))
            print(f"  ✓ {nazwa}: {cena.kwota} {waluta or ''} ({cena.zrodlo})")
        time.sleep(przerwa)
    return pomiary, bledy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="monitor_cen", description="Sprawdza ceny produktów konkurencji.")
    parser.add_argument("--produkty", default="produkty.json", help="lista produktów do śledzenia")
    parser.add_argument("--historia", default="dane/historia.csv", help="plik z historią cen")
    parser.add_argument("--raport", default="docs/index.html", help="gdzie zapisać stronę z raportem")
    parser.add_argument("--przerwa", type=float, default=2.0, help="przerwa między zapytaniami (s)")
    parser.add_argument("--bez-alertow", action="store_true", help="nie wysyłaj powiadomień")
    args = parser.parse_args(argv)

    wczytaj_env()
    with open(args.produkty, encoding="utf-8") as f:
        produkty = json.load(f)

    print(f"Sprawdzam {len(produkty)} produktów…")
    poprzednie = ostatnie_ceny(wczytaj(args.historia))
    nowe, bledy = sprawdz_produkty(produkty, args.przerwa)
    dopisz(args.historia, nowe)

    zmiany = wykryj_zmiany(poprzednie, nowe)
    print(f"\nZmian cen: {len(zmiany)}, błędów: {len(bledy)}")
    for z in zmiany:
        print("  " + z.opis().replace("\n", "  "))

    if (zmiany or bledy) and not args.bez_alertow:
        kanaly = wyslij(tresc_alertu(zmiany, bledy))
        print(f"Alert wysłany: {', '.join(kanaly)}" if kanaly else "Alerty nie są skonfigurowane (zob. .env.przyklad).")

    os.makedirs(os.path.dirname(args.raport) or ".", exist_ok=True)
    with open(args.raport, "w", encoding="utf-8") as f:
        f.write(render_html(wczytaj(args.historia), bledy, datetime.now(timezone.utc)))
    print(f"Raport: {args.raport}")
    return 0 if nowe else 1


if __name__ == "__main__":
    sys.exit(main())
