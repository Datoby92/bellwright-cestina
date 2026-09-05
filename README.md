# Čeština pro Bellwright

Fanouškovský český překlad hry **Bellwright** (Donkey Crew, Unreal Engine 5).
Překlad zařídil [TheraWoW.com](https://therawow.com).

**Stav: 100 % textů přeloženo** (28 880 řetězců) · verze 1.0 · Steam build 24840601

---

## Pro hráče – stažení a instalace

1. Stáhni nejnovější ZIP ze stránky **[Releases](../../releases/latest)**.
2. Rozbal ho a spusť `Instalovat.bat` – instalátor sám najde hru ve Steam knihovně,
   nakopíruje češtinu a přepne jazyk hry.
3. Spusť hru. Hotovo.

Odebrání: `Odinstalovat.bat`. Ruční instalace a odpovědi na časté dotazy jsou v `NAVOD.txt` v ZIPu.

Do složky hry se pouze **přidává** složka `Content/Localization/Game/cs`; nic původního se nepřepisuje.
Po aktualizaci hry zůstanou nové texty anglicky, dokud nevyjde nová verze překladu – nic se nerozbije.

**Našel jsi chybu?** Založ [Issue](../../issues) se screenshotem a napiš, co bylo v textu anglicky.

---

## Pro překladatele – jak to funguje


Veškerý text hry je v jednom souboru `Game.locres`. Hra ho hledá podle
nastaveného jazyka ve složce `Content/Localization/Game/<jazyk>/`.

```
source/en/Game.locres      anglický originál z hry (28 880 řetězců) — nikdy se needituje
        │
        ├─ export ─────────► cestina.po        pracovní soubor s překladem
        │                         ▲
        │                    apply│ bysource
        │                         │
        │                    translations/*.tsv   ← tady se překládá
        │
        └─ build ──────────► build/cs/Game.locres → nakopírovat do hry
```

`build` vezme původní anglický soubor, vymění jen přeložené řetězce a zbytek
nechá být. Proto je výsledek vždy platný, ať je hotovo 5 % nebo 100 %.

---

## Instalace do hry

```bash
python tools/bwloc.py build cestina.po -l source/en/Game.locres -o build/cs/Game.locres -g glossary.tsv
```

Pak zkopírovat `build/cs/Game.locres` do:

```
D:\SteamLibrary\steamapps\common\Bellwright\Bellwright\Content\Localization\Game\cs\Game.locres
```

A v `%LOCALAPPDATA%\Bellwright\Saved\Config\Windows\GameUserSettings.ini` mít:

```ini
[Internationalization]
Culture=cs
```

Záloha původního nastavení je vedle jako `GameUserSettings.ini.pred-cestinou.bak`.
Návrat k angličtině = přepsat `cs` zpět na `en`.

> Do složky hry se pouze **přidává** nová složka `cs`. Nic původního se nepřepisuje,
> takže ověření souborů přes Steam češtinu jen smaže, nic nerozbije.

---

## Práce na překladu

```bash
# co ještě zbývá, seřazené abecedně (stejné texty pohromadě)
python tools/dump.py --unmapped --words --unique --max-len 58 --take 400

# vložit hotovou dávku
python tools/bwloc.py bysource cestina.po translations/obsah-06.tsv

# kontrola kvality
python tools/bwloc.py check cestina.po -g glossary.tsv
python tools/bwloc.py homographs cestina.po      # víceznačná slova
python tools/bwloc.py stats cestina.po           # kolik je hotovo
```

### Dva způsoby, jak zapsat překlad

| soubor | formát | kdy |
|---|---|---|
| `bysource` | `anglicky <TAB> česky` | běžně — jeden řádek pokryje všechny výskyty |
| `apply` | `namespace <TAB> klíč <TAB> česky` | když stejný originál potřebuje v různých místech různý překlad |

`bysource` nikdy nepřepíše překlad zapsaný přes `apply`, takže se dá kombinovat.

---

## Pravidla překladu

- **Tykání** hráči. Kde existuje dobové české slovo (lapka, dýmačka,
  prošívanice, věhlas), má přednost před kalkem z angličtiny.
- **Řeč postav smí být šťavnatá.** Angličtina je v dialozích plochá, čeština to
  nemusí kopírovat: „Get lost.“ → „Kliď se mi z očí.“, „Ah, a customer!“ →
  „Á, zákazník! Čímpak posloužím?“. Barvitost patří hlavně lapkům, hospodským
  a kupcům. Přechodníky a knižní tvary ale ne — má to znít starosvětsky, ne
  jako čítanka.
- **Rozhraní zůstává věcné** — „Uložit hru“, ne stylizace. Rozdíl mezi mluvou
  postav a popisky rozhraní je záměrný.
- **Nejčastější repliky mají přednost.** Některé věty hráč slyší stokrát
  („Anything else?“ 127×, „Is there anything I could help you with?“ 55×) —
  u těch se vyplatí hledat dobré znění, u jednorázových stačí věcné.
- **Vlastní jména** osob, vsí a hospod se nepřekládají (Bradford, Andrea,
  + The Donkey's Sack +). Svět hry je anglický a nápisy v prostředí zůstávají.
  Kde je jméno součástí názvu, skloňuje se: „Chýše Alekse Amanity“.
- **Značky** `{Count}`, `<item>…</>` musí zůstat přesně. Hlídá to kontrola.
- **Slovníček** `glossary.tsv` drží jednotné pojmy. Pozdější řádek přebíjí dřívější.

### Ustálené pojmy

| anglicky | česky | | anglicky | česky |
|---|---|---|---|---|
| bandit | lapka | | brigand | lupič |
| settlement | osada | | village | ves |
| renown | věhlas | | trust | důvěra |
| bloomery | dýmačka | | gambeson | prošívanice |
| armourer | platnéř | | toolmaker | nástrojař |
| research | bádání | | harvesting | sběr |

---

## Kontroly kvality

`check` hlásí ve třech úrovních; **error** blokuje zabalení řetězce, aby se do hry
nikdy nedostal rozbitý text.

| kontrola | co hlídá |
|---|---|
| placeholder | proměnné `{…}` musí souhlasit se zdrojem |
| plural | čeština potřebuje tvary one/few/other, angličtina jen one/other |
| richtext | značky `<item>…</>` musí souhlasit |
| inconsistent | jeden originál přeložený víc způsoby |
| collision | jeden překlad použitý na víc různých originálů |
| glossary | odchylka od slovníčku |

### Víceznačná slova

`homographs` vypisuje řetězce, kde angličtina používá slovo se dvěma významy —
strojový překlad si tam pravidelně vybere špatně a **výsledek přitom vypadá
jako správná česká věta**, takže si toho jinak nikdo nevšimne.

Příklad z tohohle projektu: `Extra game yield` neznamená „výnos ze hry“,
ale **„výnos zvěřiny“**. Podobně `hide` je jednou „kůže“ a jindy „skrýt“.

Automaticky se to ověřit nedá, proto to nástroj jen předloží ke kontrole.

---

## Nástroje

| soubor | k čemu |
|---|---|
| `tools/pylocres.py` | čtení a zápis `.locres` (ověřeno bajt po bajtu) |
| `tools/po.py` | formát `.po` |
| `tools/qa.py` | kontroly kvality a seznam víceznačných slov |
| `tools/bwloc.py` | hlavní příkazy |
| `tools/dump.py` | výběr dávky k překladu |
| `tools/test_locres.py` | test, že zápis `.locres` odpovídá originálu |

Anglický `Game.locres` se z hry vytáhl nástrojem
[UEExtractor](https://github.com/SolicenTEAM/UEExtractor) (v `tools/UEExtractor/`).
Znovu je potřeba jen tehdy, když hra dostane aktualizaci.

---

## Po aktualizaci hry

```bash
# 1) vytáhnout nový anglický locres do source/en/Game.locres
# 2) přenést hotové překlady na nové texty
python tools/bwloc.py export source/en/Game.locres -o cestina.po --merge
```

`--merge` zachová hotové překlady. Řetězce, kterým se změnil anglický originál,
označí jako `fuzzy` — ty se do hry nezabalí, dokud je někdo neprojde.

---

## Stav

Sledovat příkazem `python tools/bwloc.py stats cestina.po`.

Hotové rozhraní: nabídky, nastavení, ovládání, batoh, stavění, úkolové texty,
oznámení, dovednosti, kodex, tvorba postavy. Rozpracovaný obsah: názvy a popisy
předmětů, zadání úkolů, dialogy.
