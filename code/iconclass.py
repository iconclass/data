import os, re, sys, json
import redis
redis_c = redis.StrictRedis()

__version__ = 1

DATA_ROOT_DIR = '../data/'

WITH_NAME_MATCH = re.compile(r'\((?!\.\.\.)[^+]+\)')
BRACKETS = re.compile(r'\([\w ]+?\)') 
SPLITTER = re.compile(r'(\(.+?\))')

def read_dbtxt(input_data):
    data = {}
    for chunk in input_data.split('\n$'):
        obj = parse_dbtxt(chunk)
        notation = obj.get('n')
        if notation:
            data[notation] = obj
    return data


def action(filename):
    # Split out into a seprate function so that we can call it from external packages
    # to determine what action to perform based on filename
    if filename == 'notations.txt':
        return read_structure, None
    elif filename == 'keys.txt':
        return read_keys, None
    elif filename.startswith('kw_'):
        language = filename[3:5]
        return read_keywords, language
    elif filename.startswith('txt_'):
        language = filename[4:6]
        return read_textual_correlates, language
    return None, None

def prime_redis():
    for dirpath, dirs, files in os.walk(DATA_ROOT_DIR):
        for filename in files:
            fn, language = action(filename)
            if fn:
                fn(open(os.path.join(dirpath, filename)).read(), language)

def read_keys(input_data, language):
    buf = {}
    keys = {}
    for line in input_data.split('\n'):
        if line.startswith('#'): continue
        if line == '$':
            txt = {}
            for k, v in buf.items():
                if k.startswith('txt_'):
                    tmp = k[4:].lower()
                    txt[tmp] = v.decode('utf8')
            suffix = buf.get('suffix')
            if txt and suffix:
                keys.setdefault(buf['code'], {})[suffix] = txt
            buf = {}
        else:
            tmp = line.split(' ')
            if len(tmp) < 2: continue
            field = tmp[0].lower()
            data = ' '.join(tmp[1:])
            buf[field] = data
    for k,v in keys.items():
        redis_c.set(k, json.dumps(v))

def read_structure(input_data, language):
    data = read_dbtxt(input_data)
    idx = 0
    for notation, obj in data.items():
        for k, v in obj.items():
            if not v: continue
            if type(v) is list:
                redis_c.hset(notation, k, '\n'.join(v))
            else:
                redis_c.hset(notation, k, v)
        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write('%s           \r' % idx)
            
def read_keywords(input_data, language):
    idx = 0
    data = {}

    for line in input_data.split('\n'):
        if line.startswith('#'): continue
        line = line.strip()
        tmp = line.split('|')
        if len(tmp) != 2:
            continue
        notation, keyword = tmp
        data.setdefault(notation, []).append(keyword)

    for notation, v in data.items():
        redis_c.hset(notation, "kw_" + language, '\n'.join(v))
        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write('%s           \r' % idx)


def read_textual_correlates(input_data, language):
    idx = 0
    for line in input_data.split('\n'):
        if line.startswith('#'): continue
        line = line.strip()
        tmp = line.split('|')
        if len(tmp) != 2:
            continue
        notation, text = tmp
        redis_c.hset(notation, "txt_"+language, text)
        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write('%s           \r' % idx)


def parse_dbtxt(data):
    obj = {}
    buf = []
    last_field = None
    for line in data.split('\n'):
        if line.startswith('#'): continue
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
        if field in ('n', 'k'):
            buf = buf[0]
    if buf:
        obj[last_field] = buf

    for k,v in obj.items():
        if k.startswith('t_'):
            obj.setdefault('txt', {})[k[2:]] = v[0].decode('utf8')
            del obj[k]
        if k.startswith('k_'):
            obj.setdefault('kw', {})[k[2:]] = [x.decode('utf8') for x in v]
            del obj[k]
    return obj

def dump_dbtxt(obj):
    buf = []
    ba = buf.append
    ba(u'N %s' % obj['n'])
    ba(u'P %s' % '\n; '.join(obj['p']))
    if 'k' in obj:
        ba(u'K %s' % obj['k'])
    if 'c' in obj:
        ba(u'C %s' % '\n; '.join(obj['c']))
    if obj.get('r'):
        ba(u'R %s' % '\n; '.join(obj['r']))
    for lang, txt in obj.get('txt').items():
        ba('T_%s %s' % (lang, txt))
    for lang, kws in obj.get('kw').items():
        ba('K_%s %s' % (lang, '\n; '.join(kws)))
    tmp = u'\n'.join(buf)
    return tmp.encode('utf8')

def get_parts(a):
    'Split an ICONCLASS notation up into a list of its parts'
    SPLITTER = re.compile(r'(\(.+?\))')
    p = []
    lastp = ''
    for p1 in SPLITTER.split(a):
        if p1.startswith('(+'):
            tmplastp = lastp + '(+'
            for x in p1[2:]:
                if x and x != ')':
                    p.append(tmplastp + x + ')')
                    tmplastp += x
            lastp = p[-1]
        elif p1.startswith('(') and p1.endswith(')'):
            if p1 != '(...)': p.append(lastp + '(...)')
            p.append(lastp + p1)
            lastp = p[-1]
        else:
            for x in range(len(p1)):
                p.append(lastp + p1[x])
                if p: lastp = p[-1]
    return p

def fill_obj(obj):
    '''For the specified notation return an object with the children and path filled as objects
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
    
    '''
    if not obj: return
    kids = filter(None, [get(c) for c in obj.get('c', [])])
    path = filter(None, [get(p) for p in obj.get('p', [])])
    sysrefs = filter(None, [get(r) for r in obj.get('r', [])])
    obj['c'] = kids
    obj['p'] = path
    obj['r'] = sysrefs

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
        obj = redis_get(notation)
        if not obj and WITH_NAME_MATCH.search(notation):
            notation_with_name = WITH_NAME_MATCH.sub('(...)', notation)
            obj = redis_get(notation_with_name)
            if obj:
                obj['n'] = notation
                bracketed_text = WITH_NAME_MATCH.search(notation).group()
                # The bracketed_text will be used to substitute txt in the obj
                # which already are uniciode as it comes back from the redis_get
                # so also convert this to unicode to prevent autoconversion barfs
                if type(bracketed_text) != unicode:
                    bracketed_text = bracketed_text.decode('utf8')
                # Also replace any (...) in the txts with the part in the notation
                tmp = {}
                for lang, txt in obj.get('txt', {}).items():
                    tmp[lang] = BRACKETS.sub(bracketed_text, txt)
                obj['txt'] = tmp
                tmp = []
                # Can we also remove the children that belong to the (...) parent?
                # And fix the children notations
                for kind in obj.get('c', []):
                    if kind.find('+') > 0 or not kind.endswith(')'):
                        # what form are the kids stored in, UTF8 ?
                        tmp.append(kind.replace('(...)', bracketed_text))
                obj['c'] = tmp
        if obj:
            buf[obj['n']] = obj            

    return [buf.get(x) for x in notations]

def redis_get(notation):
    # Handle the Keys (+ etc. )
    if type(notation) == unicode:
        notation = notation.encode('utf8')
    tmp = notation.split('(+')
    if len(tmp) == 2:
        base, key = tmp
        if key.endswith(')'):
            key = key[:-1]
    else:
        base = tmp[0]
        key = '' # It has to be '' and not None so that we can do a len('') 
                 # and get 0 for key-children selection later on

    obj = {}
    for k,v in redis_c.hgetall(base).items():
        if k.startswith('txt_'):
            obj.setdefault('txt', {})[k[4:6]] = v.decode('utf8')
        elif k.startswith('kw_'):
            obj.setdefault('kw', {})[k[3:5]] = v.decode('utf8').split('\n')
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
            raise Exception('Key %s not found' % keycode)
        key_obj = json.loads(r_key_obj)

    if key and keycode and key in key_obj:
        key_txt = key_obj.get(key)
        # Fix the text correlates
        for lang, k_txt in key_txt.items():
            obj_txt = obj.get('txt', {}).get(lang)
            new_txt = u'%s (+ %s)' % (obj_txt, k_txt)
            obj.setdefault('txt', {})[lang] = new_txt
        # Fix the notation
        obj['n'] = '%s(+%s)' % (obj['n'], key)

    if keycode:
        # # Fix the children
        new_kids = set()
        for kk in key_obj.keys():
            kk = kk.encode('utf8') # Make sure kk is a string to prevent unicodedecodeerrors
            if kk.startswith(key) and len(kk) == (len(key)+1):
                new_kids.add('%s(+%s)' % (base, kk))
        if key:
            obj['c'] = sorted(new_kids)
        else:
            obj['c'] = obj.get('c', []) + sorted(new_kids)
    
    obj['p'] = get_parts(notation)
    if 'k' in obj:
        del obj['k']
    return obj

def add_space(a):
    '''For a given unicode string @notation
    Add some spaces according to the ICONCLASS rules as commonly used in DE
    See tests for examples
    '''
    if len(a) < 3: return a
    if a[1:3] == '(+':
        tip = a[0]
        start = 1
    elif (a[2:4] == '(+') \
         or (a[2] == '(' and a[3] != '+'):
        tip = a[:2]
        start = 2
    else:
        tip = '%s %s' % (a[:2], a[2])
        if len(a) == 3: return tip.strip()
        if len(a) == 4 and a[2]==a[3]: return '%s %s' % (a[:2], a[2:4])
        start = 3
        if a[2]==a[3]:
            start = 4
            tip = '%s %s' % (a[:2], a[2:4])
    inbracket, inkey, parts, s = False, False, [tip], ''
    for idx, x in enumerate(a[start:]):
        if x == ' ' and not inbracket: continue
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
        if not x or x == ' ': continue
        if idx < (len(parts)-1) and parts[idx+1] == ')':
            tmp.append(x)
        else:
            tmp.append('%s ' % x if x != '(+' else x)
    return ''.join(tmp).strip()

def filter_inputs(input_filename, output_filename):
    f = open(input_filename).readlines()
    ff = sorted([x.strip().strip('"') for x in f[1:]])[4:]
    fetched = [(x, get(x)) for x in ff ]
    notfetched = [x for x in fetched if not x[1]]
    with open(output_filename, 'w') as F:
        for n in notfetched:
            F.write('%s\n' % n)
        for n,t in fetched:
            if not t: continue
            F.write('%s\t%s\n' % (n, t['txt']['en'].encode('utf8')))

def hier(notation):
    try:
        obj = get(notation)
    except:        
        return
    if not obj:
        raise Exception('Object %s does not exist' % notation)
    sys.stderr.write(' ' * 110 + '\r')
    sys.stderr.write( '%20s\t%s\r' % (notation.encode('utf8'), obj.get('txt', {}).get('en').encode('utf8')[:90]) )
    for c in obj.get('c', []):
        hier(c)

def children_iterator(notation):
    obj = get(notation)
    if not obj: return
    yield obj
    for k in obj.get('c', []):
        for kk in children_iterator(k):
            yield kk

if __name__ == '__main__':
    if len(sys.argv) > 1:
        start = sys.argv[1]
        hier(start)
