import sys, os
import textbase
from urllib.parse import quote
from rich.progress import track


def read_n(filename, keys):
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
        # Suppress the q of Keys here, this need to be double-checked with JPJB
        suffixes = [s for s in x.get("S", []) if s.find("q") < 0]
        if k and suffixes:
            x["S"] = suffixes
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


class IC:
    def __init__(self, lang="en"):
        self.keys = read_k("keys.txt")
        self.notations = read_n("notations.txt", self.keys)
        self.notations[""] = {"C": [str(x) for x in range(10)], "N": ["ICONCLASS"]}
        self.txts = read_txt(lang, "txt")
        self.kwds = read_txt(lang, "kw")


def text(ic, filename):
    F = open(filename, "w")
    for obj in track(ic.notations.values()):
        nn = obj["N"][0]
        uri = f"http://iconclass.org/{quote(nn)}"
        t = ic.txts.get(nn)
        F.write(f'<{uri}> <http://www.w3.org/2004/02/skos/core#prefLabel> "{t}"@en.\n')

        kprefix = obj.get("K", {}).get("K", [None])[0]
        if not kprefix:
            continue
        for k in obj.get("K", {}).get("S", []):
            kt = ic.txts.get(kprefix + k)
            if not kt:
                continue
            lastk = f"{nn}(+{k})"
            kuri = f"http://iconclass.org/{quote(lastk)}"
            F.write(
                f'<{kuri}> <http://www.w3.org/2004/02/skos/core#prefLabel> "{t} (+ {kt})"@en .\n'
            )
    F.close()


def structure(ic, filename):
    F = open(filename, "w")
    for obj in track(ic.notations.values()):
        nn = obj["N"][0]
        uri = f"http://iconclass.org/{quote(nn)}"
        F.write(
            f"<{uri}> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/2004/02/skos/core#Concept> .\n"
        )
        F.write(
            f"<{uri}> <http://www.w3.org/2004/02/skos/core#inScheme> <https://iconclass.org/rdf/2021/09/> .\n"
        )
        F.write(f'<{uri}> <http://www.w3.org/2004/02/skos/core#notation> "{nn}" .\n')

        for c in obj.get("C", []):
            curi = f"http://iconclass.org/{quote(c)}"
            F.write(
                f"<{uri}> <http://www.w3.org/2004/02/skos/core#narrower> <{curi}> .\n"
            )
            F.write(
                f"<{curi}> <http://www.w3.org/2004/02/skos/core#broader> <{uri}> .\n"
            )

        for r in obj.get("R", []):
            ruri = f"http://iconclass.org/{quote(r)}"
            F.write(
                f"<{uri}> <http://www.w3.org/2004/02/skos/core#related> <{ruri}> .\n"
            )

        for k in obj.get("K", {}).get("S", []):
            thek = ""
            theuri = nn
            for kk in k:
                thek = thek + kk
                lastk = f"{nn}(+{thek})"
                kuri = f"http://iconclass.org/{quote(lastk)}"
                nuri = f"http://iconclass.org/{quote(theuri)}"
                F.write(
                    f"<{nuri}> <http://www.w3.org/2004/02/skos/core#narrower> <{kuri}> .\n"
                )
                F.write(
                    f"<{kuri}> <http://www.w3.org/2004/02/skos/core#broader> <{nuri}> .\n"
                )
                theuri = lastk
    F.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            f"""
Usage:
------

To print out the SKOS structural triples
  {sys.argv[0]} struct
To print out the textual triples
  {sys.argv[0]} text
"""
        )
        sys.exit(1)
    if sys.argv[1] == "struct":
        structure(IC(), "iconclass_structure_skos.nt")
    elif sys.argv[1] == "text":
        text(IC(), "iconclass_text_skos.nt")
