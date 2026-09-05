"""Sjednoceni terminologie napric cestina.po (viz audit 2026-09-05).

Nahrady jsou sklonovane a zachovavaji velke pocatecni pismeno.
Spusteni:  python tools/audit_terms.py [--apply]
Bez --apply jen vypise, co by se zmenilo.
"""
import re
import sys

sys.path.insert(0, 'tools')
import po

PO = 'cestina.po'

# (regex, nahrada) – vzdy s \b, aby se nechytaly "pracovní síla", "hospodář", "základní" apod.
RULES = [
    # Stockpile -> sklad
    (r'\bskládk(a|y|u|ou|ám|ách|ami)\b', {'a': 'sklad', 'y': 'skladu', 'u': 'sklad', 'ou': 'skladem', 'ám': 'skladům', 'ách': 'skladech', 'ami': 'sklady'}),
    (r'\bskládek\b', 'skladů'),
    # Staging Ground -> shromaždiště
    (r'\bnástupišt(ě|i|ěm)\b', {'ě': 'shromaždiště', 'i': 'shromaždišti', 'ěm': 'shromaždištěm'}),
    # Outpost -> základna
    (r'\bvýsp(a|y|ě|u|ou|ám|ách|ami)\b', {'a': 'základna', 'y': 'základny', 'ě': 'základně', 'u': 'základnu', 'ou': 'základnou', 'ám': 'základnám', 'ách': 'základnách', 'ami': 'základnami'}),
    (r'\bvýsp\b', 'základen'),
    # Village Hall -> radnice
    (r'\bobecní dům\b', 'radnice'), (r'\bobecního domu\b', 'radnice'), (r'\bobecnímu domu\b', 'radnici'),
    (r'\bobecním domě\b', 'radnici'), (r'\bobecním domem\b', 'radnicí'),
    # Companion -> družiník
    (r'\bspolečník(a|ovi|em|ů|ům|y)?\b', lambda m: 'družiník' + (m.group(1) or '')),
    (r'\bspolečníci\b', 'družiníci'), (r'\bspolečnících\b', 'družinících'),
    # Worker -> dělník
    (r'\bpracovník(a|ovi|em|ů|ům|y)?\b', lambda m: 'dělník' + (m.group(1) or '')),
    (r'\bpracovníci\b', 'dělníci'), (r'\bpracovnících\b', 'dělnících'),
    # Mayor -> purkmistr  (starost = worry se nechyta: jine koncovky)
    (r'\bstarost(a|y|ovi|u|ou|o|ové|ů|ům)\b', {'a': 'purkmistr', 'y': 'purkmistra', 'ovi': 'purkmistrovi', 'u': 'purkmistra', 'ou': 'purkmistrem', 'o': 'purkmistře', 'ové': 'purkmistři', 'ů': 'purkmistrů', 'ům': 'purkmistrům'}),
    (r'se starostou', 's purkmistrem'),
    # Butchery -> porcovna
    (r'na jatkách', 'v porcovně'),
    (r'\bjatk(a|ách|ám|y)\b', {'a': 'porcovna', 'ách': 'porcovně', 'ám': 'porcovně', 'y': 'porcovny'}),
    (r'\bjatek\b', 'porcovny'),
    # Tavern -> krčma
    (r'\bhospod(a|y|ě|u|ou|ách|ám|ami)\b', {'a': 'krčma', 'y': 'krčmy', 'ě': 'krčmě', 'u': 'krčmu', 'ou': 'krčmou', 'ách': 'krčmách', 'ám': 'krčmám', 'ami': 'krčmami'}),
    # Shack -> chatrč
    (r'\bboud(a|y|ě|u|ou)\b', {'a': 'chatrč', 'y': 'chatrče', 'ě': 'chatrči', 'u': 'chatrč', 'ou': 'chatrčí'}),
    # Healer -> ranhojič
    (r'\bléčitel(e|i|em|é|ů|ům|ce|kou|ka|ky|ek)?\b', {None: 'ranhojič', 'e': 'ranhojiče', 'i': 'ranhojiči', 'em': 'ranhojičem', 'é': 'ranhojiči', 'ů': 'ranhojičů', 'ům': 'ranhojičům', 'ka': 'ranhojička', 'ky': 'ranhojičky', 'ce': 'ranhojičce', 'kou': 'ranhojičkou', 'ek': 'ranhojiček'}),
    # Smelter -> tavicí pec
    (r'\btavírn(a|y|ě|u|ou)\b', {'a': 'tavicí pec', 'y': 'tavicí pece', 'ě': 'tavicí peci', 'u': 'tavicí pec', 'ou': 'tavicí pecí'}),
    # Mixing Bucket -> vědro na míchání
    (r'\bv míchacím vědru\b', 've vědru na míchání'), (r'\bmíchací vědro\b', 'vědro na míchání'),
    (r'\bmíchacího vědra\b', 'vědra na míchání'), (r'\bmíchacím vědrem\b', 'vědrem na míchání'),
    # Drying Rack -> sušicí rám
    (r'\bsušák(u|em|y|ů|ům)?\b(?! na prádlo)', {None: 'sušicí rám', 'u': 'sušicím rámu', 'em': 'sušicím rámem', 'y': 'sušicí rámy', 'ů': 'sušicích rámů', 'ům': 'sušicím rámům'}),
    (r'\bsušácích\b', 'sušicích rámech'),
    # Prosperity -> rozkvět
    (r'\bprosperit(a|y|ě|u|ou)\b', {'a': 'rozkvět', 'y': 'rozkvětu', 'ě': 'rozkvětu', 'u': 'rozkvět', 'ou': 'rozkvětem'}),
    # Militia -> domobrana (milice: nom/gen/acc pl nejednoznacne -> nom/gen podle kontextu resi rucne nize)
    (r'\bmilici\b', 'domobranu'), (r'\bmilicí\b', 'domobranou'), (r'\bmilicemi\b', 'domobranami'),
    # dodatecne opravy predlozek a rodu po nahradach
    (r'\bse (purkmistr\w*)', lambda m: 's ' + m.group(1)),
    (r'\bna porcovně\b', 'v porcovně'),
    (r'\bNáš radnice\b', 'Naše radnice'),
    (r'ztratil svůj někdejší lesk\. Rád bych ho', 'ztratila svůj někdejší lesk. Rád bych ji'),
    (r'\bobnovit náš radnice\b', 'obnovit naši radnici'),
    (r'\bRadnice padl\b', 'Radnice padla'),
    (r'\btrofeje pro radnice\b', 'trofeje pro radnici'),
    (r'\bvrátit radnici jeho dřívější\b', 'vrátit radnici její dřívější'),
    (r'\bv tavírnách\b', 'v tavicích pecích'),
    (r'\bléčitelsk(á|é|ou|ých|ým)\b', {'á': 'ranhojičská', 'é': 'ranhojičské', 'ou': 'ranhojičskou', 'ých': 'ranhojičských', 'ým': 'ranhojičským'}),
]

EXACT = {  # cele retezce (nazvy predmetu/UI)
    'Balvan': None,  # resi se podle zdroje nize
}
EXACT_BY_SOURCE = {
    'Crude Stone': 'Hrubý kámen',
    'Rock': 'Kámen',
    'Stockpile': 'Sklad',
    'Lobby': 'Lobby',
    'Settlement requires at least one stockpile': 'Osada potřebuje aspoň jeden sklad',
    'Required Prosperity: {Prosperity}': 'Potřebný rozkvět: {Prosperity}',
    'Militia patrol activity: ': 'Aktivita hlídek domobrany: ',
    "Hunter's Lodge": 'Lovecký srub',
    'Find the new stockpile Miller was talking about': 'Najdi nový sklad, o kterém mluvil mlynář',
    'Sol Winery was turned into a slaughterhouse. Someone snitched about Cassandra’s plan and killed all the Sol’s goons.I need to check what is happening inside the town. The mayor could be in danger.': 'Sol Winery se změnilo v jatka. Někdo prozradil Cassandřin plán a pobil všechny hrdlořezy ze Solu. Musím zjistit, co se děje ve městě. Purkmistr může být v nebezpečí.',
    'This lodge will provide a place to sleep along with interiors and a small garden.': 'Tento srub poskytne místo na spaní spolu s vybavením a malou zahradou.',
}


def apply_rule(text, pat, rep):
    def sub(m):
        if callable(rep):
            out = rep(m)
        elif isinstance(rep, dict):
            key = m.group(1) if m.lastindex else None
            out = rep.get(key)
            if out is None:
                return m.group(0)
        else:
            out = rep
        if m.group(0)[0].isupper():
            out = out[0].upper() + out[1:]
        return out
    parts = re.split(r'(\{[^}]*\}|<[^>]*>)', text)   # {Placeholder} a <tagy> nechat na pokoji
    return ''.join(seg if i % 2 else re.sub(pat, sub, seg, flags=re.IGNORECASE) for i, seg in enumerate(parts))


def main():
    apply = '--apply' in sys.argv
    entries = po.load(PO)
    changed = 0
    samples = []
    for e in entries:
        if not e.translated:
            continue
        old = e.translation
        new = old
        if e.source in EXACT_BY_SOURCE:
            new = EXACT_BY_SOURCE[e.source]
        else:
            for pat, rep in RULES:
                new = apply_rule(new, pat, rep)
        if new != old:
            changed += 1
            if len(samples) < 400:
                samples.append((e.source[:60], old[:90], new[:90]))
            e.translation = new
    for s, o, n in samples:
        print(f'  {s!r}\n    - {o!r}\n    + {n!r}')
    print(f'\nzmeneno retezcu: {changed}')
    # zbyva rucne: "milice" (nom/gen), "chata", "Lobby"
    print('\n--- rucni kontrola (milice / chata / lobby):')
    for e in entries:
        if re.search(r'\bmilice\b|\bchat(a|y|ě|u|ou)\b|předsíň', e.translation, re.I):
            print(f'  {e.source[:70]!r}\n    = {e.translation[:110]!r}')
    if apply:
        po.save(PO, entries)
        print('ulozeno')


if __name__ == '__main__':
    main()
