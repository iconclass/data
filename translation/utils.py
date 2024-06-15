import os


def read_lines(file_name):
    if not os.path.isfile(file_name):
        return []
    with open(file_name, 'r') as f:
        return [line.rstrip() for line in f]
