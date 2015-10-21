import os, re, sys, json
import redis
redis_c = redis.StrictRedis()

__version__ = 1

DATA_ROOT_DIR = './data'

WITH_NAME_MATCH = re.compile(r'\((?!\.\.\.)[^+]+\)')
BRACKETS = re.compile(r'\([\w ]+?\)') 
SPLITTER = re.compile(r'(\(.+?\))')

def read_dbtxt(filename):    
    if not os.path.exists(filename): return {}    
    data = {}
    for chunk in open(filename).read().split('\n$'):
        obj = parse_dbtxt(chunk)
        notation = obj.get('n')
        if notation:
            data[notation] = obj
    return data

def prime_redis():
    sys.stderr.write('Reading structure\n')
    read_structure()
    sys.stderr.write('Reading textual correlates\n')
    read_textual_correlates()
    sys.stderr.write('Reading keywords\n')
    read_keywords()
    sys.stderr.write('Reading keys\n')
    read_keys()

def read_keys():
    if not os.path.exists(DATA_ROOT_DIR +'/keys.txt'): return
    buf = {}
    keys = {}
    filedata = open(DATA_ROOT_DIR +'/keys.txt').read()    
    for line in filedata.split('\n'):
        if line == '$':
            txt = {}
            for k,v in buf.items():
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

def read_structure():    
    data = read_dbtxt(DATA_ROOT_DIR + '/notations.txt')
    idx = 0
    for notation, obj in data.items():
        for k,v in obj.items():
            if not v: continue
            if type(v) is list:
                redis_c.hset(notation, k, '\n'.join(v))
            else:
                redis_c.hset(notation, k, v)
        idx += 1
        if idx % 1000 == 0:
            sys.stderr.write('%s           \r' % idx)
            
def read_keywords(language=None):
    languagefiles = []
    for dirpath, dirs, files in os.walk(DATA_ROOT_DIR + '/kw/'):
        for filename in files:
            if not filename.startswith('kw_'): continue
            if not language: languagefiles.append(os.path.join(dirpath, filename))
            if language and language == filename[3:5]:
                languagefiles.append(os.path.join(dirpath, filename))
    idx = 0
    data = {}
    sys.stderr.write('Reading keywords into memory\n')
    for filename in languagefiles:
        tmp = filename.split('kw_')
        if len(tmp) != 2:
            raise Exception('Language detection from filename failed, split on kw_ is not two chunks: ' +filename)
        language = tmp[1][:2]
        for line in open(filename).read().split('\n'):
            line = line.strip()
            tmp = line.split('|')
            if len(tmp) != 2:
                continue
            notation, keyword = tmp
            data.setdefault(notation, {}).setdefault(language, []).append(keyword)
    sys.stderr.write('Putting keywords into redis\n')
    for notation, languages in data.items():
        for language, v in languages.items():
            redis_c.hset(notation, "kw_" + language, '\n'.join(v))
            idx += 1
            if idx % 1000 == 0:
                sys.stderr.write('%s           \r' % idx)


def read_textual_correlates(language=None):
    languagefiles = []
    for dirpath, dirs, files in os.walk(DATA_ROOT_DIR + '/txt/'):
        for filename in files:
            if not filename.startswith('txt_'): continue
            if not language: languagefiles.append(os.path.join(dirpath, filename))
            if language and language == filename[4:6]:
                languagefiles.append(os.path.join(dirpath, filename))
    idx = 0
    for filename in languagefiles:
        tmp = filename.split('txt_')
        if len(tmp) != 2:
            raise Exception('Language detection from filename failed, split on txt_ is not two chunks: ' +filename)
        language = tmp[1][:2]
        for line in open(filename).read().split('\n'):
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
    sys.stderr.write( '%s\t%s\r' % (notation.encode('utf8'), obj.get('txt', {}).get('en').encode('utf8')[:70]) )
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