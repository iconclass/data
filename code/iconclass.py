import os, re, sys, json, sqlite3

__version__ = 0.9
__description__ = "sqlite driven, source files from texts in ../data/ "

WITH_NAME_MATCH = re.compile(r"\((?!\.\.\.)[^+]+\)")
BRACKETS = re.compile(r"\([\w ]+?\)")
SPLITTER = re.compile(r"(\(.+?\))")


def dump_dbtxt(obj):
    buf = []
    ba = buf.append
    ba("N %s" % obj["n"])
    ba("P %s" % "\n; ".join(obj["p"]))
    if "k" in obj:
        ba("K %s" % obj["k"])
    if "c" in obj:
        ba("C %s" % "\n; ".join(obj["c"]))
    if obj.get("r"):
        ba("R %s" % "\n; ".join(obj["r"]))
    for lang, txt in obj.get("txt").items():
        ba("T_%s %s" % (lang, txt))
    for lang, kws in obj.get("kw").items():
        ba("K_%s %s" % (lang, "\n; ".join(kws)))
    return "\n".join(buf)


def get_parts(a):
    "Split an ICONCLASS notation up into a list of its parts"
    SPLITTER = re.compile(r"(\(.+?\))")
    p = []
    lastp = ""
    for p1 in SPLITTER.split(a):
        if p1.startswith("(+"):
            tmplastp = lastp + "(+"
            for x in p1[2:]:
                if x and x != ")":
                    p.append(tmplastp + x + ")")
                    tmplastp += x
            lastp = p[-1]
        elif p1.startswith("(") and p1.endswith(")"):
            if p1 != "(...)":
                p.append(lastp + "(...)")
            p.append(lastp + p1)
            lastp = p[-1]
        else:
            for x in range(len(p1)):
                p.append(lastp + p1[x])
                if p:
                    lastp = p[-1]
    return p


def fill_obj(obj):
    """For the specified notation return an object with the children and path filled as objects
    >>> Z = get_filled_obj

    >>> o = Z('1')
    >>> sorted([x['n'] for x in o['c']])
    [u'10', u'11', u'12', u'13', u'14']
    
    And it must also work for arb keys.
    >>> t = Z('11(+1)')
    >>> sorted([x['n'] for x in t['c']])
    [u'11(+11)', u'11(+12)', u'11(+13)']
    >>> Z('XYZ')
    Traceback (most recent call last):
            ...
    NotationNotFoundException: 'XYZ'
    
    If there are no kids found, the returned obj must have an empty 'c' key    
    >>> l = Z('0')
    >>> l['c']
    []
    
    >>> a = Z('96C')
    >>> [x['n'] for x in a['p']]
    [u'9', u'96']
    
    """
    if not obj:
        return

    kids = filter(None, [get(c) for c in obj.get("c", [])])
    path = filter(None, [get(p) for p in obj.get("p", [])])
    sysrefs = filter(None, [get(r) for r in obj.get("r", [])])
    obj["c"] = kids
    obj["p"] = path
    obj["r"] = sysrefs

    return obj


def get(notation):
    return get_list([notation])[0]


def get_list(notations):
    if not notations:
        return []
    buf = {}
    # We also retrieve the WITH_NAMES (...) for all entries
    # This is in case of user-supplied WITH-NAMES (eg. 11H(FOO)(+1) ) which also includes keys
    # We can't just do them if the notation returns a None, as keys need to be expanded too...
    for notation in notations:
        obj = fetch_from_db(notation)
        if not obj and WITH_NAME_MATCH.search(notation):
            notation_with_name = WITH_NAME_MATCH.sub("(...)", notation)
            obj = fetch_from_db(notation_with_name)
            if obj:
                obj["n"] = notation
                bracketed_text = WITH_NAME_MATCH.search(notation).group()
                # Also replace any (...) in the txts with the part in the notation
                tmp = {}
                for lang, txt in obj.get("txt", {}).items():
                    tmp[lang] = BRACKETS.sub(bracketed_text, txt)
                obj["txt"] = tmp
                tmp = []
                # Can we also remove the children that belong to the (...) parent?
                # And fix the children notations
                for kind in obj.get("c", []):
                    if kind.find("+") > 0 or not kind.endswith(")"):
                        # what form are the kids stored in, UTF8 ?
                        tmp.append(kind.replace("(...)", bracketed_text))
                obj["c"] = tmp
        if obj:
            buf[obj["n"]] = obj

    return [buf.get(x) for x in notations]


def fetch_from_db(notation):
    ICONCLASS_DB_LOCATION = os.environ.get("ICONCLASS_DB_LOCATION", "iconclass.sqlite")
    if not os.path.exists(ICONCLASS_DB_LOCATION):
        # If the DB does not exist, try to get the latest file from https://iconclass.org/DB
        ICONCLASS_DB_URL = os.environ.get(
            "ICONCLASS_DB_URL", "http://iconclass.org/c877d0f9abd2575464dba10fef4fc356"
        )
        print(
            f"Iconclass DB not found at {ICONCLASS_DB_LOCATION} downloading from {ICONCLASS_DB_URL} "
        )
        from urllib.request import urlopen
        import hashlib

        datafile = urlopen(ICONCLASS_DB_URL).read()
        open(ICONCLASS_DB_LOCATION, "wb").write(datafile)

    db = sqlite3.connect(ICONCLASS_DB_LOCATION)
    cursor = db.cursor()

    # Handle the Keys (+ etc. )
    tmp = notation.split("(+")
    if len(tmp) == 2:
        base, key = tmp
        if key.endswith(")"):
            key = key[:-1]
    else:
        base = tmp[0]
        key = ""  # It has to be '' and not None so that we can do a len('')
        # and get 0 for key-children selection later on

    obj = {}
    SQL = "SELECT N.children, N.refs, N.key, type, language, text FROM notations as N LEFT JOIN texts ON N.id = texts.ref WHERE notation = ?"
    cursor.execute(SQL, (base,))
    for children, refs, nkeycode, txt_type, language, text in cursor.fetchall():
        if children:
            obj["c"] = children and children.split("|") or []
        if nkeycode:
            obj["k"] = nkeycode
        if refs:
            obj["r"] = refs and refs.split("|") or []
        if txt_type == 0:
            obj.setdefault("txt", {})[language] = text
        if txt_type == 1:
            obj.setdefault("kw", {}).setdefault(language, []).append(text)

    if not obj:
        return None

    obj["n"] = base
    keycode = obj.get("k")
    if keycode:
        SQL = "SELECT type, language, text FROM keys AS K LEFT JOIN texts ON K.id = texts.ref WHERE k.code = ? AND k.suffix = ?"
        cursor.execute(SQL, (keycode, key))
        fetched_keys = False
        for txt_type, lang, k_txt in cursor.fetchall():
            fetched_keys = True
            if txt_type == 0:
                obj_txt = obj.get("txt", {}).get(lang)
                new_txt = "%s (+ %s)" % (obj_txt, k_txt)
                obj.setdefault("txt", {})[lang] = new_txt
            if txt_type == 1:
                obj.setdefault("kw", {}).setdefault(language, []).append(k_txt)

        # If there was a key in the requested notation, but no keys retrieved, bail
        if key and not fetched_keys:
            return None

        if key:
            # Fix the notation
            obj["n"] = "%s(+%s)" % (obj["n"], key)

        # Make sure that all the keywords are unique, might be duplicated by keys
        for lang, keywords in obj.get("kw", {}).items():
            obj["kw"][lang] = list(sorted(keywords))

    if keycode:
        # # Fix the children
        cursor.execute("SELECT suffix FROM keys WHERE code = ?", (keycode,))
        new_kids = set()
        for (kk,) in cursor.fetchall():
            if kk.startswith(key) and len(kk) == (len(key) + 1):
                new_kids.add("%s(+%s)" % (base, kk))
        if key:
            obj["c"] = sorted(new_kids)
        else:
            obj["c"] = obj.get("c", []) + sorted(new_kids)

    obj["p"] = get_parts(notation)
    if "k" in obj:
        del obj["k"]
    return obj


def add_space(a):
    """For a given unicode string @notation
    Add some spaces according to the ICONCLASS rules as commonly used in DE
    See tests for examples
    """
    if len(a) < 3:
        return a
    if a[1:3] == "(+":
        tip = a[0]
        start = 1
    elif (a[2:4] == "(+") or (a[2] == "(" and a[3] != "+"):
        tip = a[:2]
        start = 2
    else:
        tip = "%s %s" % (a[:2], a[2])
        if len(a) == 3:
            return tip.strip()
        if len(a) == 4 and a[2] == a[3]:
            return "%s %s" % (a[:2], a[2:4])
        start = 3
        if a[2] == a[3]:
            start = 4
            tip = "%s %s" % (a[:2], a[2:4])
    inbracket, inkey, parts, s = False, False, [tip], ""
    for idx, x in enumerate(a[start:]):
        if x == " " and not inbracket:
            continue
        if x == "(":
            inbracket = True
            parts.append(s)
            s = ""
        s += x
        if x == "+" and inbracket:
            inkey = True
            inbracket = False
        if x == ")":
            inbracket = False
            inkey = False
            parts.append(s)
            s = ""
        if len(s) >= 2 and not inbracket:
            parts.append(s)
            s = ""
    parts.append(s)
    tmp = []
    for idx, x in enumerate(parts):
        if not x or x == " ":
            continue
        if idx < (len(parts) - 1) and parts[idx + 1] == ")":
            tmp.append(x)
        else:
            tmp.append("%s " % x if x != "(+" else x)
    return "".join(tmp).strip()


def filter_inputs(input_filename, output_filename):
    f = open(input_filename).readlines()
    ff = sorted([x.strip().strip('"') for x in f[1:]])[4:]
    fetched = [(x, get(x)) for x in ff]
    notfetched = [x for x in fetched if not x[1]]
    with open(output_filename, "w") as F:
        for n in notfetched:
            F.write("%s\n" % n)
        for n, t in fetched:
            if not t:
                continue
            F.write("%s\t%s\n" % (n, t["txt"]["en"].encode("utf8")))


def descend(notation):
    try:
        obj = get(notation)
    except:
        return
    if not obj:
        return
    yield obj
    for c in obj.get("c", []):
        for cc in descend(c):
            yield cc


def hier(notation):
    try:
        obj = get(notation)
    except:
        return
    if not obj:
        raise Exception("Object %s does not exist" % notation)
    print("\r%20s\t%s\r" % (notation, obj.get("txt", {}).get("en")[:90]))
    for c in obj.get("c", []):
        hier(c)


def children_iterator(notation):
    obj = get(notation)
    if not obj:
        return
    yield obj
    for k in obj.get("c", []):
        for kk in children_iterator(k):
            yield kk


if __name__ == "__main__":
    if len(sys.argv) > 1:
        start = sys.argv[1]
        hier(start)
