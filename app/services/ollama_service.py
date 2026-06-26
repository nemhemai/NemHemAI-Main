import ollama
import os

class OllamaLLM:
    def __init__(self, model=None):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    def create_chat_completion(self, messages, temperature=0.0, max_tokens=256, format=None, **kwargs):
        try:
            stream = kwargs.get("stream", False)
            response = ollama.chat(
                model=self.model,
                messages=messages,
                format=format,
                stream=stream,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": kwargs.get("top_p", 1.0),
                    "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
                }
            )

            if stream:
                def generator():
                    for chunk in response:
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                return generator()

            return {
                "choices": [
                    {
                        "message": {
                            "content": response["message"]["content"]
                        }
                    }
                ]
            }

        except Exception as e:
            return {
                "choices": [
                    {
                        "message": {
                            "content": f"Error: {str(e)}"
                        }
                    }
                ]
            }


# singleton (same pattern as get_llm)
_ollama_instance = None

def get_ollama_llm():
    global _ollama_instance
    if _ollama_instance is None:
        print("Initializing Ollama Qwen...")
        _ollama_instance = OllamaLLM()
    return _ollama_instance