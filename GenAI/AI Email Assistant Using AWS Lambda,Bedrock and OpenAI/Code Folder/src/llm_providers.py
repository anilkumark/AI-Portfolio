import json
import boto3
import logging
import requests
import openai
from typing import Dict

from .config import (
    LLM_PROVIDER, BEDROCK_REGION, MODEL_ID, 
    OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_MODEL
)


class LLMProvider:
    """Unified interface for different LLM providers."""
    
    def __init__(self):
        self.provider = LLM_PROVIDER.lower()
        self._setup_client()
    
    def _setup_client(self):
        """Initialize the appropriate client based on provider."""
        if self.provider == 'bedrock':
            self.client = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
        elif self.provider == 'openai':
            # OpenAI client will be initialized when needed
            pass
        elif self.provider == 'ollama':
            # Ollama uses direct HTTP requests
            pass
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
        """Call the configured LLM provider with given prompts."""
        
        if self.provider == 'bedrock':
            return self._call_bedrock(system_prompt, user_prompt, max_tokens, temperature)
        elif self.provider == 'ollama':
            return self._call_ollama(system_prompt, user_prompt, max_tokens, temperature)
        elif self.provider == 'openai':
            return self._call_openai(system_prompt, user_prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Provider {self.provider} not implemented")
    
    def _call_bedrock(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        """Call AWS Bedrock Llama 3.3 70B."""
        try:
            request_body = {
                "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": 0.9
            }
            
            response = self.client.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['generation'].strip()
            
        except Exception as e:
            logging.error(f"Bedrock error: {e}")
            raise
    
    def _call_ollama(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        """Call local Ollama instance."""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                },
                "stream": False
            }
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['message']['content'].strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            raise
    
    def _call_openai(self, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        """Call OpenAI API."""
        try:
            response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"OpenAI error: {e}")
            raise


# Global LLM instance
llm = LLMProvider()


def call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
    """Convenience function to call the configured LLM."""
    return llm.call_llm(system_prompt, user_prompt, max_tokens, temperature)