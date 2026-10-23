"""Wykrywanie zmian cen i wysyłanie powiadomień (Discord, e-mail)."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from decimal import Decimal
from email.message import EmailMessage

import requests

from .historia import Pomiar


@dataclass
class Zmiana:
    produkt: str
    url: str
    stara: Decimal
    nowa: Decimal
    waluta: str | None

    @property
    def procent(self) -> float:
        return float((self.nowa - self.stara) / self.stara * 100) if self.stara else 0.0

    def opis(self) -> str:
        kierunek = "📉 obniżka" if self.nowa < self.stara else "📈 podwyżka"
        waluta = f" {self.waluta}" if self.waluta else ""
        return (f"{kierunek}: {self.produkt}: {self.stara}{waluta} → {self.nowa}{waluta} "
                f"({self.procent:+.1f}%)\n{self.url}")


def wykryj_zmiany(poprzednie: dict[str, Pomiar], nowe: list[Pomiar]) -> list[Zmiana]:
    zmiany = []
    for p in nowe:
        stary = poprzednie.get(p.url)
        if stary is not None and stary.cena != p.cena:
            zmiany.append(Zmiana(p.produkt, p.url, stary.cena, p.cena, p.waluta))
    return zmiany


def tresc_alertu(zmiany: list[Zmiana], bledy: list[str]) -> str:
    linie = []
    if zmiany:
        linie.append(f"Zmiany cen u konkurencji ({len(zmiany)}):")
        linie += [z.opis() for z in zmiany]
    if bledy:
        linie.append(f"\n⚠️ Nie udało się sprawdzić ({len(bledy)}) - możliwe, że sklep zmienił stronę:")
        linie += [f"- {b}" for b in bledy]
    return "\n".join(linie)


def wyslij_discord(tresc: str, webhook: str) -> None:
    # Discord przyjmuje maks. 2000 znaków w jednej wiadomości.
    odp = requests.post(webhook, json={"content": tresc[:2000]}, timeout=15)
    odp.raise_for_status()


def wyslij_email(tresc: str) -> None:
    wiadomosc = EmailMessage()
    wiadomosc["Subject"] = "Monitor cen: zmiany u konkurencji"
    wiadomosc["From"] = os.environ["SMTP_USER"]
    wiadomosc["To"] = os.environ["ALERT_EMAIL_DO"]
    wiadomosc.set_content(tresc)
    port = int(os.environ.get("SMTP_PORT") or 465)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], port, timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_HASLO"])
        smtp.send_message(wiadomosc)


def wyslij(tresc: str) -> list[str]:
    """Wysyła alert wszystkimi skonfigurowanymi kanałami. Zwraca listę użytych kanałów."""
    kanaly = []
    if webhook := os.environ.get("DISCORD_WEBHOOK_URL"):
        wyslij_discord(tresc, webhook)
        kanaly.append("Discord")
    if os.environ.get("SMTP_HOST") and os.environ.get("ALERT_EMAIL_DO"):
        wyslij_email(tresc)
        kanaly.append("e-mail")
    return kanaly
