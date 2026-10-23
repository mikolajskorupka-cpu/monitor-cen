from datetime import datetime, timedelta, timezone
from decimal import Decimal

from monitor_cen.alerty import tresc_alertu, wykryj_zmiany
from monitor_cen.historia import Pomiar, dopisz, ostatnie_ceny, wczytaj
from monitor_cen.raport import render_html, wykres_svg

T0 = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)


def pomiar(dzien: int, cena: str, url: str = "https://sklep.pl/kubek", produkt: str = "Kubek") -> Pomiar:
    return Pomiar(T0 + timedelta(days=dzien), produkt, url, Decimal(cena), "PLN")


def test_historia_zapis_i_odczyt(tmp_path):
    plik = str(tmp_path / "dane" / "historia.csv")
    dopisz(plik, [pomiar(0, "49.99")])
    dopisz(plik, [pomiar(1, "44.99")])  # drugi zapis dopisuje, nie nadpisuje
    wczytane = wczytaj(plik)
    assert [p.cena for p in wczytane] == [Decimal("49.99"), Decimal("44.99")]
    assert wczytane[0].czas == T0


def test_wczytaj_plik_z_bom_po_edycji_w_excelu(tmp_path):
    plik = tmp_path / "historia.csv"
    plik.write_text("﻿czas,produkt,url,cena,waluta\n2026-10-01T06:00:00+00:00,Kubek,https://sklep.pl/kubek,49.99,PLN\n",
                    encoding="utf-8")
    assert wczytaj(str(plik))[0].cena == Decimal("49.99")


def test_wczytaj_nieistniejacy_plik(tmp_path):
    assert wczytaj(str(tmp_path / "brak.csv")) == []


def test_ostatnie_ceny_bierze_najnowszy_pomiar():
    ostatnie = ostatnie_ceny([pomiar(2, "40"), pomiar(0, "50"), pomiar(1, "45")])
    assert ostatnie["https://sklep.pl/kubek"].cena == Decimal("40")


def test_wykryj_zmiany():
    poprzednie = ostatnie_ceny([pomiar(0, "50.00"), pomiar(0, "10.00", url="https://sklep.pl/talerz")])
    nowe = [pomiar(1, "45.00"), pomiar(1, "10.00", url="https://sklep.pl/talerz"),
            pomiar(1, "99.00", url="https://sklep.pl/nowy")]  # nowy produkt to nie zmiana
    zmiany = wykryj_zmiany(poprzednie, nowe)
    assert len(zmiany) == 1
    assert zmiany[0].procent == -10.0
    assert "obniżka" in zmiany[0].opis()


def test_tresc_alertu_z_bledami():
    zmiany = wykryj_zmiany(ostatnie_ceny([pomiar(0, "40")]), [pomiar(1, "50")])
    tresc = tresc_alertu(zmiany, ["Talerz: nie znaleziono ceny na stronie"])
    assert "podwyżka" in tresc and "+25.0%" in tresc
    assert "Talerz: nie znaleziono ceny" in tresc


def test_raport_pokazuje_ostatnia_zmiane():
    historia = [pomiar(0, "50.00"), pomiar(1, "45.00"), pomiar(2, "45.00")]
    html = render_html(historia, bledy=[], teraz=T0)
    assert "45.00 PLN" in html
    assert "-10.0%" in html and "było 50.00 PLN" in html
    assert "<svg" in html


def test_raport_koduje_nazwy_i_pokazuje_bledy():
    html = render_html([pomiar(0, "10", produkt="<b>Kubek</b>")], bledy=["Talerz: błąd"], teraz=T0)
    assert "&lt;b&gt;Kubek&lt;/b&gt;" in html
    assert "Nie udało się sprawdzić" in html


def test_wykres_za_malo_danych():
    assert "za mało danych" in wykres_svg([Decimal("1")])
