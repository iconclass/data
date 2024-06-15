import requests


class Deepl:

    def __init__(self, config):
        self.config = config

    def translate(self, text_to_translate, language='NL'):
        params = {
            'auth_key': self.config['DEEPL_API_KEY'],
            'text': text_to_translate,
            'source_lang': 'EN',
            'target_lang': language
        }

        result = requests.post(self.config['DEEPL_URL'], data=params)

        if result.status_code != 200:
            raise Exception(result.text)

        try:
            return result.json()['translations'][0]['text']
        except KeyError:
            raise Exception(f"Could not retrieve `['translations'][0]['text']` from response")
