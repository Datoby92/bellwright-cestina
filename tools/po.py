"""Gettext PO reading and writing, in the dialect Unreal Engine uses.

UE identifies a string by namespace plus key and writes that pair into msgctxt as
"namespace,key". Keeping the same convention means the files here can be handed
straight to the ModKit's Localization Dashboard if we ever want to, while still
being a plain text format that diffs cleanly and survives review.
"""

import re

ESCAPES = {'\\': '\\\\', '"': '\\"', '\n': '\\n', '\t': '\\t', '\r': '\\r'}
UNESCAPES = {'\\': '\\', '"': '"', 'n': '\n', 't': '\t', 'r': '\r'}


def escape(s):
    return ''.join(ESCAPES.get(c, c) for c in s)


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            out.append(UNESCAPES.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


class PoEntry:
    __slots__ = ('namespace', 'key', 'source', 'translation', 'comments', 'flags')

    def __init__(self, namespace, key, source, translation='', comments=None, flags=None):
        self.namespace = namespace
        self.key = key
        self.source = source
        self.translation = translation
        self.comments = comments or []
        self.flags = flags or []

    @property
    def ctxt(self):
        return '%s,%s' % (self.namespace, self.key)

    @property
    def translated(self):
        return bool(self.translation)


_LINE = re.compile(r'^(msgctxt|msgid|msgstr)\s+"(.*)"\s*$')
_CONT = re.compile(r'^"(.*)"\s*$')


def parse(text):
    """Parse PO text into a list of PoEntry, skipping the header entry."""
    entries = []
    field = None
    buf = {'msgctxt': None, 'msgid': None, 'msgstr': None}
    comments = []
    flags = []

    def flush():
        if buf['msgid'] is None:
            return
        ctxt = buf['msgctxt'] or ''
        namespace, _, key = ctxt.partition(',')
        if buf['msgid'] or ctxt:            # skip the PO header (empty msgid, no ctxt)
            entries.append(PoEntry(namespace, key, buf['msgid'],
                                   buf['msgstr'] or '', list(comments), list(flags)))
        buf['msgctxt'] = buf['msgid'] = buf['msgstr'] = None
        del comments[:]
        del flags[:]

    for raw in text.splitlines():
        line = raw.rstrip('\r')
        if not line.strip():
            flush()
            field = None
            continue
        if line.startswith('#,'):
            flags.extend(f.strip() for f in line[2:].split(','))
            continue
        if line.startswith('#'):
            comments.append(line)
            continue
        m = _LINE.match(line)
        if m:
            field = m.group(1)
            if field == 'msgctxt' and buf['msgid'] is not None:
                flush()
            buf[field] = unescape(m.group(2))
            continue
        m = _CONT.match(line)
        if m and field:
            buf[field] += unescape(m.group(1))
    flush()
    return entries


def serialize(entries, header_comment=None):
    out = []
    if header_comment:
        for line in header_comment.splitlines():
            out.append('# %s' % line if line else '#')
    out.append('msgid ""')
    out.append('msgstr ""')
    out.append('"MIME-Version: 1.0\\n"')
    out.append('"Content-Type: text/plain; charset=UTF-8\\n"')
    out.append('"Content-Transfer-Encoding: 8bit\\n"')
    out.append('"Language: cs\\n"')
    out.append('"Plural-Forms: nplurals=4; plural=(n==1) ? 0 : (n>=2 && n<=4) ? 1 '
               ': (n!=1 && n%1!=0) ? 2 : 3;\\n"')
    out.append('')

    for e in entries:
        out.extend(e.comments)
        if e.flags:
            out.append('#, %s' % ', '.join(e.flags))
        out.append('msgctxt "%s"' % escape(e.ctxt))
        out.append(_field('msgid', e.source))
        out.append(_field('msgstr', e.translation))
        out.append('')
    return '\n'.join(out) + '\n'


def _field(name, value):
    """Long or multi-line values get split the way gettext tools expect."""
    if '\n' not in value and len(value) < 76:
        return '%s "%s"' % (name, escape(value))
    lines = ['%s ""' % name]
    chunks = value.split('\n')
    for i, chunk in enumerate(chunks):
        text = chunk + ('\n' if i < len(chunks) - 1 else '')
        if text:
            lines.append('"%s"' % escape(text))
    return '\n'.join(lines)


def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return parse(f.read())


def save(path, entries, header_comment=None):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(serialize(entries, header_comment))
