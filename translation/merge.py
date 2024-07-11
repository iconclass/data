#!/usr/bin/env python3
from utils import read_lines, append


def read_file(file_name):
    translations = {}
    for line in read_lines(file_name):
        parts = line.strip().split('|', maxsplit=1)
        if len(parts) != 2:
            print('OOPS:', line)
            return {}
        translations[parts[0]] = parts[1]
    return translations


if __name__ == '__main__':
    translations1 = read_file(f'../txt/nl/txt_nl_0_1.txt')
    translations2 = read_file(f'../txt/nl/erwin_txt_nl_0_1.txt')
    merged = '../txt/nl/temp_txt_nl_0_1.txt'
    for key, value in translations2.items():
        if key[0] == '#':
            real_key = key[1:]
            append(f'{real_key}|{translations1[real_key]}    # {value}', merged)
        else:
            append(f'{key}|{value}', merged)
