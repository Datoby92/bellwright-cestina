"""Quality checks for the Czech translation.

Most of what goes wrong in a game translation is not bad prose - it is a dropped
{PlayerName}, a rich-text tag that no longer closes, or a plural that reads fine
for one item and wrong for five. Those break silently in game, so they are
checked mechanically here. The rest of the checks enforce the things a reader
notices: consistent terminology and correct Czech typography.

Severities:
    error   - will look broken or crash formatting in game; must be fixed
    warning - very likely wrong; look at it
    info    - worth a glance, often fine
"""

import re

# ---------------------------------------------------------------- placeholders

# UE format arguments look like {Name} or {0}, optionally followed by a modifier
# such as |plural(one=box,other=boxes) or |gender(masculine,feminine).
_ARG = re.compile(r'\{([A-Za-z_][A-Za-z0-9_]*|\d+)\}')
_MODIFIER = re.compile(r'\}\|([A-Za-z]+)\(')

# Rich text: <Bold>text</>, <img id="coin"/>, closed with </>.
_TAG_OPEN = re.compile(r'<([A-Za-z][A-Za-z0-9_.]*)\b[^>]*?(/?)>')
_TAG_CLOSE = re.compile(r'</\s*([A-Za-z][A-Za-z0-9_.]*)?\s*>')

# Czech needs more plural categories than English does.
CZECH_PLURAL_FORMS = {'one', 'few', 'many', 'other'}
CZECH_PLURAL_REQUIRED = {'one', 'few', 'other'}


class Issue:
    __slots__ = ('severity', 'code', 'message')

    def __init__(self, severity, code, message):
        self.severity = severity
        self.code = code
        self.message = message

    def __repr__(self):
        return '%s/%s: %s' % (self.severity, self.code, self.message)


def _args(text):
    return sorted(_ARG.findall(text))


def _modifiers(text):
    """Return [(modifier_name, body)] with balanced parentheses."""
    found = []
    for m in _MODIFIER.finditer(text):
        depth = 1
        i = m.end()
        while i < len(text) and depth:
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
            i += 1
        found.append((m.group(1), text[m.end():i - 1]))
    return found


def _plural_forms(body):
    return {m.group(1) for m in re.finditer(r'(?:^|,)\s*([A-Za-z]+|=\d+)\s*=', body)}


def _tags(text):
    opened = [m.group(1) for m in _TAG_OPEN.finditer(text) if not m.group(2)]
    selfclosed = [m.group(1) for m in _TAG_OPEN.finditer(text) if m.group(2)]
    closed = len(_TAG_CLOSE.findall(text))
    # UE rich text always closes with </>, so a <...> with no close anywhere in
    # the string is not markup - it is a stage direction the game prints as-is
    # ("<Fight>", "<Tell Cyrus about the ambush>"). Those do get translated, so
    # they must not be compared as tags.
    if closed == 0:
        opened = []
    return sorted(opened), sorted(selfclosed), closed


# ---------------------------------------------------------------------- checks

def check_placeholders(source, target):
    issues = []
    src, tgt = _args(source), _args(target)
    if src != tgt:
        missing = sorted(set(src) - set(tgt))
        extra = sorted(set(tgt) - set(src))
        detail = []
        if missing:
            detail.append('chybí %s' % ', '.join('{%s}' % a for a in missing))
        if extra:
            detail.append('přebývá %s' % ', '.join('{%s}' % a for a in extra))
        if not detail:
            detail.append('jiný počet výskytů')
        issues.append(Issue('error', 'placeholder',
                            'proměnné nesedí: ' + '; '.join(detail)))
    return issues


def check_plurals(source, target):
    issues = []
    src_mods = _modifiers(source)
    tgt_mods = {name: body for name, body in _modifiers(target)}

    for name, body in src_mods:
        if name not in tgt_mods:
            issues.append(Issue('error', 'modifier',
                                'v překladu chybí |%s(...)' % name))
            continue
        if name != 'plural':
            continue
        forms = _plural_forms(tgt_mods[name])
        named = {f for f in forms if not f.startswith('=')}
        missing = CZECH_PLURAL_REQUIRED - named
        if missing:
            issues.append(Issue('error', 'plural',
                                'čeština potřebuje tvary %s (má jen %s)'
                                % (', '.join(sorted(missing)),
                                   ', '.join(sorted(named)) or 'žádné')))
        elif 'many' not in named:
            issues.append(Issue('info', 'plural',
                                'chybí tvar "many" pro desetinná čísla (např. 1,5)'))
    return issues


def check_richtext(source, target):
    issues = []
    s_open, s_self, s_close = _tags(source)
    t_open, t_self, t_close = _tags(target)
    if s_open != t_open or s_self != t_self:
        issues.append(Issue('error', 'richtext',
                            'formátovací značky nesedí: zdroj %s, překlad %s'
                            % (s_open + s_self, t_open + t_self)))
    elif s_close != t_close:
        issues.append(Issue('error', 'richtext',
                            'jiný počet uzavíracích </>: zdroj %d, překlad %d'
                            % (s_close, t_close)))
    return issues


def check_whitespace(source, target):
    issues = []
    if source[:1].isspace() != target[:1].isspace() or \
       source[-1:].isspace() != target[-1:].isspace():
        issues.append(Issue('warning', 'whitespace',
                            'jiné mezery na začátku/konci než ve zdroji'))
    if source.count('\n') != target.count('\n'):
        issues.append(Issue('warning', 'newlines',
                            'jiný počet řádků: zdroj %d, překlad %d'
                            % (source.count('\n'), target.count('\n'))))
    if '  ' in target.replace('\n', ' ').strip():
        issues.append(Issue('info', 'typography', 'dvojitá mezera'))
    return issues


def check_typography(target):
    issues = []
    if '"' in target:
        issues.append(Issue('info', 'typography',
                            'rovné uvozovky " - v češtině se sází „takto“'))
    if '...' in target:
        issues.append(Issue('info', 'typography',
                            'tři tečky - správně je výpustka …'))
    if re.search(r'\s[-]\s', target):
        issues.append(Issue('info', 'typography',
                            'spojovník mezi mezerami - správně je pomlčka –'))
    return issues


def check_glossary(source, target, glossary):
    """glossary: {english_term: (czech_term, [accepted_variants])}"""
    issues = []
    low_src = source.lower()
    low_tgt = target.lower()
    for term, (czech, variants) in glossary.items():
        if not re.search(r'\b%s\b' % re.escape(term.lower()), low_src):
            continue
        accepted = [czech] + list(variants)
        if not any(v.lower() in low_tgt for v in accepted if v):
            issues.append(Issue('warning', 'glossary',
                                '"%s" se podle slovníku překládá jako "%s"'
                                % (term, czech)))
    return issues


def check_length(source, target, limit_ratio=1.8, min_source=12):
    """Czech runs roughly 10% longer than English; far beyond that risks clipped UI."""
    if len(source) < min_source:
        return []
    ratio = len(target) / len(source)
    if ratio > limit_ratio:
        return [Issue('info', 'length',
                      'překlad je %.1fx delší než zdroj - hlídej, ať se vejde do UI'
                      % ratio)]
    return []


def check_entry(source, target, glossary=None, skip_typography=False):
    """Run every check on one string pair. Returns a list of Issue."""
    if not target:
        return [Issue('warning', 'untranslated', 'nepřeloženo')]
    if target == source and re.search(r'[A-Za-z]{3}', source):
        return [Issue('info', 'identical', 'shodné se zdrojem')]

    issues = []
    issues += check_placeholders(source, target)
    issues += check_plurals(source, target)
    issues += check_richtext(source, target)
    issues += check_whitespace(source, target)
    if not skip_typography:
        issues += check_typography(target)
    if glossary:
        issues += check_glossary(source, target, glossary)
    issues += check_length(source, target)
    return issues


def check_consistency(entries):
    """Flag one English string translated several different ways, and vice versa.

    Both directions matter: the first makes the game feel sloppy, the second
    quietly merges two distinct game concepts into one Czech word.
    """
    issues = []
    forward = {}
    backward = {}
    for e in entries:
        if not e.translation:
            continue
        forward.setdefault(e.source, {}).setdefault(e.translation, []).append(e)
        backward.setdefault(e.translation, {}).setdefault(e.source, []).append(e)

    for source, variants in forward.items():
        if len(variants) > 1 and len(source) < 60:
            issues.append(Issue('warning', 'inconsistent',
                                '"%s" je přeloženo %d způsoby: %s'
                                % (source, len(variants),
                                   ' / '.join(sorted(variants)))))
    for translation, sources in backward.items():
        if len(sources) > 1 and len(translation) < 60:
            issues.append(Issue('info', 'collision',
                                '"%s" pokrývá %d různých originálů: %s'
                                % (translation, len(sources),
                                   ' / '.join(sorted(sources)))))
    return issues


def load_glossary(path):
    """TSV: english <tab> czech <tab> optional comma-separated accepted variants."""
    glossary = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            english = parts[0].strip()
            czech = parts[1].strip()
            variants = [v.strip() for v in parts[2].split(',')] if len(parts) > 2 else []
            glossary[english] = (czech, variants)
    return glossary


# ----------------------------------------------------------------- homographs

# English words that mean two different things in this game and therefore have
# two different Czech words. Machine translation reliably picks the wrong one at
# least some of the time, and nothing else in the pipeline would notice, because
# the result is a perfectly ordinary Czech sentence - just about the wrong thing.
#
# So these are not auto-checked, they are listed for a human to eyeball. The
# meanings are written out so the reviewer can tell at a glance which one the
# string actually needed.
HOMOGRAPHS = {
    'hide':    ['kůže (surovina)', 'skrýt (sloveso)'],
    'game':    ['hra', 'zvěř (lovená)'],
    'arms':    ['zbraně', 'paže'],
    'bow':     ['luk', 'úklona', 'příď'],
    'draw':    ['nátah (luku)', 'kreslit', 'remíza'],
    'craft':   ['řemeslo / vyrábět', 'plavidlo'],
    'stock':   ['zásoba', 'pažba', 'dobytek'],
    'range':   ['dostřel', 'rozsah', 'pastvina'],
    'order':   ['rozkaz', 'zakázka', 'pořadí'],
    'charge':  ['útok (vojenský)', 'nálož', 'poplatek', 'nabít'],
    'lead':    ['vést', 'olovo'],
    'iron':    ['železo', 'žehlit'],
    'train':   ['cvičit', 'vlak', 'vlečka'],
    'light':   ['světlo', 'lehký', 'zapálit'],
    'fair':    ['trh', 'spravedlivý', 'světlý'],
    'fine':    ['pokuta', 'jemný', 'v pořádku'],
    'well':    ['studna', 'dobře'],
    'spring':  ['pramen', 'jaro', 'pružina'],
    'staff':   ['hůl', 'personál'],
    'board':   ['prkno', 'vývěska', 'nastoupit'],
    'post':    ['sloup / kůl', 'stanoviště', 'pošta'],
    'plant':   ['rostlina', 'zasadit', 'závod'],
    'scale':   ['šupina', 'váhy', 'měřítko'],
    'pen':     ['ohrada', 'pero'],
    'yield':   ['výnos', 'ustoupit'],
    'mine':    ['důl', 'můj'],
    'rest':    ['odpočinek', 'zbytek'],
    'watch':   ['hlídka', 'sledovat'],
    'second':  ['druhý', 'sekunda'],
    'round':   ['kolo', 'kulatý'],
    'match':   ['zápalka', 'shoda', 'zápas'],
    'store':   ['sklad', 'obchod'],
    'temper':  ['kalit (kov)', 'povaha'],
    'fell':    ['pokácet', 'padl'],
    'ring':    ['prsten', 'zvonit', 'kruh'],
    'saw':     ['pila', 'viděl'],
    'stake':   ['kůl', 'sázka'],
    'tie':     ['uvázat', 'remíza'],
    'quarter': ['čtvrtina', 'ubytovat', 'čtvrť'],
    'coat':    ['kabát', 'vrstva', 'srst'],
    'bill':    ['halapartna', 'účet', 'zobák'],
    'pitch':   ['smola', 'hod', 'sklon'],
    'sound':   ['zvuk', 'zdravý'],
    'point':   ['bod', 'špice', 'ukázat'],
    'left':    ['vlevo', 'odešel', 'zbylý'],
    'spoke':   ['paprsek kola', 'promluvil'],
    'yard':    ['dvůr', 'yard (míra)'],
}

_HOMOGRAPH_RE = {w: re.compile(r'\b%s\b' % re.escape(w), re.I) for w in HOMOGRAPHS}


def find_homographs(source):
    """Return the ambiguous English words present in this source string."""
    return [w for w, rx in _HOMOGRAPH_RE.items() if rx.search(source)]

# Reported from play-testing: "Content" showed up under Morale as "Obsah"
# (table of contents) instead of "Spokojenost" (a mood). Same trap as "hide".
HOMOGRAPHS.update({
    'content':   ['obsah', 'spokojený (nálada)'],
    'full':      ['plný (nádoba)', 'najedený (sytost)'],
    'stout':     ['statný', 'silné pivo'],
    'dealt':     ['způsobený', 'rozdaný'],
})
_HOMOGRAPH_RE.update({w: re.compile(r'\b%s\b' % re.escape(w), re.I)
                      for w in ('content', 'full', 'stout', 'dealt')})
