import ollama

class OllamaLLM:
    def __init__(self, model="llama3.2:3b"):
        self.model = model

    def create_chat_completion(self, messages, temperature=0.0, max_tokens=256, format=None, **kwargs):
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                format=format,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": kwargs.get("top_p", 1.0),
                    "repeat_penalty": kwargs.get("repeat_penalty", 1.1),
                }
            )

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