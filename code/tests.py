# -*- coding: utf-8 -*-
from iconclass import *
# https://nose.readthedocs.org/en/latest/usage.html

test_notations = [
    '0', '1', '25FF'   
]

def test_keywords():
    x = get('0')
    assert x['kw']['en'] == [u'abstract art', u'art', u'non-representational art']
    x = get('31AA25')
    assert x['kw']['de'] == [u'Arm', u'Geste', u'Haltung', u'Hand']

def test_keys():
    x = get('11(+1)')    
    assert x['txt']['en'] == u'Christian religion (+ Holy Trinity)'
    assert x['c'] == ['11(+11)', '11(+12)', '11(+13)']
    # handle a bogus key gracefully...
    x = get('25FF1(+8)')
    assert x is None

def test_withnames():
    o = get('11H(FOO)')
    assert o['txt']['en'] == 'male saints (FOO)'
    assert get('11H(FOO)0')['txt']['en'] == u'male saints (FOO) - male saint represented in a group'

def test_basic():
    results = get_list(test_notations)
    assert len(filter(None, results)) == len(test_notations)

    assert results[1]['n'] == '1'
    assert results[1]['p'] == ['1']
    assert results[2]['p'] == ['2', '25', '25F', '25FF']
    assert results[0]['txt']['de'] == u'abstrakte, ungegenständliche Kunst'
    c = ['25FF1', '25FF2', '25FF3', '25FF4', '25FF5', '25FF6', '25FF7', '25FF8', '25FF9', 
         '25FF(+0)', '25FF(+1)', '25FF(+2)', '25FF(+3)', '25FF(+4)', '25FF(+5)', '25FF(+6)', '25FF(+7)']   
    assert results[2]['c'] == c

def test_spaces():
    assert add_space(u'11H1') == u'11 H 1'
    assert add_space(u'25F(+0)') == u'25 F (+0)'
    assert add_space(u'25F1(+123)') == u'25 F 1 (+12 3)'
    assert add_space(u'1') == u'1'
    assert add_space(u'11') == u'11'
    assert add_space(u'11H') == u'11 H'
    assert add_space(u'11H(...)') == u'11 H (...)'
    assert add_space(u'11H(JOHN)') == u'11 H (JOHN)'
    assert add_space(u'25FF') == u'25 FF'
    assert add_space(u'25F(+123)') == u'25 F (+12 3)'
    assert add_space(u'11H(JOHN)(+12345)') == u'11 H (JOHN) (+12 34 5)'
    assert add_space(u'7(+5)') == u'7 (+5)'
    assert add_space(u'31AA') == u'31 AA'
    assert add_space(u'31AA2(+0)') == u'31 AA 2 (+0)'
    assert add_space(u'31AA25(+0)') == u'31 AA 25 (+0)'
    assert add_space(u'11HH') == u'11 HH'
    assert add_space(u'11HH(AGNES)') == u'11 HH (AGNES)'
    assert add_space(u'11HH(AGNES)(+1)') == u'11 HH (AGNES) (+1)'
    assert add_space(u'11HH(AGNES)3(+1)') == u'11 HH (AGNES) 3 (+1)'
    assert add_space(u'11HH(AGNES)31(+31)') == u'11 HH (AGNES) 31 (+31)'
    assert add_space(u'43C1(+411)') == u'43 C 1 (+41 1)'
    assert add_space(u'43C78611(+3111)') == u'43 C 78 61 1 (+31 11)'
    assert add_space(u'61B2(...)2(+5)') == u'61 B 2 (...) 2 (+5)'
    assert add_space(u'34(+91)') == u'34 (+91)'
    assert add_space(u'83(BOCCACCIO, Decamerone)') == u'83 (BOCCACCIO, Decamerone)'
    assert add_space(u'11H(ALOYSIUS GONZAGA)') == u'11 H (ALOYSIUS GONZAGA)'
