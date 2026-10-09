#!/usr/bin/env python3
"""Bible data helper for the Biblical Translation Project.

Gathers data from the files at
https://raw.githubusercontent.com/AndrewChristensenWork/bible-data/main/
in one step. It downloads only the files a command needs and keeps them
in /tmp/bible-data for the rest of the chat.

Commands:
  python3 lookup.py passage "1 Peter 2:24"
      Everything for a first answer on the verse or verses sent (a range
      such as "1 Peter 2:21-25" also works): Berean verses, the verses
      around them (for the Context line and the menu's previous verse,
      next verse, and whole thought), the Berean word table, a verb form
      check against the second source, edition differences, quote notes
      with their verses, the cross-reference menu, and lexicon entries.
  python3 lookup.py uses G399 "1 Peter 2:24" [start]
      Every use of a dictionary number: count, Berean renderings, and
      up to 20 verses from position [start] with the linked English.
      Give the verse being studied so uses in the same book come first.
      The numbering is fixed, so "3.5" always means the same verse.
  python3 lookup.py check "1 Peter 2:24" draft.txt
      Test a draft's word lines before answering. Each line of the draft
      starts with the ids of the original words it carries, in braces:
        {w6} 3. **bore** — carried up — seen as a whole, in the past
        {} 2. ***was***                    (an added word carries none)
        {w10} HIDDEN: quote marker         (a word left out by rule)
      Prints CHECK PASSED or the list of faults.
  python3 lookup.py verses "Isaiah 53:5; Acts 10:39-41"
  python3 lookup.py lex G1519,G5228      (brief lexicon, full entries)
  python3 lookup.py lex G3468 classical  (classical Greek lexicon)
  python3 lookup.py xref "1 Peter 2:24"      (list the entries)
  python3 lookup.py xref "1 Peter 2:24" 2    (print the verses of entry 2)
  python3 lookup.py quoted "Isaiah 53:5"     (who quotes this verse)
  python3 lookup.py lxx "Isaiah 53:5"        (old Greek translation)
  python3 lookup.py tyndale "1 Peter 2:24"   (full rows from the second source)

Output is data for Claude to use under the project rules. The lexicons,
cross-references, and Berean notes are leads, never evidence.
"""
import os
import re
import sys
import urllib.request
from collections import Counter, OrderedDict

BASE = "https://raw.githubusercontent.com/AndrewChristensenWork/bible-data/main/"
DIR = os.environ.get("BIBLE_DATA_DIR", "/tmp/bible-data")

BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
         "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
         "Nehemiah", "Esther", "Job", "Psalm", "Proverbs", "Ecclesiastes", "Song of Solomon",
         "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
         "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
         "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
         "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
         "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
         "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
         "Revelation"]
TYN = ["Gen", "Exo", "Lev", "Num", "Deu", "Jos", "Jdg", "Rut", "1Sa", "2Sa", "1Ki", "2Ki", "1Ch",
       "2Ch", "Ezr", "Neh", "Est", "Job", "Psa", "Pro", "Ecc", "Sng", "Isa", "Jer", "Lam", "Ezk",
       "Dan", "Hos", "Jol", "Amo", "Oba", "Jon", "Mic", "Nam", "Hab", "Zep", "Hag", "Zec", "Mal",
       "Mat", "Mrk", "Luk", "Jhn", "Act", "Rom", "1Co", "2Co", "Gal", "Eph", "Php", "Col", "1Th",
       "2Th", "1Ti", "2Ti", "Tit", "Phm", "Heb", "Jas", "1Pe", "2Pe", "1Jn", "2Jn", "3Jn", "Jud",
       "Rev"]
LXX = {"Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numbers": "Num",
       "Deuteronomy": "Deut", "Joshua": "JoshB", "Judges": "JudgB", "Ruth": "Ruth",
       "1 Samuel": "1Sam", "2 Samuel": "2Sam", "1 Kings": "1Kgs", "2 Kings": "2Kgs",
       "1 Chronicles": "1Chr", "2 Chronicles": "2Chr", "Ezra": "Ezra", "Nehemiah": "Neh",
       "Esther": "Esth", "Job": "Job", "Psalm": "Ps", "Proverbs": "Prov", "Ecclesiastes": "Qoh",
       "Song of Solomon": "Cant", "Isaiah": "Isa", "Jeremiah": "Jer", "Lamentations": "Lam",
       "Ezekiel": "Ezek", "Daniel": "DanTh", "Hosea": "Hos", "Joel": "Joel", "Amos": "Amos",
       "Obadiah": "Obad", "Jonah": "Jonah", "Micah": "Mic", "Nahum": "Nah", "Habakkuk": "Hab",
       "Zephaniah": "Zeph", "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal"}
LXX_FILE_1 = {"Gen", "Exod", "Lev", "Num", "Deut", "JoshB", "JoshA", "JudgB", "JudgA", "Ruth",
              "1Sam", "2Sam", "1Kgs", "2Kgs", "1Chr", "2Chr", "1Esdr", "Ezra", "Neh", "Esth",
              "Jdt", "TobBA", "TobS", "1Mac"}


def ensure(name):
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, name)
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        try:
            urllib.request.urlretrieve(BASE + name, path)
        except Exception as exc:  # report and stop; the rules say what to do next
            print("DOWNLOAD FAILED: %s (%s)" % (name, exc))
            sys.exit(2)
    return path


def lines(name):
    with open(ensure(name), encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                yield line.rstrip("\n")


_bsb = None


def bsb():
    global _bsb
    if _bsb is None:
        _bsb = OrderedDict()
        for line in lines("bsb-verses.txt"):
            if "\t" in line:
                ref, text = line.split("\t", 1)
                _bsb[ref] = text
    return _bsb


def split_ref(ref):
    m = re.match(r"^\s*((?:[1-3] )?[A-Za-z ]+?) (\d+):(\d+)\s*$", ref)
    if not m:
        raise SystemExit("Cannot read reference: %r" % ref)
    book = m.group(1)
    if book == "Psalms":
        book = "Psalm"
    if book not in BOOKS:
        raise SystemExit("Unknown book: %r" % book)
    return book, int(m.group(2)), int(m.group(3))


def expand(spec):
    """'1 Peter 2:21-25' or 'Isaiah 52:13-53:12' or 'A 1:1; B 2:2' -> list of refs."""
    out = []
    keys = list(bsb().keys())
    index = {k: i for i, k in enumerate(keys)}
    for part in re.split(r"\s*;\s*", spec.strip()):
        if not part:
            continue
        part = part.replace("\u2013", "-")
        m = re.match(r"^(.*?) (\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$", part.strip())
        if not m:
            raise SystemExit("Cannot read reference: %r" % part)
        book, c1, v1, c2, v2 = m.groups()
        if book == "Psalms":
            book = "Psalm"
        start = "%s %s:%s" % (book, c1, v1)
        end = "%s %s:%s" % (book, c2 or c1, v2 or v1)
        if start not in index or end not in index:
            raise SystemExit("Reference not found in the Berean file: %r" % part)
        out.extend(keys[index[start]:index[end] + 1])
    return out


def words_file(book):
    i = BOOKS.index(book)
    if i >= 39:
        return "words-nt.txt"
    if i <= 7:
        return "words-ot-1-genesis-to-ruth.txt"
    if i <= 21:
        return "words-ot-2-samuel-to-song.txt"
    return "words-ot-3-isaiah-to-malachi.txt"


def tyn_file(book):
    i = BOOKS.index(book)
    if i >= 39:
        return "tyndale-nt.txt"
    return "tyndale-ot-1-genesis-to-esther.txt" if i <= 16 else "tyndale-ot-2-job-to-malachi.txt"


def tyn_ref(ref):
    book, c, v = split_ref(ref)
    return "%s.%d.%d" % (TYN[BOOKS.index(book)], c, v)


def berean_rows(refs):
    want = set(refs)
    rows = []
    for name in sorted({words_file(split_ref(r)[0]) for r in refs}):
        for line in lines(name):
            ref = line.split("\t", 1)[0]
            if ref in want:
                rows.append(line.split("\t"))
    return rows


def tyndale_rows(refs):
    want = {tyn_ref(r): r for r in refs}
    rows = []
    for name in sorted({tyn_file(split_ref(r)[0]) for r in refs}):
        for line in lines(name):
            head = line.split("\t", 1)[0]
            key = re.split(r"[#(]", head, maxsplit=1)[0]
            if key in want:
                rows.append([want[key]] + line.split("\t"))
    return rows


def count_verses(reflist):
    keys = list(bsb().keys())
    index = {k: i for i, k in enumerate(keys)}
    total = 0
    for part in re.split(r";\s*", reflist):
        m = re.match(r"^(.*?) (\d+):(.*)$", part.strip())
        if not m:
            continue
        book, ch, rest = m.groups()
        for piece in rest.split(","):
            piece = piece.strip()
            mm = re.match(r"^(\d+)-(\d+):(\d+)$", piece)
            if mm:
                a = index.get("%s %s:%s" % (book, ch, mm.group(1)))
                z = index.get("%s %s:%s" % (book, mm.group(2), mm.group(3)))
                total += (z - a + 1) if a is not None and z is not None else 1
            elif "-" in piece:
                a, z = piece.split("-")[:2]
                try:
                    total += int(z) - int(a) + 1
                except ValueError:
                    total += 1
            elif piece:
                total += 1
    return total


def expand_reflist(reflist):
    """'Deuteronomy 21:22,23; Acts 5:30; Isaiah 53:4-6,11' -> list of ref groups."""
    groups = []
    for part in re.split(r";\s*", reflist):
        m = re.match(r"^(.*?) (\d+):(.*)$", part.strip())
        if not m:
            continue
        book, ch, rest = m.groups()
        for piece in rest.split(","):
            piece = piece.strip()
            if not piece:
                continue
            mm = re.match(r"^(\d+)-(\d+):(\d+)$", piece)
            try:
                if mm:
                    groups.append(expand("%s %s:%s-%s:%s" % (book, ch, mm.group(1), mm.group(2), mm.group(3))))
                else:
                    groups.append(expand("%s %s:%s" % (book, ch, piece)))
            except SystemExit:
                groups.append(["%s %s:%s (not found)" % (book, ch, piece)])
    return groups


def xref_rows(ref):
    return [l.split("\t") for l in lines("cross-references.txt") if l.startswith(ref + "\t")]


def lex_key(number):
    m = re.match(r"^([GH])0*(\d+)", number)
    return "%s%04d" % (m.group(1), int(m.group(2))) if m else number


def lex_entries(number, classical=False):
    key = lex_key(number)
    if classical:
        names = ["lexicon-greek-classical-1.txt", "lexicon-greek-classical-2.txt"]
    else:
        names = ["lexicon-greek.txt" if key.startswith("G") else "lexicon-hebrew.txt"]
    out = []
    for name in names:
        for line in lines(name):
            head = line.split("\t", 1)[0]
            if head.startswith(key) and not head[len(key):len(key) + 1].isdigit():
                out.append(line.split("\t"))
    return out


def greek_parts_berean(code):
    m = re.match(r"^V-(\d?)([A-Z])([A-Z])([A-Z/]+)", code)
    return (m.group(2), m.group(3), m.group(4)) if m else None  # tense, mood, voice


def greek_parts_tyndale(field):
    m = re.search(r"=V-(\d?)([A-Z])([A-Z])([A-Z])", field)
    return (m.group(2), m.group(4), m.group(3)) if m else None  # tense, mood, voice


def cmd_verses(spec):
    for ref in expand(spec):
        print("%s\t%s" % (ref, bsb()[ref]))


def cmd_passage(spec, requested=None):
    refs = expand(spec)
    requested = requested or refs[0]
    is_nt = BOOKS.index(split_ref(refs[0])[0]) >= 39
    print("== BEREAN VERSES ==")
    for ref in refs:
        print("%s\t%s" % (ref, bsb()[ref]))

    keys = list(bsb().keys())
    first, last = keys.index(refs[0]), keys.index(refs[-1])
    print("\n== AROUND THESE VERSES (for the Context line and menu items A, B, C; not for printing) ==")
    print("Previous verse: %s" % (keys[first - 1] if first > 0 else "none"))
    print("Next verse: %s" % (keys[last + 1] if last + 1 < len(keys) else "none"))
    for k in keys[max(0, first - 10):first]:
        print("before  %s\t%s" % (k, bsb()[k]))
    for k in keys[last + 1:last + 7]:
        print("after   %s\t%s" % (k, bsb()[k]))

    b = berean_rows(refs)
    print("\n== WORDS: BEREAN TABLE (word id | reference | lang | word | sound | form | number | Berean English | edition marks | note) ==")
    for i, row in enumerate(b, 1):
        print("w%d | %s" % (i, " | ".join(row)))
    print("(%d original words, w1 to w%d. Every one must be placed on a word line or listed as hidden. Run 'lookup.py check' on the draft before answering.)" % (len(b), len(b)))

    print("(Each row is ONE original word. When its English is shown as several lines, those lines are pieces of one word.)")

    print("\n== WORDS THE BEREAN LEAVES WITHOUT ENGLISH (account for every one: translate it, show a hidden 'the' in square brackets, or follow the rules for quote markers, object pointers, and helper words) ==")
    none_dropped = True
    for row in b:
        eng = row[6].strip() if len(row) > 6 else ""
        if re.fullmatch(r"[-. v]*", eng):
            none_dropped = False
            print("%s | %s | %s | %s | %s" % (row[0], row[2], row[3], row[4], row[5] if len(row) > 5 else ""))
    if none_dropped:
        print("None.")

    t = tyndale_rows(refs)

    print("\n== VERB FORM CHECK ==")
    if is_nt:
        for ref in refs:
            bv = [r for r in b if r[0] == ref and len(r) > 4 and r[4].startswith("V-")]
            tv = [r for r in t if r[0] == ref and len(r) > 4 and "=V-" in r[4]]
            if len(bv) != len(tv):
                print("%s: the two tables list a different number of verbs (%d and %d). Compare by eye."
                      % (ref, len(bv), len(tv)))
            for x, y in zip(bv, tv):
                p, q = greek_parts_berean(x[4]), greek_parts_tyndale(y[4])
                if p and q:
                    tense_mood = "same" if p[:2] == q[:2] else "DIFFERENT TENSE OR MOOD"
                    voice = "same voice" if p[2] == q[2] else "voice labels differ (%s / %s)" % (p[2], q[2])
                    print("%s  %s (%s)  Berean %s | Tyndale %s  -> %s; %s"
                          % (ref, x[2], x[6] if len(x) > 6 else "", x[4], y[4].split("=")[-1], tense_mood, voice))
    else:
        print("Hebrew and Aramaic: compare the Berean form (spelled out) with the Tyndale code, using the key in each file.")
        for ref in refs:
            bv = [r for r in b if r[0] == ref and len(r) > 4 and r[4].startswith("V-")]
            tv = [r for r in t if r[0] == ref and len(r) > 5 and re.match(r"^[HA]V", r[5] or "")]
            for x in bv:
                print("%s  Berean: %s  %s (%s)" % (ref, x[2], x[4], x[6] if len(x) > 6 else ""))
            for y in tv:
                print("%s  Tyndale: %s  %s (%s)" % (ref, y[2], y[5], y[3]))

    print("\n== EDITION DIFFERENCES (report only those that change the translation) ==")
    found = False
    for row in b:
        if len(row) > 7 and row[7].strip():
            print("Berean marks  %s  %s -> %s" % (row[0], row[2], row[7])); found = True
    if is_nt:
        for row in t:
            if len(row) > 6 and row[6] and "NA28" not in row[6]:
                print("Tyndale: not in NA28  %s  %s  (%s)  editions: %s" % (row[0], row[2], row[3], row[6])); found = True
            if len(row) > 7 and row[7].strip():
                print("Tyndale meaning variant  %s  %s  %s" % (row[0], row[2], row[7])); found = True
    else:
        for row in t:
            if len(row) > 6 and row[6].strip():
                print("Tyndale meaning variant  %s  %s  %s" % (row[0], row[2], row[6])); found = True
    if not found:
        print("None marked.")

    print("\n== QUOTES (from the Berean notes; the only source) ==")
    any_quote = False
    for ref in refs:
        for row in xref_rows(ref):
            if row[1].startswith("Berean note (quotes)"):
                any_quote = True
                print("%s quotes %s  [at \"%s\"]" % (ref, row[3], row[2]))
                for group in expand_reflist(row[3]):
                    for g in group:
                        print("    %s\t%s" % (g, bsb().get(g, "")))
            elif row[1].startswith("Berean note (quoted in)"):
                any_quote = True
                print("%s is quoted in %s  [at \"%s\"]" % (ref, row[3], row[2]))
                for group in expand_reflist(row[3]):
                    for g in group:
                        print("    %s\t%s" % (g, bsb().get(g, "")))
    if not is_nt:
        for ref in refs:
            noted = " ".join(r[3] for r in xref_rows(ref) if r[1].startswith("Berean note (quoted in)"))
            for hit in find_quoted(ref):
                if hit in noted:
                    continue
                any_quote = True
                print("%s is quoted in %s" % (ref, hit))
                print("    %s\t%s" % (hit, bsb().get(hit, "")))
    if not any_quote:
        print("None.")
    print("(Print exactly the one verse named. Do not add neighboring verses.)")

    for target in (refs if len(refs) <= 3 else [requested]):
        print("\n== CROSS-REFERENCE MENU for %s (entry number | source | heading | verses) ==" % target)
        for i, row in enumerate(xref_rows(target), 1):
            print("%d. %s | %s | verses: %d" % (i, row[1], row[2], count_verses(row[3])))

    seen = []
    for row in b:
        if len(row) > 5 and row[5] not in seen and re.match(r"^[GH]\d", row[5]):
            seen.append(row[5])
    rend = renderings_for(seen, is_nt)
    totals = {k: len(v) for k, v in rend.items()}
    print("\n== HOW THE BEREAN RENDERS EACH WORD EVERYWHERE (grouped by main word, with counts; use this before rating or ruling out a meaning) ==")
    for number in seen:
        g = group_renderings(rend.get(number, []))
        shown = " | ".join("%s %d" % (k, n) for k, n in g[:14])
        more = "" if len(g) <= 14 else " | (%d more groups, %d uses)" % (len(g) - 14, sum(n for _, n in g[14:]))
        print("%s (%d uses): %s%s" % (number, totals.get(number, 0), shown, more))
    print("\n== LEXICON (every meaning of each word; verse citations are removed to keep it short; read each entry whole. An entry over %d characters is cut and says so. 'uses' is the count in the Berean word tables; RARE means %d or fewer) ==" % (LEX_CAP, RARE))
    for number in seen:
        entries = lex_entries(number)
        n = totals.get(number, 0)
        tag = "uses %d%s" % (n, " RARE: consult 'lookup.py lex %s classical'" % number if n <= RARE and number.startswith("G") else (" RARE" if n <= RARE else ""))
        if not entries:
            print("%s (%s): no lexicon entry (often a name). Second table's meaning: %s. Offer no options beyond this." % (number, tag, tyndale_gloss(number, is_nt) or "none found"))
        shown = set()
        for e in entries:
            body = slim(e[5] if len(e) > 5 else "")
            if body in shown:
                continue
            shown.add(body)
            cut = ""
            if len(body) > LEX_CAP:
                body, cut = body[:LEX_CAP], "  [CUT: run 'lookup.py lex %s' for the rest]" % number
            print("%s (%s) | %s | %s | %s%s" % (e[0], tag, e[1], e[4] if len(e) > 4 else "", body, cut))


SMALL = set("""a an the of to in on by for with from at as and or but that this these those it its is are was were be been being
his her their our your my me him them us you we he she they i who whom whose which what not no do does did has have had will would shall
should may might can could so then than into unto upon out up there here also all any some one own when while let if because how
about over under before after through between among against toward""".split())


def clean(eng):
    return re.sub(r"[\[\]{}]", "", eng).strip().lower()


def group_renderings(engs):
    """Group Berean renderings by their main word. Returns [(label, count)] largest first."""
    freq = Counter()
    toks = []
    for e in engs:
        w = [x for x in re.findall(r"[a-z’']+", e) if x not in SMALL]
        toks.append(w)
        freq.update(set(w))
    groups = Counter()
    for e, w in zip(engs, toks):
        if re.fullmatch(r"[-. v]*", e):
            groups["(left without English)"] += 1
        elif not w:
            groups[e] += 1
        else:
            groups[max(w, key=lambda x: (freq[x], -len(x)))] += 1
    return groups.most_common()


def renderings_for(numbers, is_nt):
    want = set(numbers)
    out = {}
    for name in (["words-nt.txt"] if is_nt else OT_WORDS):
        for line in lines(name):
            p = line.split("\t")
            if len(p) > 6 and p[5] in want:
                out.setdefault(p[5], []).append(clean(p[6]))
    return out


BK = r"(?:[1-3]?[A-Z][a-z]{1,3})"
REF = re.compile(r"(?:\b%s\.\s?\d+[:.]\d+(?:[-–]\d+)?(?:\s*,\s*(?:\d+[:.])?\d+(?![A-Za-z])(?:[-–]\d+)?)*)(?:\s*,\s*)?" % BK)


def slim(body):
    """Drop verse citations from a lexicon entry so the list of meanings is short enough to read whole."""
    body = REF.sub("", body)
    body = re.sub(r"\b(al\.|ll\. with|cf\.)\s*;?", "", body)
    body = re.sub(r"\s+([;:,.])", r"\1", body)
    body = re.sub(r"[:;,]\s*(?=[;/])", "", body)
    body = re.sub(r"(,\s*){2,}", ", ", body)
    return re.sub(r"\s{2,}", " ", body).strip()


def tyndale_gloss(number, is_nt):
    """Fallback meaning for a word the lexicon file lacks (mostly names): the gloss in the second word table."""
    if not is_nt:
        return ""
    key = lex_key(number)
    for line in lines("tyndale-nt.txt"):
        p = line.split("\t")
        if len(p) > 4 and re.match(r"^%s[A-Za-z]?=" % key, p[3]):
            return p[4]
    return ""


LEX_CAP = 5000
RARE = 5
OT_WORDS = ["words-ot-1-genesis-to-ruth.txt", "words-ot-2-samuel-to-song.txt",
            "words-ot-3-isaiah-to-malachi.txt"]


def use_counts(numbers, is_nt):
    want = set(numbers)
    out = Counter()
    for name in (["words-nt.txt"] if is_nt else OT_WORDS):
        for line in lines(name):
            p = line.split("\t", 6)
            if len(p) > 5 and p[5] in want:
                out[p[5]] += 1
    return out


def find_quoted(ref):
    """New Testament (or other) verses whose Berean note names this verse."""
    book, c, v = split_ref(ref)
    hits = []
    for line in lines("cross-references.txt"):
        p = line.split("\t")
        if len(p) < 4 or not p[1].startswith("Berean note (quotes)"):
            continue
        for group in expand_reflist(p[3]):
            if ref in group and p[0] not in hits:
                hits.append(p[0])
    return hits


def cmd_quoted(ref):
    ref = expand(ref)[0]
    hits = find_quoted(ref)
    for row in xref_rows(ref):
        if row[1].startswith("Berean note (quoted in)"):
            for group in expand_reflist(row[3]):
                for g in group:
                    if g not in hits:
                        hits.append(g)
    if not hits:
        print("No Berean note names %s as quoted." % ref)
    for h in hits:
        print("%s is quoted in %s\t%s" % (ref, h, bsb().get(h, "")))


def cmd_uses(number, home=None, start=1):
    m = re.match(r"^([GH])0*(\d+)$", number.strip())
    if not m:
        raise SystemExit("Give a dictionary number such as G399 or H5375.")
    num = "%s%s" % (m.group(1), m.group(2))
    files = (["words-nt.txt"] if num.startswith("G") else
             ["words-ot-1-genesis-to-ruth.txt", "words-ot-2-samuel-to-song.txt",
              "words-ot-3-isaiah-to-malachi.txt"])
    hits = []
    for name in files:
        for line in lines(name):
            p = line.split("\t")
            if len(p) > 6 and p[5] == num:
                hits.append(p)
    verses = OrderedDict()
    for p in hits:
        verses.setdefault(p[0], []).append(re.sub(r"[\[\]{}]", "", p[6]).strip())
    print("Dictionary number %s: used %d times in %d verses." % (num, len(hits), len(verses)))
    print("\nBerean renderings (count):")
    for eng, n in Counter(e.lower() for p in hits for e in [re.sub(r"[\[\]{}]", "", p[6]).strip()]).most_common():
        print("  %d  %s" % (n, eng or "(untranslated)"))
    g = group_renderings([clean(p[6]) for p in hits])
    print("\nGrouped by main word (copy these numbers; they total %d):" % sum(n for _, n in g))
    for k, n in g:
        print("  %d  %s" % (n, k))
    keys = list(verses.keys())
    if home:
        book = split_ref(expand(home)[0])[0]
        keys = [k for k in keys if split_ref(k)[0] == book] + [k for k in keys if split_ref(k)[0] != book]
    start = max(1, int(start))
    chunk = keys[start - 1:start + 19]
    print("\nVerses %d to %d of %d (same book first when a verse was given, then Bible order; keep these numbers). Linked English is in braces:"
          % (start, start + len(chunk) - 1, len(keys)))
    for i, ref in enumerate(chunk, start):
        print("%d. %s {%s}\t%s" % (i, ref, " / ".join(verses[ref]), bsb().get(ref, "")))
    if start + 19 < len(keys):
        print("More: lookup.py uses %s %s%d" % (num, ('"%s" ' % home) if home else "", start + 20))


GREEK_TAG = {"AI": "seen as a whole, in the past", "R": "a completed act that still has effect",
             "I": "ongoing, in the past", "P": "ongoing"}
HIDDEN_OK = ("quote marker", "object pointer", "helper word")
TIERS = ("STRONG:", "LIKELY:", "POSSIBLE:", "UNLIKELY:", "RULED OUT:")


def expected_tag(lang, form):
    """The verb tag the rules require for this form, or None when no single tag is fixed."""
    if lang == "G":
        m = re.match(r"^V-(\d?)([A-Z])([A-Z])", form)
        if not m:
            return None
        tense, mood = m.group(2), m.group(3)
        if tense == "A":
            return GREEK_TAG["AI"] if mood == "I" else "seen as a whole, with no time fixed"
        return GREEK_TAG.get(tense)
    if "Prtcpl" in form:
        return "a state, with no time fixed"
    if "ConsecImperf" in form or "Perf" in form and "Imperf" not in form:
        return "a completed act"
    if "Imperf" in form:
        return "an act not yet complete"
    return None


def cmd_check(spec, path):
    """Test a draft's word lines against the word table. Each draft line starts with the ids of the
    original words it carries, in braces: {w6} 3. **bore** — ...   An added word has {}.
    A hidden word is a line such as: {w10} HIDDEN: quote marker"""
    refs = expand(spec)
    rows = berean_rows(refs)
    n = len(rows)
    faults = []
    placed = {}
    hidden = {}
    nums = []
    depth_ids = None
    with open(path, encoding="utf-8") as fh:
        draft = [l.rstrip("\n") for l in fh if l.strip()]
    for line in draft:
        m = re.match(r"^\{([w\d,\s]*)\}\s*(.*)$", line)
        if not m:
            faults.append("No {word ids} at the start of: %s" % line[:60])
            continue
        ids = [int(x) for x in re.findall(r"w(\d+)", m.group(1))]
        body = m.group(2)
        for i in ids:
            if i < 1 or i > n:
                faults.append("w%d does not exist (the verse has w1 to w%d): %s" % (i, n, body[:50]))
        hm = re.match(r"^HIDDEN:\s*(.+)$", body)
        if hm:
            if not any(k in hm.group(1).lower() for k in HIDDEN_OK):
                faults.append("A word may be hidden only as a quote marker, an object pointer, or a helper word with a note: %s" % body)
            for i in ids:
                hidden.setdefault(i, []).append(body)
            continue
        lm = re.match(r"^(\d+)\.\s+(.*)$", body)
        if not lm:
            faults.append("Not a numbered word line: %s" % body[:60])
            continue
        num, text = int(lm.group(1)), lm.group(2)
        nums.append(num)
        for i in ids:
            placed.setdefault(i, []).append(num)
        if re.search(r"—\s*$", text):
            faults.append("Line %d ends with a dash and nothing after it." % num)
        bm = re.search(r"\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*", text)
        if not bm:
            faults.append("Line %d has no bold word." % num)
            continue
        added = bm.group(1) is not None
        word = (bm.group(1) or bm.group(2)).strip()
        if added and "(added)" not in text:
            faults.append("Line %d is an added word. Write '(added)' right after it." % num)
        if not added and "(added)" in text:
            faults.append("Line %d says (added) but the word is not in bold italics." % num)
        if added and ids:
            faults.append("Line %d is bold italic (added) but carries original word(s) %s." % (num, ", ".join("w%d" % i for i in ids)))
        if not added and not ids:
            faults.append("Line %d is bold (in the original) but carries no original word. If Claude added it, use bold italics." % num)
        opens, closes = text.startswith("("), bool(re.search(r"\*\*\)", text))
        if opens:
            if depth_ids is not None:
                faults.append("Line %d opens a parenthesis before the last one closed." % num)
            depth_ids = set(ids)
        if depth_ids is not None and not added and not (set(ids) & depth_ids):
            faults.append("Line %d is inside parentheses but carries a different original word than the line that opened them." % num)
        if closes:
            if depth_ids is None:
                faults.append("Line %d closes a parenthesis that was never opened." % num)
            depth_ids = None
        arts = [i for i in ids if 1 <= i <= n and len(rows[i - 1]) > 5 and rows[i - 1][5] in ("G3588",) and len(ids) > 1]
        if arts and "[the]" not in text and not re.search(r"\bthe\b", word, re.I):
            faults.append("Line %d carries a Greek 'the' (w%d) but shows neither 'the' nor [the]." % (num, arts[0]))
        if "[the]" in text and not any(1 <= i <= n and rows[i - 1][5] == "G3588" for i in ids):
            faults.append("Line %d shows [the] but carries no Greek 'the'." % num)
        rest = text[bm.end():]
        if any(t in rest for t in TIERS):
            live = rest.split("RULED OUT:")[0]
            opts = [o.strip(" †*").lower() for seg in re.split(r"(?:STRONG|LIKELY|POSSIBLE|UNLIKELY):", live)
                    for o in re.split(r"[|;]", seg.split(" — ")[0])]
            base = re.sub(r"[†*<>]", "", re.sub(r"^the\s+", "", word, flags=re.I)).strip().lower()
            if base not in opts and re.sub(r"[†*<>]", "", word).strip().lower() not in opts:
                faults.append("Line %d: the bold word '%s' does not appear in its own tier." % (num, word))
            if "STRONG:" in live and "LIKELY:" in live:
                faults.append("Line %d has both STRONG and LIKELY. When one option is STRONG, none can be LIKELY." % num)
        for i in ids:
            if 1 <= i <= n and rows[i - 1][4].startswith("V-"):
                want = expected_tag(rows[i - 1][1], rows[i - 1][4])
                if want and want not in text:
                    faults.append("Line %d: the verb (w%d, %s) needs the tag '%s'." % (num, i, rows[i - 1][4], want))
    if depth_ids is not None:
        faults.append("A parenthesis was opened and never closed.")
    for i in range(1, n + 1):
        if i not in placed and i not in hidden:
            r = rows[i - 1]
            faults.append("w%d is missing: %s (%s), Berean English '%s'. Give it a line or list it as hidden." % (i, r[3], r[5], r[6]))
        if i in placed and i in hidden:
            faults.append("w%d is both on a line and listed as hidden." % i)
    if nums and nums != list(range(nums[0], nums[0] + len(nums))):
        faults.append("The line numbers do not run in order without gaps: %s" % nums)
    if faults:
        print("CHECK FAILED: %d fault(s). Fix each one and run the check again." % len(faults))
        for f in faults:
            print("- " + f)
    else:
        print("CHECK PASSED: all %d original words are accounted for on %d lines." % (n, len(nums)))
        print("\n== NOW AUDIT THE OPTIONS. This is the second half of the check. Do it before answering. ==")
        print("For each line below, compare YOUR LINE with the LEXICON entry and the BEREAN renderings.")
        print("1. Every distinct meaning in the lexicon entry must be in a tier or under RULED OUT. Add any that are missing.")
        print("2. Every option you list must come from the lexicon entry or the Berean renderings. Remove any that came from memory.")
        print("3. RULED OUT needs a tested reason: the data shows the meaning never occurs in a setting like this, or the lexicon itself")
        print("   says the meaning needs a form this verse lacks. With no tested reason, move it to UNLIKELY.")
        print("4. Every option before RULED OUT must be able to replace the bold word and still make a sentence.")
        print("5. A rating that rests only on the order of the lexicon entry becomes POSSIBLE.")
        is_nt = BOOKS.index(split_ref(refs[0])[0]) >= 39
        numbers = []
        for r in rows:
            if len(r) > 5 and re.match(r"^[GH]\d", r[5]) and r[5] not in numbers:
                numbers.append(r[5])
        rend = renderings_for(numbers, is_nt)
        by_line = {}
        for line in draft:
            m = re.match(r"^\{([w\d,\s]*)\}\s*(\d+\..*)$", line)
            if m:
                by_line[m.group(2)] = [int(x) for x in re.findall(r"w(\d+)", m.group(1))]
        done = set()
        for text, ids in by_line.items():
            for i in ids:
                number = rows[i - 1][5] if len(rows[i - 1]) > 5 else ""
                if not re.match(r"^[GH]\d", number) or number in ("G3588",) or number in done:
                    continue
                done.add(number)
                print("\nYOUR LINE: %s" % text)
                g = group_renderings(rend.get(number, []))
                print("BEREAN (%d uses): %s" % (len(rend.get(number, [])), " | ".join("%s %d" % (k, c) for k, c in g[:14])))
                entries = lex_entries(number)
                if not entries:
                    print("LEXICON: no entry (often a name). Offer no options beyond the second table's meaning.")
                seen_body = set()
                for e in entries:
                    body = slim(e[5] if len(e) > 5 else "")
                    if body and body not in seen_body:
                        seen_body.add(body)
                        print("LEXICON: %s" % body[:LEX_CAP])
        print("\nWhen the audit is done and the lines are fixed, print the answer. Make its last line exactly:")
        print("Checked: %d words on %d lines." % (n, len(nums)))


def cmd_lex(numbers, classical=False):
    for number in re.split(r"[,\s]+", numbers.strip()):
        if not number:
            continue
        entries = lex_entries(number, classical)
        if not entries:
            print("No entry found for %s." % number)
        for e in entries:
            print(" | ".join(e))
        print()


def cmd_xref(ref, pick=None):
    ref = expand(ref)[0]
    rows = xref_rows(ref)
    if not rows:
        print("No cross-reference entries for %s." % ref)
        return
    if pick is None:
        for i, row in enumerate(rows, 1):
            print("%d. %s | %s | %d verses | %s" % (i, row[1], row[2], count_verses(row[3]), row[3]))
        return
    row = rows[int(pick) - 1]
    print("%s | %s | %s" % (row[1], row[2], ref))
    for group in expand_reflist(row[3]):
        label = group[0] if len(group) == 1 else "%s-%s" % (group[0], group[-1].split(":")[-1])
        print("%s\t%s" % (label, " ".join(bsb().get(g, "") for g in group)))
    print("(If a verse ends mid-sentence, add the next verse with: lookup.py verses \"...\")")


def cmd_tyndale(spec):
    for row in tyndale_rows(expand(spec)):
        print(" | ".join(row))


def cmd_lxx(spec):
    for ref in expand(spec):
        book, c, v = split_ref(ref)
        if book not in LXX:
            print("%s: not an Old Testament book." % ref)
            continue
        code = LXX[book]
        name = "septuagint-1.txt" if code in LXX_FILE_1 else "septuagint-2.txt"
        key = "%s.%d.%d\t" % (code, c, v)
        rows = [l.split("\t") for l in lines(name) if l.startswith(key)]
        print("%s (Septuagint %s.%d.%d): %d words. Numbering can differ from English Bibles, especially in Psalms and Jeremiah."
              % (ref, code, c, v, len(rows)))
        for r in rows:
            print("  " + " | ".join(r[1:]))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "passage":
        cmd_passage(argv[2], argv[3] if len(argv) > 3 else None)
    elif cmd == "verses":
        cmd_verses(argv[2])
    elif cmd == "uses":
        rest = argv[3:]
        home = next((x for x in rest if not x.isdigit()), None)
        start = next((x for x in rest if x.isdigit()), 1)
        cmd_uses(argv[2], home, start)
    elif cmd == "check":
        if len(argv) < 4:
            raise SystemExit('Use: lookup.py check "1 Peter 2:24" draft.txt')
        cmd_check(argv[2], argv[3])
    elif cmd == "lex":
        cmd_lex(argv[2], len(argv) > 3 and argv[3] == "classical")
    elif cmd == "xref":
        cmd_xref(argv[2], argv[3] if len(argv) > 3 else None)
    elif cmd == "quoted":
        cmd_quoted(argv[2])
    elif cmd == "lxx":
        cmd_lxx(argv[2])
    elif cmd == "tyndale":
        cmd_tyndale(argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
