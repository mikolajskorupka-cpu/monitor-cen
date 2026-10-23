"""Historia cen zapisywana w pliku CSV.

CSV zamiast bazy danych, bo: da się go otworzyć w Excelu, a Git pokazuje
zmiany w nim linijka po linijce - widać na GitHubie, kiedy zmieniła się cena.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

KOLUMNY = ["czas", "produkt", "url", "cena", "waluta"]


@dataclass
class Pomiar:
    czas: datetime
    produkt: str
    url: str
    cena: Decimal
    waluta: str | None


def wczytaj(sciezka: str) -> list[Pomiar]:
    if not os.path.exists(sciezka):
        return []
    # utf-8-sig: toleruje znak BOM, który dodaje np. Excel albo Notatnik przy zapisie.
    with open(sciezka, newline="", encoding="utf-8-sig") as f:
        return [
            Pomiar(
                czas=datetime.fromisoformat(w["czas"]),
                produkt=w["produkt"],
                url=w["url"],
                cena=Decimal(w["cena"]),
                waluta=w["waluta"] or None,
            )
            for w in csv.DictReader(f)
        ]


def dopisz(sciezka: str, pomiary: list[Pomiar]) -> None:
    nowy_plik = not os.path.exists(sciezka)
    os.makedirs(os.path.dirname(sciezka) or ".", exist_ok=True)
    with open(sciezka, "a", newline="", encoding="utf-8") as f:
        pisarz = csv.DictWriter(f, fieldnames=KOLUMNY)
        if nowy_plik:
            pisarz.writeheader()
        for p in pomiary:
            pisarz.writerow({
                "czas": p.czas.isoformat(timespec="seconds"),
                "produkt": p.produkt,
                "url": p.url,
                "cena": str(p.cena),
                "waluta": p.waluta or "",
            })


def ostatnie_ceny(pomiary: list[Pomiar]) -> dict[str, Pomiar]:
    """Najnowszy pomiar każdego produktu (klucz: adres strony)."""
    ostatnie: dict[str, Pomiar] = {}
    for p in sorted(pomiary, key=lambda p: p.czas):
        ostatnie[p.url] = p
    return ostatnie
