import sqlite3
import os
import traceback
import sys

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS "notations" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"notation" TEXT,
	"children" TEXT,
	"refs" TEXT,
	"key" TEXT
	)""",
    """CREATE TABLE IF NOT EXISTS "keys" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"code" TEXT,
	"suffix" TEXT
	)""",
    """CREATE TABLE IF NOT EXISTS "texts" (
	"ref" INTEGER,
	"type" INTEGER,
	"language" TEXT,
	"text" TEXT
	)""",
    """CREATE INDEX IF NOT EXISTS "texts_ref" ON "texts" ("ref")""",
    """CREATE INDEX IF NOT EXISTS "notations_notation" ON "notations" ("notation")""",
    """CREATE INDEX IF NOT EXISTS "keys_code" ON "keys" ("code")""",
]


def parse_dbtxt(data):
    obj = {}
    buf = []
    last_field = None
    for line in data.split("\n"):
        if line.startswith("#"):
            continue
        data = line.split(" ")
        if len(data) < 2:
            continue
        field = data[0].lower()
        data = " ".join(data[1:])
        if field == ";":
            buf.append(data)
        elif field != last_field:
            if buf:
                obj[last_field] = buf
            buf = [data]
            last_field = field
        if field in ("n", "k"):
            buf = buf[0]
    if buf:
        obj[last_field] = buf

    for k, v in obj.copy().items():
        if k.startswith("txt_"):
            obj.setdefault("txt", {})[k[4:]] = v
            del obj[k]
        if k.startswith("kwd_"):
            obj.setdefault("kw", {})[k[4:]] = v
            del obj[k]
    return obj


def read_notations(filename, cursor):
    print("Reading notations")
    rowid = 1
    INSERT_SQL = "INSERT INTO notations VALUES (?, ?, ?, ?, ?)"
    notation_ids = {}
    with open(filename, "rt", encoding="utf8") as input_file:
        for lineno, chunk in enumerate(input_file.read().split("\n$")):
            try:
                obj = parse_dbtxt(chunk)
            except:
                print(
                    f"Problem with notations in {filename} on line {lineno}: {repr(chunk)}"
                )
                return None
            notation = obj.get("n")
            children = "|".join(obj.get("c", [])) or None
            refs = "|".join(obj.get("r", [])) or None
            key = obj.get("k")
            if notation:
                data = (rowid, notation, children, refs, key)
                cursor.execute(INSERT_SQL, data)
                notation_ids[notation] = rowid
                rowid += 1
    return notation_ids


def read_texts(txt_type, notation_ids, filename, language, cursor):
    print("Reading %s texts from %s" % (language, filename))
    INSERT_SQL = (
        "INSERT INTO texts (ref, type, language, text) VALUES (?, %s, ?, ?)" % txt_type
    )
    with open(filename, "rt", encoding="utf8") as input_file:
        for line in input_file.read().split("\n"):
            if line.startswith("#"):
                continue
            line = line.strip()
            tmp = line.split("|")
            if len(tmp) != 2:
                continue
            notation, txt = tmp
            ref = notation_ids.get(notation)
            if not ref:
                continue
            data = (ref, language, txt)
            cursor.execute(INSERT_SQL, data)


def read_keys(notation_ids, filename, cursor):
    print("Reading keys")
    # get the maximum row id for notations
    # the keys id should start from the maximum notation ids plus 1
    # as the texts table have infor on both notations and keys
    row_id = max(notation_ids.values())
    INSERT_SQL1 = "INSERT INTO keys (id, code, suffix) VALUES (?, ?, ?)"

    keys_ids = {}
    with open(filename, "rt", encoding="utf8") as input_file:
        for chunk in input_file.read().split("\n$"):
            obj = parse_dbtxt(chunk)
            code = obj.get("k")
            for suffix in obj.get("s", []):
                row_id += 1
                data = (row_id, code, suffix)
                cursor.execute(INSERT_SQL1, data)
                keys_ids[f"{code}{suffix}"] = row_id
            notation_ids[code] = row_id
            
    return keys_ids

if __name__ == "__main__":
    db = sqlite3.connect("iconclass.sqlite")
    cursor = db.cursor()
    for statement in SCHEMA:
        try:
            cursor.execute(statement)
        except sqlite3.OperationalError:
            traceback.print_exc()
            print("Problem with ---> [", end="")
            print(statement, end="")
            print("]")
            sys.exit(1)

    # Read the structure
    notation_ids = read_notations("notations.txt", cursor)
    if not notation_ids:
        sys.exit(1)

    # read the keys
    keys_ids = read_keys(notation_ids, "keys.txt", cursor)

    # Read the texts
    for dirpath, dirs, files in os.walk("."):
        for filename in files:
            if filename.find("_keys") > 0:
                thebuf = keys_ids
            else:
                thebuf = notation_ids

            if filename.startswith("kw_"):
                language = filename[3:5]
                read_texts(
                    1, thebuf, os.path.join(dirpath, filename), language, cursor
                )
            elif filename.startswith("txt_"):                
                language = filename[4:6]
                read_texts(
                    0, thebuf, os.path.join(dirpath, filename), language, cursor
                )


    db.commit()
