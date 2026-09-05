"""Command line front end for the Bellwright Czech localization.

    export  en/Game.locres            -> cestina.po   (source strings, empty translations)
    stats   cestina.po                -> how much is done
    check   cestina.po                -> quality report
    build   cestina.po + en/Game.locres -> cs/Game.locres

The English Game.locres stays the single source of truth for structure: build
never invents entries, it copies the shipped file and swaps in the strings we
have translated. Anything untranslated falls back to English in game, so a
partial translation is always safe to ship.
"""

import argparse
import os
import sys
import collections
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import po as po_mod
import qa as qa_mod
from pylocres import LocRes


def _sort_key(entry):
    return (entry.namespace, entry.key)


# ------------------------------------------------------------------- commands

def cmd_export(args):
    res = LocRes.load(args.locres)
    sources = res.as_dict()

    existing = {}
    if args.merge and os.path.exists(args.out):
        for e in po_mod.load(args.out):
            existing[(e.namespace, e.key)] = e

    entries = []
    kept = dropped = added = 0
    for (namespace, key), source in sources.items():
        old = existing.get((namespace, key))
        translation = ''
        flags = []
        if old is not None:
            if old.source == source:
                translation = old.translation
                flags = [f for f in old.flags if f != 'fuzzy']
                kept += 1
            elif old.translation:
                # English changed under us - keep the old Czech but mark it.
                translation = old.translation
                flags = ['fuzzy']
                dropped += 1
        else:
            added += 1
        entries.append(po_mod.PoEntry(namespace, key, source, translation,
                                      comments=[], flags=flags))

    entries.sort(key=_sort_key)
    po_mod.save(args.out, entries,
                header_comment='Bellwright - ceska lokalizace\n'
                               'Generovano z %s' % os.path.basename(args.locres))
    print('zapsano %d retezcu do %s' % (len(entries), args.out))
    if args.merge:
        print('  prevzato beze zmeny : %d' % kept)
        print('  zmeneny original    : %d  (oznaceno fuzzy)' % dropped)
        print('  nove retezce        : %d' % added)
    return 0


def cmd_apply(args):
    """Merge namespace/key/czech TSV files into the .po."""
    entries = po_mod.load(args.po)
    index = {(e.namespace, e.key): e for e in entries}

    applied = unknown = unchanged = 0
    missing = []
    for path in args.tsv:
        with open(path, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = line.rstrip('\n')
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                parts = line.split('\t')
                # Most of the game's text sits in the empty namespace and is
                # addressed by a bare 32-hex key, so allow the shorter two
                # column form rather than making every such line start with a tab.
                if len(parts) == 2 and re.fullmatch(r'[0-9A-Fa-f]{32}', parts[0]):
                    namespace, key, czech = '', parts[0], parts[1]
                elif len(parts) >= 3:
                    namespace, key, czech = parts[0], parts[1], '\t'.join(parts[2:])
                else:
                    print('%s:%d: preskoceno, ceka se namespace<TAB>key<TAB>text'
                          % (os.path.basename(path), lineno))
                    continue
                target = index.get((namespace, key))
                if target is None:
                    unknown += 1
                    missing.append('%s / %s' % (namespace, key))
                    continue
                czech = czech.replace('\\r\\n', '\r\n').replace('\\n', '\n')
                if target.translation == czech:
                    unchanged += 1
                    continue
                target.translation = czech
                target.flags = [f for f in target.flags if f != 'fuzzy']
                applied += 1

    entries.sort(key=_sort_key)
    po_mod.save(args.po, entries, header_comment='Bellwright - ceska lokalizace')
    print('vlozeno   : %d' % applied)
    print('beze zmeny: %d' % unchanged)
    print('neznamych : %d' % unknown)
    for m in missing[:15]:
        print('    ? %s' % m)
    return 0


def cmd_bysource(args):
    """Apply "english <TAB> czech" TSVs to every entry sharing that English text.

    The game repeats a lot of short strings - the same "(GOT IT)" reply sits
    under sixteen different keys - so translating by source text instead of by
    key both saves the work and guarantees they stay identical.

    Only untranslated entries are filled in, so a deliberate context-specific
    translation made earlier by key is never overwritten.
    """
    entries = po_mod.load(args.po)
    by_source = collections.defaultdict(list)
    for e in entries:
        if args.overwrite or not e.translated:
            by_source[e.source].append(e)

    filled = phrases = unknown = 0
    missing = []
    for path in args.tsv:
        with open(path, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = line.rstrip('\n')
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) < 2:
                    print('%s:%d: preskoceno, ceka se original<TAB>preklad'
                          % (os.path.basename(path), lineno))
                    continue
                english = parts[0].replace('\\r\\n', '\r\n').replace('\\n', '\n')
                czech = '\t'.join(parts[1:]).replace('\\r\\n', '\r\n') \
                                            .replace('\\n', '\n')
                targets = by_source.get(english)
                if not targets:
                    unknown += 1
                    missing.append(english[:70])
                    continue
                phrases += 1
                for e in targets:
                    e.translation = czech
                    e.flags = [f for f in e.flags if f != 'fuzzy']
                    filled += 1

    entries.sort(key=_sort_key)
    po_mod.save(args.po, entries, header_comment='Bellwright - ceska lokalizace')
    print('originalu prelozeno: %d' % phrases)
    print('retezcu vyplneno   : %d' % filled)
    print('nenalezeno         : %d' % unknown)
    for m in missing[:15]:
        print('    ? %r' % m)
    return 0


def cmd_stats(args):
    entries = po_mod.load(args.po)
    done = sum(1 for e in entries if e.translated)
    fuzzy = sum(1 for e in entries if 'fuzzy' in e.flags)
    chars = sum(len(e.source) for e in entries)
    todo = sum(len(e.source) for e in entries if not e.translated)

    print('retezcu celkem   : %d' % len(entries))
    print('prelozeno        : %d (%.1f %%)'
          % (done, 100.0 * done / len(entries) if entries else 0))
    print('k revizi (fuzzy) : %d' % fuzzy)
    print('znaku celkem     : %d' % chars)
    print('znaku k prekladu : %d' % todo)

    by_ns = collections.Counter()
    done_ns = collections.Counter()
    for e in entries:
        by_ns[e.namespace] += 1
        if e.translated:
            done_ns[e.namespace] += 1
    print()
    print('podle jmenneho prostoru:')
    for ns, total in by_ns.most_common(25):
        print('  %-40s %6d  %5.1f %%'
              % (ns or '(bez namespace)', total, 100.0 * done_ns[ns] / total))
    return 0


def cmd_check(args):
    entries = po_mod.load(args.po)
    glossary = qa_mod.load_glossary(args.glossary) if args.glossary else None

    counts = collections.Counter()
    shown = 0
    limit = args.limit

    for e in entries:
        if not e.translated and not args.include_untranslated:
            counts['untranslated'] += 1
            continue
        issues = qa_mod.check_entry(e.source, e.translation, glossary)
        for issue in issues:
            counts[issue.code] += 1
            if issue.severity in args.severity and shown < limit:
                shown += 1
                print('[%s] %s / %s' % (issue.severity, e.namespace, e.key))
                print('    EN: %s' % e.source.replace('\n', '\\n')[:160])
                print('    CS: %s' % e.translation.replace('\n', '\\n')[:160])
                print('    -> %s' % issue.message)
                print()

    for issue in qa_mod.check_consistency(entries):
        counts[issue.code] += 1
        if issue.severity in args.severity and shown < limit:
            shown += 1
            print('[%s] %s' % (issue.severity, issue.message))
            print()

    if shown >= limit:
        print('... vypis zkracen na %d polozek, uprav --limit' % limit)
        print()

    print('souhrn:')
    for code, n in counts.most_common():
        print('  %-16s %d' % (code, n))

    blocking = counts['placeholder'] + counts['plural'] + \
        counts['modifier'] + counts['richtext']
    print()
    print('chyb, ktere je nutne opravit: %d' % blocking)
    return 1 if blocking and args.strict else 0


def cmd_homographs(args):
    """List translated strings whose English source contains an ambiguous word.

    These cannot be checked automatically - both readings produce valid Czech -
    so the point is to put them in front of a human in one compact list.
    """
    entries = [e for e in po_mod.load(args.po) if e.translated]
    groups = collections.OrderedDict()
    for e in entries:
        for word in qa_mod.find_homographs(e.source):
            groups.setdefault(word, []).append(e)

    if args.word:
        groups = {w: v for w, v in groups.items() if w == args.word.lower()}

    total = 0
    for word in sorted(groups, key=lambda w: -len(groups[w])):
        hits = groups[word]
        total += len(hits)
        print('== %s == (%d) muze znamenat: %s'
              % (word, len(hits), ' | '.join(qa_mod.HOMOGRAPHS[word])))
        for e in hits[:args.limit]:
            print('   EN: %s' % e.source.replace('\n', ' ')[:110])
            print('   CS: %s' % e.translation.replace('\n', ' ')[:110])
        if len(hits) > args.limit:
            print('   ... a dalsich %d' % (len(hits) - args.limit))
        print()
    print('celkem k prohlednuti: %d retezcu' % total)
    return 0


def cmd_build(args):
    res = LocRes.load(args.locres)
    entries = po_mod.load(args.po)

    glossary = qa_mod.load_glossary(args.glossary) if args.glossary else None
    translations = {}
    skipped = 0
    for e in entries:
        if not e.translated:
            continue
        if 'fuzzy' in e.flags and not args.include_fuzzy:
            skipped += 1
            continue
        if not args.no_verify:
            issues = qa_mod.check_entry(e.source, e.translation, glossary)
            if any(i.severity == 'error' for i in issues):
                skipped += 1
                continue
        translations[(e.namespace, e.key)] = e.translation

    changed = res.apply(translations)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    res.save(args.out)

    print('zapsano %s' % args.out)
    print('  prelozenych retezcu : %d' % changed)
    print('  preskoceno          : %d  (fuzzy nebo chyba kontroly)' % skipped)
    print('  zbytek zustava v EN (hra si poradi)')
    return 0


# ---------------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(prog='bwloc', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)

    e = sub.add_parser('export', help='Game.locres -> .po pro preklad')
    e.add_argument('locres')
    e.add_argument('-o', '--out', default='cestina.po')
    e.add_argument('--merge', action='store_true',
                   help='zachovat preklady z existujiciho .po')
    e.set_defaults(func=cmd_export)

    a = sub.add_parser('apply', help='vlozit preklady z TSV do .po')
    a.add_argument('po')
    a.add_argument('tsv', nargs='+')
    a.set_defaults(func=cmd_apply)

    bs = sub.add_parser('bysource',
                        help='vlozit preklady podle anglickeho textu (original<TAB>preklad)')
    bs.add_argument('po')
    bs.add_argument('tsv', nargs='+')
    bs.add_argument('--overwrite', action='store_true',
                    help='prepsat i uz prelozene retezce (uprava stylu)')
    bs.set_defaults(func=cmd_bysource)

    s = sub.add_parser('stats', help='stav prekladu')
    s.add_argument('po')
    s.set_defaults(func=cmd_stats)

    c = sub.add_parser('check', help='kontrola kvality')
    c.add_argument('po')
    c.add_argument('-g', '--glossary')
    c.add_argument('--severity', default='error,warning',
                   type=lambda v: set(v.split(',')))
    c.add_argument('--limit', type=int, default=60)
    c.add_argument('--include-untranslated', action='store_true')
    c.add_argument('--strict', action='store_true',
                   help='skoncit chybou, pokud jsou nalezeny chyby')
    c.set_defaults(func=cmd_check)

    h = sub.add_parser('homographs',
                       help='vypsat preklady slov, ktera maji vic vyznamu')
    h.add_argument('po')
    h.add_argument('-w', '--word', help='jen tohle jedno slovo')
    h.add_argument('--limit', type=int, default=6, help='kolik ukazek na slovo')
    h.set_defaults(func=cmd_homographs)

    b = sub.add_parser('build', help='.po + anglicky locres -> cesky locres')
    b.add_argument('po')
    b.add_argument('-l', '--locres', required=True, help='anglicky Game.locres')
    b.add_argument('-o', '--out', required=True, help='cilovy cs/Game.locres')
    b.add_argument('-g', '--glossary')
    b.add_argument('--include-fuzzy', action='store_true')
    b.add_argument('--no-verify', action='store_true',
                   help='zabalit i retezce, ktere neprosly kontrolou')
    b.set_defaults(func=cmd_build)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
