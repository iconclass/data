import requests
import json


class ChatGPT:

    def __init__(self, config):
        self.config = config

    def translate(self, text_to_translate):
        headers = {'Content-Type': 'application/json', 'Authorization': f"Bearer {self.config['OPEN_AI_API_KEY']}"}

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": self.config['OPEN_AI_PROMPT']
                },
                {
                    "role": "user",
                    "content": text_to_translate
                }
            ],
            "max_tokens": int(self.config['OPEN_AI_MAX_TOKENS']),
            "temperature": float(self.config['OPEN_AI_TEMPERATURE'])
        }

        result = requests.post(self.config['OPEN_AI_URL'], headers=headers, data=json.dumps(payload))

        if result.status_code != 200:
            raise Exception(result.text)

        try:
            return result.json()['choices'][0]['message']['content']
        except KeyError:
            raise Exception(f"Could not retrieve '['choices'][0]['message']['content']' from response")
