# Request from Hans on 7 June 2016: How many words are there on average per notation?
import os
import sys

words = {}
txts = {}
for f in os.listdir(sys.argv[1]):
    if f.endswith('.txt'):
        for line in open(sys.argv[1] + f).read().split('\n'):
            tmp = line.split('|')
            if len(tmp) != 2: continue
            notation, txt = tmp
            count = len(txt.split(' '))
            words[notation] = count
            txts[notation] = txt.split(' ')
