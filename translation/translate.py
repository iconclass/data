#!/usr/bin/env python3
from dotenv import dotenv_values
from chat_gpt import ChatGPT
from utils import read_lines

config = dotenv_values(".env")
chat_gpt = ChatGPT(config)


def append(text, file_name):
    with open(file_name, 'a') as f:
        f.write(f'{text}\n')


def translate(file_name_to_translate, target_file_name):
    processed = 0
    existing_translations = len(read_lines(target_file_name))

    for line in read_lines(file_name_to_translate):
        if processed >= existing_translations:
            parts = line.split('|', maxsplit=2)
            translation = chat_gpt.translate(parts[1])
            append(f'{parts[0]}|{translation}', target_file_name)
            print(parts[1], ' --> ', translation)
        processed += 1


if __name__ == '__main__':
    # text = "water (one of the four elements)"
    # print(chat_gpt.translate(text))
    file = 'txt_en_2_3.txt'
    translate(f'../txt/en/{file}', f'../txt/nl/BK_{file}')

