import os
import sys
import textbase
import re
import sqlite3
import gzip
from tqdm import tqdm


def hier(data, n):
    if n not in data:
        return
    obj = data.get(n)
    nn = obj["N"][0]
    yield nn
    for C in obj.get("C", []):
        for CC in hier(data, C):
            yield CC
    for k in obj.get("K", {"S": []})["S"]:
        yield f"{nn}(+{k})"


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


class TextNotFoundException(Exception):
    pass


def lookup_text(n, txts, kwds):
    if not n:
        return ""
    # Handle the Keys (+ etc. )
    tmp = n.split("(+")
    if len(tmp) == 2:
        base, key = tmp
        if key.endswith(")"):
            key = key[:-1]
    else:
        base = tmp[0]
        key = ""  # It has to be '' and not None so that we can do a len('')
        # and get 0 for key-children selection later on

    # is this a valid base object?
    obj = notations.get(base)
    if not obj:
        return ""
    base_t = txts.get(base, "") + " " + kwds.get(base, "")
    obj_t = base_t
    if key:
        obj_key = obj.get("K")
        # This object should have K and S keys
        if key in obj_key.get("S", []):
            lookup_k = obj_key["K"][0] + key
            t2 = txts.get(lookup_k, "") + " " + kwds.get(lookup_k, "")
            if t2:
                obj_t = f"{base_t} {t2}"
            else:
                raise TextNotFoundException(n)
    return f"{n} {obj_t}"
    # buf = []
    # for x in obj_t:
    #     if x in "-():[].,":
    #         x = " "
    #     buf.append(x)

    # return f"{n} {''.join(buf)}"


def read_n(filename):
    d = {}
    for x in textbase.parse(filename):
        n = x.get("N")
        if n:
            d[n[0]] = x
        k = x.get("K")
        if k:
            kk = keys.get(k[0])
            if kk:
                x["K"] = kk
            else:
                del x["K"]
    return d


def read_k(filename):
    d = {}
    for x in textbase.parse(filename):
        k = x.get("K")
        if k:
            d[k[0]] = x
    return d


def read_txt(lang, kw_or_text):
    d = {}
    langpath = os.path.join(kw_or_text, lang)
    for filename in os.listdir(langpath):
        filepath = os.path.join(langpath, filename)
        if not filepath.lower().endswith(".txt"):
            continue
        with open(filepath, "rt", encoding="utf8") as input_file:
            for lineno, line in enumerate(input_file.read().split("\n")):
                if line.startswith("#"):
                    continue
                tmp = line.split("|")
                if len(tmp) != 2:
                    continue
                notation, txt = tmp
                if notation in d:
                    d[notation] = d[notation] + "\n" + txt
                else:
                    d[notation] = txt
    return d


def index(lang, lang_name, prime_content=False):
    txts = read_txt(lang, "txt")
    kwds = read_txt(lang, "kw")
    all_notations = list(enumerate(set(hier(notations, ""))))

    Z = []
    with sqlite3.connect("iconclass_index.sqlite") as index_db:
        index_db.enable_load_extension(True)
        index_db.load_extension("/usr/local/lib/fts5stemmer")
        ci = index_db.cursor()

        ci.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {lang}  USING fts5(notation UNINDEXED, is_key, text, tokenize = 'snowball {lang_name} unicode61', content=notations)"
        )
        ci.execute(
            f"CREATE TABLE IF NOT EXISTS notations (id integer primary key, notation , is_key, text)"
        )

        batch = []
        for row_id, n in tqdm(all_notations):
            try:
                t = "\n".join([lookup_text(part, txts, kwds) for part in get_parts(n)])
            except TypeError:
                print(f"Error {n}")
                continue
            except TextNotFoundException:
                continue
            is_key = 0 if n.find("(+") < 0 else 1
            tt = (row_id + 1, n, is_key, t)
            batch.append(tt)
            Z.append((row_id + 1, n, is_key, None))
            if len(batch) > 99999:
                ci.executemany(
                    f"INSERT INTO {lang}(rowid, notation, is_key, text) VALUES (?, ?, ?, ?)",
                    batch,
                )
                batch = []
        ci.executemany(
            f"INSERT INTO {lang}(rowid, notation, is_key, text) VALUES (?, ?, ?, ?)",
            batch,
        )

        if prime_content:
            ci.executemany(f"INSERT INTO notations VALUES (?, ?, ?, ?)", Z)

        ci.execute("CREATE TABLE IF NOT EXISTS txts (notation, lang, txt)")
        ci.execute("CREATE INDEX IF NOT EXISTS txts_notation ON txts (notation)")
        ci.execute("CREATE TABLE IF NOT EXISTS kwds (notation, lang, kw)")
        ci.execute("CREATE INDEX IF NOT EXISTS kwds_notation ON kwds (notation)")
        ci.executemany(
            "INSERT INTO txts VALUES (?, ?, ?)", [(k, lang, v) for k, v in txts.items()]
        )
        ci.executemany(
            "INSERT INTO kwds VALUES (?, ?, ?)", [(k, lang, v) for k, v in kwds.items()]
        )


LANGUAGE_MAP = {
    "en": "english",
    "de": "german",
    "it": "italian",
    "fr": "french",
    "nl": "dutch",
    "fi": "finnish",
    "pt": "portuguese",
}

keys = read_k("keys.txt")
# if we first read the keys, we can add references in the notations...
notations = read_n("notations.txt")
notations[""] = {"C": [str(x) for x in range(10)], "N": ["ICONCLASS"]}

if __name__ == "__main__":
    lang = sys.argv[1]
    index(lang, LANGUAGE_MAP[lang], lang == "en")
