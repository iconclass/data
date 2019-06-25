import json
import os
import re
import sys
from typing import List, Dict, Tuple, Callable, Union, Optional, Iterator, Any

import redis

redis_c = redis.StrictRedis()

__version__ = 1

DATA_ROOT_DIR = '../data/'

WITH_NAME_MATCH = re.compile(r'\((?!\.\.\.)[^+]+\)')
BRACKETS = re.compile(r'\([\w ]+?\)')
SPLITTER = re.compile(r'(\(.+?\))')


def read_dbtxt(input_data: str) -> Dict[str, Dict[str, Union[str, List[str]]]]:
    data: Dict[str, Dict[str, Union[str, List[str]]]] = {}

    for chunk in input_data.split('\n$'):
        parsed = parse_dbtxt(chunk)
        notation = parsed.get('n')

        if notation:
            data[notation] = parsed

    return data


def get_data_parser(filename: str) -> Tuple[Optional[Callable[[str, Optional[str]], None]], Optional[str]]:
    # Split out into a separate function so that we can call it from external packages
    # to determine what action to perform based on filename
    if filename == "notations.txt":
        return read_structure, None

    elif filename == "keys.txt":
        return read_keys, None

    elif filename.startswith('kw_'):
        language = filename[3:5]
        return read_keywords, language

    elif filename.startswith('txt_'):
        language = filename[4:6]
        return read_textual_correlates, language

    return None, None


def prime_redis() -> None:
    for dirpath, dirs, files in os.walk(DATA_ROOT_DIR):
        for filename in files:
            fn, language = get_data_parser(filename)

            if fn:
                file_data: str = open(os.path.join(dirpath, filename), mode='rt', encoding='utf-8').read()

                if file_data:
                    # check for Byte Order Mark (BOM), remove it
                    if file_data[0] and file_data[0].encode('utf-8') == b'\xef\xbb\xbf':
                        file_data = file_data[1:]

                    fn(file_data, language)


def read_keys(input_data: str, language: Optional[str]) -> None:
    buf: Dict[str, str] = {}
    keys: Dict[str, str] = {}

    for line in input_data.split('\n'):
        if line.startswith('#'):
            continue

        if line == '$':
            txt: Dict[str, str] = {}

            for k, v in buf.items():
                if k.startswith('txt_'):
                    tmp = k[4:].lower()
                    txt[tmp] = v

            suffix = buf.get('suffix')

            if txt and suffix:
                keys.setdefault(buf['code'], {})[suffix] = txt

            buf = {}

        else:
            tmp = line.split(' ')
            if len(tmp) < 2:
                continue

            field = tmp[0].lower()
            data = ' '.join(tmp[1:])
            buf[field] = data

    for k, v in keys.items():
        redis_c.set(k, json.dumps(v))


def read_structure(input_data, language: Optional[str]) -> None:
    data = read_dbtxt(input_data)
    idx = 0

    for notation, obj in data.items():
        for k, v in obj.items():
            if not v:
                continue

            if type(v) is list:
                redis_c.hset(notation, k, '\n'.join(v))
            else:
                redis_c.hset(notation, k, v)

        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write(f"{idx}           \r")


def read_keywords(input_data: str, language: str) -> None:
    data: Dict[str, List[str]] = {}
    idx = 0

    for line in input_data.split('\n'):
        if line.startswith('#'):
            continue

        stripped = line.strip()
        line_chunks = stripped.split('|')

        if len(line_chunks) != 2:
            continue

        notation, keyword = line_chunks
        data.setdefault(notation, []).append(keyword)

    for notation, v in data.items():
        redis_c.hset(notation, "kw_" + language, '\n'.join(v))

        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write(f"{idx}           \r")


def read_textual_correlates(input_data: str, language: str) -> None:
    idx = 0

    for line in input_data.split('\n'):
        if line.startswith('#'):
            continue

        stripped = line.strip()
        line_chunks = stripped.split('|')

        if len(line_chunks) != 2:
            continue

        notation, text = line_chunks
        redis_c.hset(notation, "txt_" + language, text)

        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write(f"{idx}           \r")


def parse_dbtxt(input_data: str) -> Dict[str, Union[str, Dict[str, Union[str, List[str]]]]]:
    parsed: Dict[str, Union[str, Dict[str, Union[str, List[str]]]]] = {}
    buf: Union[str, List[str]] = []
    last_field: Optional[str] = None

    for line in input_data.split('\n'):
        if line.startswith('#'):
            continue

        line_chunks = line.split(' ')

        if len(line_chunks) < 2:
            continue

        field = line_chunks[0].lower()
        line_data = ' '.join(line_chunks[1:])

        if field == ';':
            buf.append(line_data)

        elif field != last_field:
            if buf:
                parsed[last_field] = buf

            buf = [line_data]
            last_field = field

        if field in ('n', 'k'):
            buf = buf[0]

    if buf:
        parsed[last_field] = buf

    for k, v in parsed.items():
        if k.startswith('t_'):
            parsed.setdefault('txt', {})[k[2:]] = v[0]
            del parsed[k]

        if k.startswith('k_'):
            parsed.setdefault('kw', {})[k[2:]] = [x for x in v]
            del parsed[k]

    return parsed


def dump_dbtxt(obj) -> str:
    buf: List[str] = []
    ba_fn: Callable[[str], None] = buf.append

    ba_fn(f"N {obj['n']}")
    ba_fn("P {}".format("\n; ".join(obj['p'])))

    if 'k' in obj:
        ba_fn(f"K {obj['k']}")

    if 'c' in obj:
        ba_fn("C {}".format("\n; ".join(obj['c'])))

    if obj.get('r'):
        ba_fn("R {}".format("\n; ".join(obj['r'])))

    for lang, txt in obj.get('txt').items():
        ba_fn(f"T_{lang} {txt}")

    for lang, kws in obj.get('kw').items():
        ba_fn("K_{} {}".format(lang, "\n; ".join(kws)))

    result = "\n".join(buf)
    return result


def get_parts(notation: str) -> List[str]:
    """Split an ICONCLASS notation up into a list of its parts"""
    parts: List[str] = []
    last_part = ''

    for part in SPLITTER.split(notation):
        if part.startswith('(+'):
            tmp_last_part = last_part + '(+'

            for x in part[2:]:
                if x and x != ')':
                    parts.append(tmp_last_part + x + ')')
                    tmp_last_part += x

            last_part = parts[-1]

        elif part.startswith('(') and part.endswith(')'):
            if part != '(...)':
                parts.append(last_part + '(...)')

            parts.append(last_part + part)
            last_part = parts[-1]

        else:
            for x in range(len(part)):
                parts.append(last_part + part[x])

                if parts:
                    last_part = parts[-1]

    return parts


def fill_obj(notation_obj: Any) -> Optional[Dict[str, Union[str, List[str]]]]:
    """
    For the specified notation return an object with the children and path filled as objects
    >> Z = get_filled_obj

    >> o = Z('1')
    >> sorted([x['n'] for x in o['c']])
    [u'10', u'11', u'12', u'13', u'14']
    
    And it must also work for arb keys.
    >> t = Z('11(+1)')
    >> sorted([x['n'] for x in t['c']])
    [u'11(+11)', u'11(+12)', u'11(+13)']
    >> Z('XYZ')
    Traceback (most recent call last):
            ...
    NotationNotFoundException: 'XYZ'
    
    If there are no kids found, the returned obj must have an empty 'c' key    
    >> l = Z('0')
    >> l['c']
    []
    
    >> a = Z('96C')
    >> [x['n'] for x in a['p']]
    [u'9', u'96']
    
    """

    if not notation_obj:
        return

    kids = [v for v in [get(c) for c in notation_obj.get('c', [])] if v]
    path = [v for v in [get(p) for p in notation_obj.get('p', [])] if v]
    sysrefs = [v for v in [get(r) for r in notation_obj.get('r', [])] if v]

    notation_obj['c'] = kids
    notation_obj['p'] = path
    notation_obj['r'] = sysrefs

    return notation_obj


def get(notation) -> str:
    return get_list([notation])[0]


def get_list(notations) -> List[Union[List, Dict, str]]:
    if not notations:
        return []

    buf: Dict[str, Union[List, Dict, str]] = {}
    # We also retrieve the WITH_NAMES (...) for all entries
    # This is in case of user-supplied WITH-NAMES (eg. 11H(FOO)(+1) ) which also includes keys
    # We can't just do them if the notation returns a None, as keys need to be expanded too...    
    for notation in notations:
        obj = redis_get(notation)

        if not obj and WITH_NAME_MATCH.search(notation):
            notation_with_name = WITH_NAME_MATCH.sub('(...)', notation)
            obj = redis_get(notation_with_name)

            if obj:
                obj['n'] = notation
                bracketed_text: Optional[str] = WITH_NAME_MATCH.search(notation).group()
                # The bracketed_text will be used to substitute txt in the obj

                # Also replace any (...) in the txts with the part in the notation
                tmp1 = {}
                for lang, txt in obj.get('txt', {}).items():
                    tmp1[lang] = BRACKETS.sub(bracketed_text, txt)
                obj['txt'] = tmp1

                # Can we also remove the children that belong to the (...) parent?
                # And fix the children notations
                tmp2 = []
                for kind in obj.get('c', []):
                    if kind.find('+') > 0 or not kind.endswith(')'):
                        tmp2.append(kind.replace('(...)', bracketed_text))
                obj['c'] = tmp2

        if obj:
            buf[obj['n']] = obj

    return [buf.get(x) for x in notations]


def redis_get(notation: str) -> Optional[Dict[str, Union[Dict[str, Union[str, List[str]]], str, List[str]]]]:
    # Handle the Keys (+ etc. )
    tmp = notation.split('(+')

    if len(tmp) == 2:
        base, key = tmp
        if key.endswith(')'):
            key = key[:-1]
    else:
        base = tmp[0]
        key = ''  # It has to be '' and not None so that we can do a len('')
        # and get 0 for key-children selection later on

    obj = {}

    for k, v in [(k.decode('utf-8'), v.decode('utf-8')) for (k, v) in redis_c.hgetall(base).items()]:

        if k.startswith('txt_'):
            obj.setdefault('txt', {})[k[4:6]] = v

        elif k.startswith('kw_'):
            obj.setdefault('kw', {})[k[3:5]] = v.split('\n')

        elif k in ('n', 'k'):
            obj[k] = v

        else:
            values = v.split('\n')
            if values:
                obj[k] = values
    if not obj:
        return None

    keycode = obj.get('k')

    if keycode:
        r_key_obj = redis_c.get(keycode)

        if not r_key_obj:
            raise Exception(f"Key {keycode} not found")

        key_obj = json.loads(r_key_obj)  # Automatically converts to utf-8

    if key and keycode and key in key_obj:
        key_txt = key_obj.get(key)

        # Fix the text correlates
        for lang, k_txt in key_txt.items():
            obj_txt = obj.get('txt', {}).get(lang)
            new_txt = f"{obj_txt} (+ {k_txt})"
            obj.setdefault('txt', {})[lang] = new_txt

        # Fix the notation
        obj['n'] = f"{obj['n']}(+{key})"

    if keycode:
        # Fix the children
        new_kids = set()

        for kk in key_obj.keys():
            if type(kk) != str:
                kk = str(kk)  # Make sure kk is a string to prevent UnicodeDecodeErrors

            if kk.startswith(key) and len(kk) == (len(key) + 1):
                new_kids.add(f"{base}(+{kk})")

        if key:
            obj['c'] = sorted(new_kids)
        else:
            obj['c'] = obj.get('c', []) + sorted(new_kids)

    obj['p'] = get_parts(notation)

    if 'k' in obj:
        del obj['k']

    return obj


def add_space(value: str) -> str:
    """For a given unicode string @notation
    Add some spaces according to the ICONCLASS rules as commonly used in DE
    See tests for examples
    """
    if len(value) < 3:
        return value

    if value[1:3] == '(+':
        tip = value[0]
        start = 1

    elif (value[2:4] == '(+') \
            or (value[2] == '(' and value[3] != '+'):
        tip = value[:2]
        start = 2

    else:
        tip = f"{value[:2]} {value[2]}"

        if len(value) == 3:
            return tip.strip()

        if len(value) == 4 and value[2] == value[3]:
            return f"{value[:2]} {value[2:4]}"

        start = 3

        if value[2] == value[3]:
            start = 4
            tip = f"{value[:2]} {value[2:4]}"

    inbracket, inkey, parts, s = False, False, [tip], ''

    for idx, x in enumerate(value[start:]):
        if x == ' ' and not inbracket:
            continue

        if x == '(':
            inbracket = True
            parts.append(s)
            s = ''

        s += x

        if x == '+' and inbracket:
            inkey = True
            inbracket = False

        if x == ')':
            inbracket = False
            inkey = False
            parts.append(s)
            s = ''

        if len(s) >= 2 and not inbracket:
            parts.append(s)
            s = ''

    parts.append(s)

    tmp = []

    for idx, x in enumerate(parts):
        if not x or x == ' ':
            continue
        if idx < (len(parts) - 1) and parts[idx + 1] == ')':
            tmp.append(x)
        else:
            tmp.append(f"{x} " if x != '(+' else x)

    return ''.join(tmp).strip()


def filter_inputs(input_filename: str, output_filename: str) -> None:
    f = open(input_filename).readlines()
    ff = sorted([x.strip().strip('"') for x in f[1:]])[4:]
    fetched = [(x, get(x)) for x in ff]
    notfetched = [x for x in fetched if not x[1]]

    with open(output_filename, 'w') as F:
        for n in notfetched:
            F.write(f"{n}\n")

        for n, t in fetched:
            if not t:
                continue
            F.write(f"{n}\t{t['txt']['en'].encode('utf-8')}\n")


def children_iterator(notation) -> Iterator[Any]:
    obj = get(notation)
    if not obj:
        return

    yield obj

    for k in obj.get('c', []):
        for kk in children_iterator(k):
            yield kk
