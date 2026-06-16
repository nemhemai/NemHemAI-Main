import ollama

class OllamaLLM:
    def __init__(self, model="llama3:8b"):
        self.model = model

    def create_chat_completion(self, messages, temperature=0.0, max_tokens=256, **kwargs):
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
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
        print("Initializing Ollama Llama3...")
        _ollama_instance = OllamaLLM()
    return _ollama_instance