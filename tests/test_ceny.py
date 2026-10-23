from decimal import Decimal

import pytest

from monitor_cen.ceny import parsuj_kwote, rozpoznaj_walute, znajdz_cene


@pytest.mark.parametrize("tekst, oczekiwana", [
    ("49,99 zł", "49.99"),
    ("1 299,99 zł", "1299.99"),
    ("1 299,00 PLN", "1299.00"),
    ("£51.77", "51.77"),
    ("$1,299.99", "1299.99"),
    ("1.299,99 €", "1299.99"),
    ("1.299 zł", "1299"),
    ("Cena: 15 zł", "15"),
])
def test_parsuj_kwote(tekst, oczekiwana):
    assert parsuj_kwote(tekst) == Decimal(oczekiwana)


def test_parsuj_kwote_bez_liczby():
    assert parsuj_kwote("Brak w magazynie") is None


def test_rozpoznaj_walute():
    assert rozpoznaj_walute("49,99 zł") == "PLN"
    assert rozpoznaj_walute("£51.77") == "GBP"
    assert rozpoznaj_walute("49.99") is None


def test_cena_z_selektora():
    html = '<p class="price_color">£51.77</p><p class="price_color">£1.00</p>'
    cena = znajdz_cene(html, "p.price_color")
    assert (cena.kwota, cena.waluta, cena.zrodlo) == (Decimal("51.77"), "GBP", "selektor")


def test_cena_z_json_ld():
    html = """<script type="application/ld+json">
      {"@context": "https://schema.org", "@type": "Product", "name": "Kubek",
       "offers": {"@type": "Offer", "price": "49.00", "priceCurrency": "PLN"}}
    </script>"""
    cena = znajdz_cene(html)
    assert (cena.kwota, cena.waluta, cena.zrodlo) == (Decimal("49.00"), "PLN", "json-ld")


def test_cena_z_json_ld_w_grafie_i_liscie_ofert():
    html = """<script type="application/ld+json">
      {"@graph": [{"@type": "WebPage"},
                  {"@type": ["Product"], "offers": [{"@type": "AggregateOffer", "lowPrice": 19.5, "priceCurrency": "EUR"}]}]}
    </script>"""
    assert znajdz_cene(html).kwota == Decimal("19.5")


def test_cena_z_meta():
    html = """<meta property="product:price:amount" content="129.00">
              <meta property="product:price:currency" content="PLN">"""
    cena = znajdz_cene(html)
    assert (cena.kwota, cena.waluta, cena.zrodlo) == (Decimal("129.00"), "PLN", "meta")


def test_cena_z_mikrodanych():
    html = '<span itemprop="price" content="89.90">89,90 zł</span><meta itemprop="priceCurrency" content="PLN">'
    cena = znajdz_cene(html)
    assert (cena.kwota, cena.waluta) == (Decimal("89.90"), "PLN")


def test_brak_ceny():
    assert znajdz_cene("<html><body>Witaj</body></html>") is None
    assert znajdz_cene("<p>nic</p>", "p.price_color") is None
