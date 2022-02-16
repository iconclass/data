import os
from urllib.parse import quote_plus
import textbase
from rich import print
from rich.progress import track
from rdflib import Namespace
from rdflib.namespace import DC, SKOS, RDF
from rdflib import Graph, URIRef, Literal


def set_parents(objs: dict):
    for n, obj in track(objs.items()):
        for c in obj.get("C", []):
            c_obj = objs.get(c)
            if not c_obj:
                print(c)
            else:
                c_obj["B"] = n


def main():
    ic = {}
    for obj in track(textbase.parse("notations.txt")):
        ic[obj["N"][0]] = obj
    set_parents(ic)
    for dirpath, dirs, files in os.walk("txt"):
        for filename in files:
            if not filename.startswith("txt_"):
                continue
            lang, txts = read_texts(os.path.join(dirpath, filename))
            # import pdb

            # pdb.set_trace()
            for notation, txt in txts:
                if notation not in ic:
                    print(filename, notation)
                else:
                    ic[notation].setdefault("txt", {})[lang] = txt
    return ic


def read_texts(filename):
    if filename[4:6] not in (
        "en",
        "de",
        "fr",
        "it",
        "fi",
        "nl",
        "pt",
        "zh",
        "jp",
        "hu",
        "pl",
    ):
        return None, []
    lang = filename[4:6]
    buf = []
    with open(filename, "rt", encoding="utf8") as input_file:
        for line in input_file.read().split("\n"):
            if line.startswith("#"):
                continue
            line = line.strip()
            tmp = line.split("|")
            if len(tmp) != 2:
                continue
            notation, txt = tmp
            buf.append((notation, txt))
        print(f"Read {len(buf)} for {lang} in {filename}")
    return lang, buf


def dump(ic):

    g = Graph()
    IC = Namespace("http://iconclass.org/")
    g.bind("ic", IC)
    g.bind("rdf", RDF)
    g.bind("skos", SKOS)

    def ga(*kw):
        s, p, o = kw
        g.add((s, p, o))

    for n, obj in track(ic.items()):
        N = URIRef(IC[quote_plus(n)])
        ga(N, RDF.type, SKOS.Concept)
        ga(N, SKOS.notation, Literal(n))
        ga(N, SKOS.inScheme, URIRef("http://iconclass.org/rdf/2011/09/"))
        for lang, txt in obj.get("txt", {}).items():
            ga(N, SKOS.prefLabel, Literal(txt, lang=lang))

        b = obj.get("B")
        if b:
            ga(N, SKOS.broader, IC[quote_plus(b)])
        for c in obj.get("C", []):
            ga(N, SKOS.narrower, IC[quote_plus(c)])
        for r in obj.get("R", []):
            ga(N, SKOS.related, IC[quote_plus(r)])

        # TODO add DC.subject for the keyswords
    return g


if __name__ == "__main__":
    ic = main()
    thegraph = dump(ic)
    open("iconclass.ttl", "w").write(thegraph.serialize())
