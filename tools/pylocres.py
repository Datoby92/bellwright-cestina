"""Read and write Unreal Engine .locres files.

Supports all four LocRes versions:
    0 Legacy                      (no magic header)
    1 Compact                     (magic + string array, no hashes)
    2 Optimized_CRC32             (adds entry count + FTextKey hashes + refcounts)
    3 Optimized_CityHash64_UTF16  (same layout as 2, different hash function)

A round trip read -> write reproduces the original file byte for byte, which is
what lets us swap out only the strings we translate and leave everything else
exactly as the game shipped it.
"""

import struct

MAGIC = bytes([0x0E, 0x14, 0x74, 0x75, 0x67, 0x4A, 0x03, 0xFC,
               0x4A, 0x15, 0x90, 0x9D, 0xC3, 0x37, 0x7F, 0x1B])

VERSION_LEGACY = 0
VERSION_COMPACT = 1
VERSION_CRC32 = 2
VERSION_CITYHASH64 = 3


class Reader:
    def __init__(self, buf, offset=0):
        self.buf = buf
        self.o = offset

    def u32(self):
        v, = struct.unpack_from('<I', self.buf, self.o)
        self.o += 4
        return v

    def i32(self):
        v, = struct.unpack_from('<i', self.buf, self.o)
        self.o += 4
        return v

    def i64(self):
        v, = struct.unpack_from('<q', self.buf, self.o)
        self.o += 8
        return v

    def u8(self):
        v = self.buf[self.o]
        self.o += 1
        return v

    def fstring(self):
        """UE FString: positive length = ANSI, negative = UTF-16LE. Includes a null terminator."""
        n = self.i32()
        if n == 0:
            return ''
        if n < 0:
            n = -n
            raw = self.buf[self.o:self.o + n * 2]
            self.o += n * 2
            return raw.decode('utf-16-le')[:-1]
        raw = self.buf[self.o:self.o + n]
        self.o += n
        # UE widens ANSI bytes straight to TCHAR, which is latin-1, not UTF-8.
        return raw.decode('latin-1')[:-1]


class Writer:
    def __init__(self):
        self.parts = []
        self.size = 0

    def raw(self, b):
        self.parts.append(b)
        self.size += len(b)

    def u32(self, v):
        self.raw(struct.pack('<I', v))

    def i32(self, v):
        self.raw(struct.pack('<i', v))

    def i64(self, v):
        self.raw(struct.pack('<q', v))

    def u8(self, v):
        self.raw(bytes([v]))

    def fstring(self, s):
        """Match UE's encoding choice.

        FCString::IsPureAnsi treats anything above 0x7f as non-ANSI, so the cut-off
        is plain ASCII and not latin-1 - getting this wrong rewrites accented
        strings in a different encoding than the engine shipped them in.
        """
        # UE serializes Len+1 characters so the null terminator is kept, which
        # makes an empty string length 1 holding just that terminator - not 0.
        t = s + '\x00'
        if all(ord(c) <= 0x7F for c in t):
            self.i32(len(t))
            self.raw(t.encode('ascii'))
        else:
            self.i32(-len(t))
            self.raw(t.encode('utf-16-le'))

    def getvalue(self):
        return b''.join(self.parts)


class Entry:
    """One translatable string, addressed by (namespace, key)."""

    __slots__ = ('namespace', 'key', 'ns_hash', 'key_hash', 'source_hash', 'string_index')

    def __init__(self, namespace, key, ns_hash, key_hash, source_hash, string_index):
        self.namespace = namespace
        self.key = key
        self.ns_hash = ns_hash
        self.key_hash = key_hash
        self.source_hash = source_hash
        self.string_index = string_index


class LocRes:
    """A parsed .locres file, kept close enough to the on-disk layout to rewrite it exactly."""

    def __init__(self):
        self.version = VERSION_CITYHASH64
        self.strings = []        # list[str] - the shared localized string array
        self.refcounts = []      # list[int] - parallel to strings, version >= 2 only
        self.namespaces = []     # list[(ns_hash, namespace, [Entry, ...])] in file order

    # ---------- reading ----------

    @classmethod
    def parse(cls, data):
        self = cls()
        r = Reader(data)
        if data[:16] == MAGIC:
            r.o = 16
            self.version = r.u8()
        else:
            self.version = VERSION_LEGACY

        if self.version == VERSION_LEGACY:
            raise NotImplementedError('legacy (version 0) locres is not supported')

        array_offset = r.i64()
        if not (0 < array_offset <= len(data)):
            raise ValueError('bad localized string array offset %d' % array_offset)

        # The string array lives at the end; entries reference it by index.
        s = Reader(data, array_offset)
        count = s.i32()
        for _ in range(count):
            self.strings.append(s.fstring())
            self.refcounts.append(s.i32() if self.version >= VERSION_CRC32 else None)

        if self.version >= VERSION_CRC32:
            r.i32()  # total entry count, recomputed on write

        for _ in range(r.i32()):                       # namespace count
            ns_hash = r.u32() if self.version >= VERSION_CRC32 else None
            namespace = r.fstring()
            entries = []
            for _ in range(r.i32()):                   # key count
                key_hash = r.u32() if self.version >= VERSION_CRC32 else None
                key = r.fstring()
                source_hash = r.u32()
                entries.append(Entry(namespace, key, ns_hash, key_hash,
                                     source_hash, r.i32()))
            self.namespaces.append((ns_hash, namespace, entries))
        return self

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as f:
            return cls.parse(f.read())

    # ---------- writing ----------

    def serialize(self):
        # Entries come first but the header needs the array offset, so build the
        # entry block, then place the string array right after it.
        body = Writer()
        if self.version >= VERSION_CRC32:
            body.i32(sum(len(e) for _, _, e in self.namespaces))
        body.i32(len(self.namespaces))
        for ns_hash, namespace, entries in self.namespaces:
            if self.version >= VERSION_CRC32:
                body.u32(ns_hash)
            body.fstring(namespace)
            body.i32(len(entries))
            for e in entries:
                if self.version >= VERSION_CRC32:
                    body.u32(e.key_hash)
                body.fstring(e.key)
                body.u32(e.source_hash)
                body.i32(e.string_index)

        header_size = 16 + 1 + 8
        array_offset = header_size + body.size

        out = Writer()
        out.raw(MAGIC)
        out.u8(self.version)
        out.i64(array_offset)
        out.raw(body.getvalue())
        out.i32(len(self.strings))
        for i, text in enumerate(self.strings):
            out.fstring(text)
            if self.version >= VERSION_CRC32:
                out.i32(self.refcounts[i] if self.refcounts[i] is not None else 0)
        return out.getvalue()

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.serialize())

    # ---------- convenience ----------

    def entries(self):
        for _, _, entries in self.namespaces:
            for e in entries:
                yield e

    def as_dict(self):
        """{(namespace, key): text} - the view a translator cares about."""
        return {(e.namespace, e.key): self.strings[e.string_index]
                for e in self.entries()}

    def apply(self, translations):
        """Replace text for the given {(namespace, key): text} pairs.

        Each retranslated entry gets its own slot in the string array so that
        entries which happened to share an English string can diverge in Czech.
        Returns the number of entries changed.
        """
        changed = 0
        for e in self.entries():
            new = translations.get((e.namespace, e.key))
            if new is None or new == self.strings[e.string_index]:
                continue
            self.strings.append(new)
            self.refcounts.append(1)
            old = e.string_index
            if self.refcounts[old] is not None:
                self.refcounts[old] = max(0, self.refcounts[old] - 1)
            e.string_index = len(self.strings) - 1
            changed += 1
        return changed
