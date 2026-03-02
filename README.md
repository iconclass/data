# ICONCLASS

Please use the following to cite:

```
H. van de Waal, Iconclass, an iconographic classification system. Completed and edited by L.D. Couprie, E. Tholen & G. Vellekoop. (Amsterdam, 1972-1985). online edition by E. Posthumus & J.P.J. Brandhorst, 2024. https://iconclass.org/
```

[![DOI](https://zenodo.org/badge/350851584.svg)](https://zenodo.org/badge/latestdoi/350851584)

A multilingual subject classification system for cultural content
For more information see: http://www.iconclass.org/

Made by Hans Brandhorst <jpjbrand@xs4all.nl> & Etienne Posthumus <eposthumus@gmail.com>

    ...with lots of support from a global cast of many, many people since 1972.

## Data file

This repository contains the main data files for the ICONCLASS system. It is a collection of simple structured text files, dating back in concept to the late nineties of the previous century.

### Structure

The structure is determined by the file `notations.txt`.

For example, the file looks like:

```
N 1
C 10
; 11
; 12
; 13
; 14
$
N 10
$
```

This is a chunk of data (each chunk is separated by a single $ character on its own line)
The first part of a line, up to the first space, is the field name. If there are multi-valued fields, in other words, more than one value for a field, it is listed on a different line starting with a `;` character,followed by a space and the field value. The above snippet, is roughly equivalent to the following JSON value:

```javascript
[
    {N: "1",
     C: ["10", "11", "12", "13", "14"]},
    {N: "10}
]
```

## Why not use a standard Knowledge Management System?

You might wonder why we can not simply use a standard system to manage vocabularies or classification systems. If IC has a SKOS version, surely we can just use a SKOS editor?

Alas, no. The ["base" ICONCLASS system](notations.txt) has around 40K nodes arranged in a tree. But then there are several "sub-trees" that are switched on and off at various parts of the base tree. These so-called "keys" in the IC causes an explosion to more than 1 million nodes in the system, which would make it very [tricky to maintain in a traditional system](https://iconclass.org/help/skos_sparql).

![Keys to 25F](/misc/key_to_25F.jpg)

A further complication is the use of WITH-NAMES placeholders in tree, also known as _bracketed text_. These notations look like 11H(...) where the ... can be filled in with any valid entry that makes sense to the user using that particular node in the tree. In the example, 11H(...) are male saints, so that could be 11H(JOHN) - but this could be in any language or variant. In the printed volumes for IC, several entries were already filled in as a convenience, and over the years some items have been added to the "official" list.

This also causes a problem when we create static _dumps_ of the IC system, for example in RDF as it creates very large files.

## Dual-agent corpus builder specification assets

This repository now includes a concrete architecture package for a batch-first **WebScout → IconoCode** pipeline:

- Architecture and operational defaults: `docs/spec-1/dual-agent-corpus-builder.md`
- JSON contracts: `schemas/*.schema.json`
- PostgreSQL MVP migration: `sql/migrations/0001_dual_agent_corpus.sql`

These files are intended as implementation scaffolding for evidence-traceable corpus construction with ABNT-ready source output.
