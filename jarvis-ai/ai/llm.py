"""
JARVIS LLM Client - Interface to Ollama for local LLM inference.

Supports multiple models and provides both sync and streaming responses.
"""

import json
from typing import Optional, Generator, Dict, Any, List
from dataclasses import dataclass

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama not installed. Run: pip install ollama")


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = "stop"


class LLMClient:
    """
    Client for local LLM inference via Ollama.
    
    Supports:
    - Multiple models (Phi-3, Mistral, LLaMA, etc.)
    - System prompts
    - JSON output mode
    - Streaming responses
    """
    
    DEFAULT_MODEL = "phi3:mini"
    
    def __init__(self, model: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize LLM client.
        
        Args:
            model: Ollama model name (default: phi3:mini)
            timeout: Request timeout in seconds
        """
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout
        self._check_ollama()
    
    def _check_ollama(self):
        """Verify Ollama is available and model exists."""
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama is not installed. Run: pip install ollama")
        
        try:
            # Check if Ollama is running
            models = ollama.list()
            available = [m['name'] for m in models.get('models', [])]
            
            if self.model not in available and not any(self.model in m for m in available):
                print(f"Model {self.model} not found. Available: {available}")
                print(f"Pull with: ollama pull {self.model}")
        except Exception as e:
            print(f"Warning: Could not connect to Ollama: {e}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            json_mode: If True, request JSON output
            
        Returns:
            LLMResponse with generated content
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        options = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": options,
        }
        
        if json_mode:
            kwargs["format"] = "json"
        
        try:
            response = ollama.chat(**kwargs)
            
            return LLMResponse(
                content=response["message"]["content"],
                model=self.model,
                tokens_used=response.get("eval_count", 0),
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                finish_reason="error",
            )
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON dictionary
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True,
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            content = response.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass
            return {"error": "Invalid JSON", "raw": response.content}
    
    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """
        Stream response from LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Yields:
            Tokens as they are generated
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={"temperature": temperature},
            )
            
            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Multi-turn chat with message history.
        
        Args:
            messages: List of {"role": "user"|"assistant"|"system", "content": str}
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            
            return LLMResponse(
                content=response["message"]["content"],
                model=self.model,
                tokens_used=response.get("eval_count", 0),
            )
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=self.model,
                finish_reason="error",
            )


# Convenience function
def ask(prompt: str, model: str = "phi3:mini") -> str:
    """Quick one-shot question to LLM."""
    client = LLMClient(model=model)
    response = client.generate(prompt)
    return response.content


if __name__ == "__main__":
    # Test the LLM client
    client = LLMClient()
    
    print("Testing LLM client...")
    response = client.generate("Say 'Hello, I am JARVIS' in exactly those words.")
    print(f"Response: {response.content}")
    
    print("\nTesting JSON mode...")
    json_response = client.generate_json(
        "Return a JSON object with keys 'status' set to 'ok' and 'message' set to 'JARVIS online'"
    )
    print(f"JSON: {json_response}")
