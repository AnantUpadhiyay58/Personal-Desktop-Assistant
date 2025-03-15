import requests
import json

GROQ_API_KEY = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {GROQ_API_KEY}"
}

data = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {"role": "user", "content": "Explain the importance of fast language models"}
    ]
}

response = requests.post(url, headers=headers, data=json.dumps(data))

response_json = response.json()

content = response_json["choices"][0]["message"]["content"]
print(content)