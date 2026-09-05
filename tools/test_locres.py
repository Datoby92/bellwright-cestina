"""Round-trip pylocres against every uncompressed .locres the game pak contains.

The big Game.locres is Oodle-compressed and out of reach here, but the engine and
plugin resources sit in the pak uncompressed, which is enough to prove the
reader and writer agree with the engine's own format byte for byte.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pylocres import LocRes, MAGIC

PAK = ("D:/SteamLibrary/steamapps/common/Bellwright/Bellwright/Content/Paks/"
       "pakchunk0-Windows.pak")

CZECH = 'Příliš žluťoučký kůň úpěl ďábelské ódy — ĚŠČŘŽÝÁÍÉÚŮŤĎŇ'


def find_blobs(data):
    pos = 0
    while True:
        at = data.find(MAGIC, pos)
        if at < 0:
            return
        yield at
        pos = at + 1


def main():
    data = open(PAK, 'rb').read()
    total = exact = 0
    versions = {}

    for at in find_blobs(data):
        total += 1
        try:
            res = LocRes.parse(data[at:])
        except Exception as exc:
            print('  parse failed at 0x%x: %s' % (at, exc))
            continue

        out = res.serialize()
        versions[res.version] = versions.get(res.version, 0) + 1

        if out == data[at:at + len(out)]:
            exact += 1
        else:
            print('  MISMATCH at 0x%x (v%d, %d entries)'
                  % (at, res.version, sum(1 for _ in res.entries())))

    print('locres blobs found      : %d' % total)
    print('byte-identical roundtrip: %d' % exact)
    print('versions seen           : %s' % versions)

    # Now prove we can actually write Czech text back out and read it again.
    at = next(find_blobs(data))
    res = LocRes.parse(data[at:])
    pairs = res.as_dict()
    if not pairs:
        print('no entries to translate in the sample resource')
        return 1
    target = sorted(pairs)[0]
    changed = res.apply({target: CZECH})

    reloaded = LocRes.parse(res.serialize())
    got = reloaded.as_dict()[target]

    print()
    print('translation test')
    print('  entry          : %s / %s' % target)
    print('  english        : %r' % pairs[target])
    print('  wrote          : %d entry' % changed)
    print('  read back      : %r' % got)
    print('  czech survived : %s' % (got == CZECH))

    untouched = {k: v for k, v in reloaded.as_dict().items() if k != target}
    original = {k: v for k, v in pairs.items() if k != target}
    print('  others intact  : %s' % (untouched == original))

    ok = exact == total and got == CZECH and untouched == original
    print()
    print('RESULT: %s' % ('PASS' if ok else 'FAIL'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
