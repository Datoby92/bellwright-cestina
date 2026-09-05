"""Print a batch of untranslated strings, ready to be turned into a TSV.

Sorting alphabetically by the English source is deliberate: it clusters item
families together ("Halmayan Leather Boots", "Halmayan Leather Gloves", ...),
which is what keeps their Czech names consistent with each other.

    python tools/dump.py --skip 0 --take 250
    python tools/dump.py --max-len 26          # only short strings (names, UI)
    python tools/dump.py --category Npcs/Talk  # only one asset category
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import po as po_mod

PO = 'D:/BellwrightCZ/cestina.po'
CSV = 'D:/BellwrightCZ/tools/UEExtractor/Bellwright_locres.csv'
_ROW = re.compile(r'^\[([^\]]*)\]\[([0-9A-Fa-f]{32})\]\[(\d+)\],')


def load_paths():
    """key -> asset path, for the strings UEExtractor could trace to an asset."""
    paths = {}
    if not os.path.exists(CSV):
        return paths
    with open(CSV, encoding='utf-8-sig') as f:
        for line in f:
            m = _ROW.match(line)
            if m and m.group(1):
                paths.setdefault(m.group(2).upper(), m.group(1))
    return paths


def category(path):
    m = re.search(r'/Mist/Data/([^/]+)(?:/([^/]+))?', path or '')
    if not m:
        return ''
    head, tail = m.group(1), m.group(2) or ''
    return '%s/%s' % (head, tail) if head in ('Npcs', 'Quests') and tail else head


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--skip', type=int, default=0)
    p.add_argument('--take', type=int, default=250)
    p.add_argument('--max-len', type=int)
    p.add_argument('--min-len', type=int)
    p.add_argument('--category')
    p.add_argument('--unmapped', action='store_true',
                   help='jen retezce, ktere se nepodarilo zaradit k assetu')
    p.add_argument('--unique', action='store_true',
                   help='seskupit shodne originaly do jednoho radku (pocet + text)')
    p.add_argument('--words', action='store_true',
                   help='vynechat retezce bez pismen (cisla, symboly, oddelovace)')
    p.add_argument('--po', default=PO)
    args = p.parse_args()

    paths = load_paths()
    entries = [e for e in po_mod.load(args.po)
               if not e.namespace and not e.translated]

    if args.unmapped:
        entries = [e for e in entries if e.key.upper() not in paths]
    if args.category:
        entries = [e for e in entries
                   if category(paths.get(e.key.upper())) == args.category]
    if args.max_len:
        entries = [e for e in entries if len(e.source) <= args.max_len]
    if args.min_len:
        entries = [e for e in entries if len(e.source) >= args.min_len]

    if args.words:
        # Numbers, separators and "4/5" style debug leftovers need no translation.
        entries = [e for e in entries
                   if len(re.findall(r'[A-Za-z]', e.source)) >= 2]

    def escape(text):
        # CRLF and LF are escaped distinctly - the game uses both, and a TSV line
        # that collapses them will not match its source when applied back.
        return text.replace('\\', '\\\\').replace('\r\n', '\\r\\n') \
                   .replace('\n', '\\n').replace('\t', ' ')

    if args.unique:
        counts = {}
        for e in entries:
            counts[e.source] = counts.get(e.source, 0) + 1
        sources = sorted(counts, key=lambda s: s.lower())
        total = len(sources)
        chunk = sources[args.skip:args.skip + args.take]
        print('# ruznych originalu: %d (celkem %d retezcu), zobrazeno %d-%d'
              % (total, len(entries), args.skip, args.skip + len(chunk)))
        for s in chunk:
            print('%dx\t%s' % (counts[s], escape(s)))
        return

    entries.sort(key=lambda e: (e.source.lower(), e.key))
    total = len(entries)
    chunk = entries[args.skip:args.skip + args.take]

    print('# odpovida filtru: %d, zobrazeno %d-%d'
          % (total, args.skip, args.skip + len(chunk)))
    for e in chunk:
        print('%s\t%s' % (e.key, escape(e.source)))


if __name__ == '__main__':
    main()
