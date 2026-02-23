import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1"


def call_llm(prompt: str) -> str:

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        },
    )

    '''print("STATUS CODE:", response.status_code)
    print("RAW TEXT:", response.text)'''

    result = response.json()
    '''print("PARSED JSON:", result)'''

    return result.get("response", "")