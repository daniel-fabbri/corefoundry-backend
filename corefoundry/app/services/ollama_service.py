"""Ollama service for interacting with Ollama API."""

import requests
from typing import Dict, List, Any, Optional
from corefoundry.configs.settings import settings


class OllamaService:
    """Service for interacting with Ollama API."""
    
    def __init__(self, host: Optional[str] = None):
        """
        Initialize Ollama service.
        
        Args:
            host: Ollama host URL (defaults to settings.OLLAMA_HOST)
        """
        self.host = host or settings.OLLAMA_HOST
        self.base_url = f"{self.host}/api"
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in Ollama.
        
        Returns:
            List of model dictionaries
            
        Raises:
            requests.RequestException: If request fails
        """
        try:
            response = requests.get(f"{self.base_url}/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except requests.RequestException as e:
            print(f"Error listing models: {e}")
            return []
    
    def run_prompt(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Run a prompt through Ollama.
        
        Args:
            prompt: The prompt to run
            model: Model name (defaults to settings.OLLAMA_MODEL)
            system: System prompt
            temperature: Temperature for generation
            stream: Whether to stream the response
            
        Returns:
            Response dictionary with 'response' key containing the generated text
            
        Raises:
            requests.RequestException: If request fails
        """
        model = model or settings.OLLAMA_MODEL
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=300  # 5 minute timeout for generation
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error running prompt: {e}")
            raise
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Run a chat conversation through Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (defaults to settings.OLLAMA_MODEL)
            temperature: Temperature for generation
            stream: Whether to stream the response
            
        Returns:
            Response dictionary
            
        Raises:
            requests.RequestException: If request fails
        """
        model = model or settings.OLLAMA_MODEL
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error in chat: {e}")
            raise
    
    def check_health(self) -> bool:
        """
        Check if Ollama is healthy and responding.
        
        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False


# Create singleton instance
ollama_service = OllamaService()
