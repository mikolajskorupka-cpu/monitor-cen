"""Odczytywanie ceny ze strony produktu.

Sklepy zapisują cenę na różne sposoby, więc próbujemy po kolei:
1. selektor CSS podany ręcznie dla danego produktu (najpewniejsze),
2. dane strukturalne schema.org (JSON-LD) - ma je większość nowoczesnych sklepów,
3. znaczniki meta product:price:amount / og:price:amount (Facebook, Shopify),
4. mikrodane itemprop="price".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup

WALUTY = {
    "zł": "PLN", "pln": "PLN", "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP", "$": "USD", "usd": "USD",
}
WZOR_KWOTY = re.compile(r"\d[\d\s .,]*")


@dataclass
class Cena:
    kwota: Decimal
    waluta: str | None
    zrodlo: str  # skąd wzięliśmy cenę - przydaje się przy szukaniu błędów


def parsuj_kwote(tekst: str) -> Decimal | None:
    """Zamienia tekst typu '1 299,99 zł', '£51.77' albo '1,299.99' na liczbę."""
    dopasowanie = WZOR_KWOTY.search(tekst)
    if not dopasowanie:
        return None
    s = re.sub(r"[\s ]", "", dopasowanie.group()).rstrip(".,")
    if "," in s and "." in s:
        # Separatorem dziesiętnym jest ten znak, który występuje później.
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # '49,99' -> przecinek dziesiętny; '1,299' -> separator tysięcy
        s = s.replace(",", ".") if len(s.rsplit(",", 1)[1]) <= 2 else s.replace(",", "")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.rsplit(".", 1)[1]) == 3):
        s = s.replace(".", "")  # '1.299' -> 1299
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def rozpoznaj_walute(tekst: str) -> str | None:
    tekst = tekst.lower()
    for znak, kod in WALUTY.items():
        if znak in tekst:
            return kod
    return None


def _z_selektora(soup: BeautifulSoup, selektor: str) -> Cena | None:
    el = soup.select_one(selektor)
    if el is None:
        return None
    tekst = el.get("content") or el.get_text(" ", strip=True)
    kwota = parsuj_kwote(tekst)
    return Cena(kwota, rozpoznaj_walute(tekst), "selektor") if kwota is not None else None


def _z_json_ld(soup: BeautifulSoup) -> Cena | None:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            dane = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        obiekty = dane if isinstance(dane, list) else dane.get("@graph", [dane])
        for obiekt in obiekty:
            if not isinstance(obiekt, dict):
                continue
            typ = obiekt.get("@type")
            if "Product" not in (typ if isinstance(typ, list) else [typ]):
                continue
            oferty = obiekt.get("offers")
            for oferta in oferty if isinstance(oferty, list) else [oferty]:
                if not isinstance(oferta, dict):
                    continue
                cena = oferta.get("price", oferta.get("lowPrice"))
                if cena is None:
                    continue
                kwota = parsuj_kwote(str(cena))
                if kwota is not None:
                    return Cena(kwota, oferta.get("priceCurrency"), "json-ld")
    return None


def _z_meta(soup: BeautifulSoup) -> Cena | None:
    for prefiks in ("product", "og"):
        kwota_tag = soup.find("meta", property=f"{prefiks}:price:amount")
        if kwota_tag and (kwota := parsuj_kwote(kwota_tag.get("content", ""))) is not None:
            waluta_tag = soup.find("meta", property=f"{prefiks}:price:currency")
            return Cena(kwota, waluta_tag.get("content") if waluta_tag else None, "meta")
    return None


def _z_mikrodanych(soup: BeautifulSoup) -> Cena | None:
    el = soup.find(attrs={"itemprop": "price"})
    if el is None:
        return None
    kwota = parsuj_kwote(el.get("content") or el.get_text(" ", strip=True))
    if kwota is None:
        return None
    waluta_el = soup.find(attrs={"itemprop": "priceCurrency"})
    return Cena(kwota, waluta_el.get("content") if waluta_el else None, "mikrodane")


def znajdz_cene(html: str, selektor: str | None = None) -> Cena | None:
    soup = BeautifulSoup(html, "html.parser")
    if selektor:
        return _z_selektora(soup, selektor)
    return _z_json_ld(soup) or _z_meta(soup) or _z_mikrodanych(soup)
