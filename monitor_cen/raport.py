"""Strona HTML z aktualnymi cenami i wykresami historii (publikowana na GitHub Pages)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from html import escape

from .historia import Pomiar


def wykres_svg(ceny: list[Decimal], szer: int = 160, wys: int = 40) -> str:
    """Mały wykres liniowy (sparkline) narysowany w czystym SVG - bez bibliotek."""
    if len(ceny) < 2:
        return '<span class="brak">za mało danych</span>'
    lo, hi = min(ceny), max(ceny)
    zakres = (hi - lo) or Decimal(1)
    punkty = " ".join(
        f"{i * szer / (len(ceny) - 1):.1f},{wys - 4 - float((c - lo) / zakres) * (wys - 8):.1f}"
        for i, c in enumerate(ceny)
    )
    return (f'<svg viewBox="0 0 {szer} {wys}" width="{szer}" height="{wys}" role="img" '
            f'aria-label="historia ceny"><polyline points="{punkty}" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>')


def _cena(kwota: Decimal, waluta: str | None) -> str:
    return f"{kwota:.2f} {waluta or ''}".strip()


def render_html(pomiary: list[Pomiar], bledy: list[str], teraz: datetime) -> str:
    po_produkcie: dict[str, list[Pomiar]] = defaultdict(list)
    for p in sorted(pomiary, key=lambda p: p.czas):
        po_produkcie[p.url].append(p)

    wiersze = []
    for url, historia in po_produkcie.items():
        ostatni = historia[-1]
        ceny = [p.cena for p in historia]
        # Poprzednia *inna* cena - żeby pokazać ostatnią zmianę, a nie wczorajszy pomiar.
        poprzednia = next((c for c in reversed(ceny) if c != ostatni.cena), None)
        if poprzednia is None:
            zmiana = '<span class="brak">bez zmian</span>'
        else:
            procent = float((ostatni.cena - poprzednia) / poprzednia * 100)
            klasa = "spadek" if procent < 0 else "wzrost"
            zmiana = f'<span class="{klasa}">{procent:+.1f}%</span> <small>(było {_cena(poprzednia, ostatni.waluta)})</small>'
        wiersze.append(f"""
        <tr>
          <td><a href="{escape(url)}">{escape(ostatni.produkt)}</a></td>
          <td class="cena">{_cena(ostatni.cena, ostatni.waluta)}</td>
          <td>{zmiana}</td>
          <td>{_cena(min(ceny), ostatni.waluta)} – {_cena(max(ceny), ostatni.waluta)}</td>
          <td class="wykres">{wykres_svg(ceny)}</td>
        </tr>""")

    sekcja_bledow = ""
    if bledy:
        lista = "".join(f"<li>{escape(b)}</li>" for b in bledy)
        sekcja_bledow = f'<section class="bledy"><h2>Nie udało się sprawdzić</h2><ul>{lista}</ul></section>'

    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor cen konkurencji</title>
<style>
  :root {{ --tlo:#f6f7f9; --karta:#fff; --tekst:#1d2330; --szary:#667085; --linia:#eaecf0;
          --zielony:#079455; --czerwony:#d92d20; --akcent:#2e6bd0; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --tlo:#0f1218; --karta:#181c24; --tekst:#e6e8ec; --szary:#98a2b3; --linia:#2a303b;
            --zielony:#3ccb7f; --czerwony:#f97066; --akcent:#7aa7ff; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.5 system-ui, sans-serif; background:var(--tlo); color:var(--tekst); }}
  main {{ max-width:1000px; margin:0 auto; padding:32px 16px; }}
  h1 {{ margin:0 0 4px; }} .podtytul {{ color:var(--szary); margin:0 0 24px; }}
  .tabela {{ overflow-x:auto; background:var(--karta); border-radius:12px; box-shadow:0 1px 2px #0002; }}
  table {{ width:100%; border-collapse:collapse; }}
  th, td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--linia); vertical-align:middle; }}
  th {{ font-size:13px; color:var(--szary); font-weight:600; }}
  .cena {{ font-weight:700; white-space:nowrap; }}
  .spadek {{ color:var(--zielony); font-weight:700; }} .wzrost {{ color:var(--czerwony); font-weight:700; }}
  .brak, small {{ color:var(--szary); }}
  .wykres {{ color:var(--akcent); }}
  a {{ color:var(--akcent); }}
  .bledy {{ margin-top:24px; background:var(--karta); border-left:6px solid var(--czerwony);
           border-radius:12px; padding:8px 20px; }}
  footer {{ color:var(--szary); font-size:13px; margin-top:32px; }}
</style>
</head>
<body><main>
  <h1>Monitor cen konkurencji</h1>
  <p class="podtytul">Ostatnie sprawdzenie: {teraz:%Y-%m-%d %H:%M} UTC · produktów: {len(po_produkcie)} · pomiarów: {len(pomiary)}</p>
  <div class="tabela"><table>
    <thead><tr><th>Produkt</th><th>Cena</th><th>Ostatnia zmiana</th><th>Zakres</th><th>Historia</th></tr></thead>
    <tbody>{"".join(wiersze) or '<tr><td colspan="5">Brak pomiarów.</td></tr>'}</tbody>
  </table></div>
  {sekcja_bledow}
  <footer>Strona aktualizowana automatycznie codziennie przez GitHub Actions.</footer>
</main></body>
</html>
"""
