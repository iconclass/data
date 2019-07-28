import sqlite3
import os

SCHEMA = ['''CREATE TABLE IF NOT EXISTS "notations" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"notation" TEXT,
	"children" TEXT,
	"refs" TEXT,
	"key" TEXT
	)''',
	          '''CREATE TABLE IF NOT EXISTS "keys" (
	"id" INTEGER PRIMARY KEY AUTOINCREMENT,
	"code" TEXT,
	"suffix" TEXT
	)''',
	          '''CREATE TABLE IF NOT EXISTS "texts" (
	"ref" INTEGER,
	"type" INTEGER,
	"language" TEXT,
	"text" TEXT
	)''',
	'''CREATE INDEX IF NOT EXISTS "texts_ref" ON "texts" ("ref")''',
	'''CREATE INDEX IF NOT EXISTS "notations_notation" ON "notations" ("notation")'''
	'''CREATE INDEX IF NOT EXISTS "keys_code" ON "keys" ("code")''',
]


def parse_dbtxt(data):
    obj = {}
    buf = []
    last_field = None
    for line in data.split('\n'):
        if line.startswith('#'):
            continue
        data = line.split(' ')
        if len(data) < 2:
            continue
        field = data[0].lower()
        data = ' '.join(data[1:])
        if field == ';':
            buf.append(data)
        elif field != last_field:
            if buf:
                obj[last_field] = buf
            buf = [data]
            last_field = field
        if field in ('n', 'k', 'code', 'suffix'):
            buf = buf[0]
    if buf:
        obj[last_field] = buf

    for k, v in obj.copy().items():
        if k.startswith('txt_'):
            obj.setdefault('txt', {})[k[4:]] = v
            del obj[k]
        if k.startswith('kwd_'):
            obj.setdefault('kw', {})[k[4:]] = v
            del obj[k]
    return obj


def read_notations(filename, cursor):
    print("Reading notations")
    rowid = 1
    INSERT_SQL = 'INSERT INTO notations VALUES (?, ?, ?, ?, ?)'
    notation_ids = {}
    with open(filename, 'rt', encoding='utf8') as input_file:
        for chunk in input_file.read().split('\n$'):
            obj = parse_dbtxt(chunk)
            notation = obj.get('n')
            children = '|'.join(obj.get('c', [])) or None
            refs = '|'.join(obj.get('r', [])) or None
            key = obj.get('k')
            if notation:
                data = (rowid, notation, children, refs, key)
                cursor.execute(INSERT_SQL, data)
                notation_ids[notation] = rowid
                rowid += 1
    return notation_ids


def read_texts(txt_type, notation_ids, filename, language, cursor):
    print("Reading %s texts from %s" % (language, filename))
    INSERT_SQL = 'INSERT INTO texts (ref, type, language, text) VALUES (?, %s, ?, ?)' % txt_type
    with open(filename, 'rt', encoding='utf8') as input_file:
        for line in input_file.read().split('\n'):
            if line.startswith('#'):
                continue
            line = line.strip()
            tmp = line.split('|')
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
    INSERT_SQL1 = 'INSERT INTO keys (id, code, suffix) VALUES (?, ?, ?)'
    INSERT_SQL2 = 'INSERT INTO texts (ref, type, language, text) VALUES (?, ?, ?, ?)'

    with open(filename, 'rt', encoding='utf8') as input_file:
        for chunk in input_file.read().split('\n$'):
            row_id += 1

            obj = parse_dbtxt(chunk)
            code = obj.get('code')
            suffix = obj.get('suffix')
            if not code and suffix:
                continue
            data = (row_id, code, suffix)
            cursor.execute(INSERT_SQL1, data)
            notation_ids[code] = row_id

            # And also insert the texts and keywords
            for language, v in obj.get('txt', {}).items():
                for vv in v:
                    data = (row_id, 0, language, vv)
                    cursor.execute(INSERT_SQL2, data)
            for language, v in obj.get('kw', {}).items():
                for vv in v:
                    data = (row_id, 1, language, vv)
                    cursor.execute(INSERT_SQL2, data)


if __name__ == '__main__':
    db = sqlite3.connect('iconclass.sqlite')
    cursor = db.cursor()
    for statement in SCHEMA:
        cursor.execute(statement)

    # Read the structure
    notation_ids = read_notations('notations.txt', cursor)

    # Read the texts
    for dirpath, dirs, files in os.walk('.'):
        for filename in files:
            if filename.startswith('kw_'):
                language = filename[3:5]
                read_texts(1, notation_ids, os.path.join(
                    dirpath, filename), language, cursor)
            elif filename.startswith('txt_'):
                language = filename[4:6]
                read_texts(0, notation_ids, os.path.join(
                    dirpath, filename), language, cursor)

    # read the keys
    read_keys(notation_ids, 'keys.txt', cursor)

    db.commit()
