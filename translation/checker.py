from utils import read_lines
import re


def check_lines_and_keys(lines1, lines2):
    if len(lines1) != len(lines2):
        raise Exception(F'unequal number of lines')

    keys1 = set([line.split('|')[0] for line in lines1])
    keys2 = set([line.split('|')[0] for line in lines2])

    if keys1 != keys2:
        raise Exception(F'unequal keys')


def check_cases(lines1, lines2):
    for i, line in enumerate(lines1):
        parts1 = line.split('|')
        parts2 = lines2[i].split('|')
        if str(parts1[1][0]).isupper() != str(parts2[1][0]).isupper():
            if parts2[1].split(' ')[0] in ['januari;', 'februari;', 'maart;', 'april;', 'mei;', 'juni;', 'juli;',
                                           'augustus;', 'september;', 'oktober;', 'november;', 'december;',
                                           'januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
                                           'augustus', 'september', 'oktober', 'november', 'december']:
                continue
            print(i)
            print(line)
            print(lines2[i])
            print()


def check_quotes_count(lines1, lines2):
    for i, line in enumerate(lines1):
        quotes1 = line.count("'")
        quotes2 = lines2[i].count("'")
        if quotes1 != quotes2:
            print(i)
            print(line)
            print(lines2[i])
            print()


def check_quotes(lines1, lines2):
    for i, line in enumerate(lines1):
        quoted1 = set(re.findall(r"'[^']+'", line))
        quoted2 = set(re.findall(r"'[^']+'", lines2[i]))
        if quoted1 != quoted2:
            print(i)
            print(line)
            print(lines2[i])
            print()


if __name__ == '__main__':
    lines_1 = read_lines('../txt/en/txt_en_2_3.txt')
    lines_2 = read_lines('../txt/nl/txt_nl_2_3.txt')

    check_lines_and_keys(lines_1, lines_2)
    # check_cases(lines_1, lines_2)
    # check_quotes_count('../txt/en/txt_en_2_3.txt', '../txt/nl/txt_nl_2_3.txt')
    check_quotes(lines_1, lines_2)
