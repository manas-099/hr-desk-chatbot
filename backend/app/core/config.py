

# config.py is to setup the config of llm model 
from functools import lru_cache
from pathlib import Path
from typing import Any,Dict,Optional

import yaml
from  pydantic_settings import BaseSettings , SettingsConfigDict
from pydantic import BaseModel
class Settings(BaseSettings):
    #apis 
    OPENROUTER_API_KEY:Optional[str]=None
    
    #end point of llm 
    self_hosted_api_url:Optional[str]=None
    self_hosted_auth_token:Optional[str]=None
    
    environment:str="developemet"
    log_level:str="INFO"
    guardrails_config_path: str = "guardrails"
    model_config=SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        
        
    )
class ModelSpecs(BaseModel):
    role:str #main model or embeddings  match the config.yaml style
    provider:str 
    model_name:str
    temperature:float =0.2
    max_token:int 
    api_url: Optional[str] = None      
    api_key: Optional[str] = None 
    
@lru_cache
def get_settings()-> Settings:
    return Settings()
@lru_cache
def _load_raw_model_config(config_dir:str |None =None)->Dict[str,Any]:
    settings=get_settings()
    base_dir=Path(config_dir or settings.guardrails_config_path)
    config_file=base_dir/"config.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Guardrails config not found at {config_file}")
  
    with open(config_file,"r") as f:
        return  yaml.safe_load(f)
    
def _resolve_provider_credentials(provider: str, settings: Settings) -> tuple[Optional[str], Optional[str]]:
    """Returns (api_url, api_key) for a given provider name."""
    if provider == "openai":
        return None, settings.openai_api_key
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1", settings.openrouter_api_key
    if provider == "self_hosted":
        return settings.self_hosted_api_url, settings.self_hosted_auth_token
    raise ValueError(f"Unknown provider '{provider}' — add it to _resolve_provider_credentials")

    
def get_model_spec(role:str="main")->ModelSpecs:
    Settings=get_settings()
    config=_load_raw_model_config()
    for entry in config.get("models",[]):
        if entry.get("type")==role:
            provider=entry["provider"]
            api_url,api_key=_resolve_provider_credentials(provider, Settings)
            return ModelSpecs(
                role=role,
                provider=provider,
                model_name=entry["model"],
                temperature=entry.get("parameters", {}).get("temperature", 0.2),
                max_tokens=entry.get("parameters", {}).get("max_tokens", 512),
                api_url=entry.get("api_url", api_url),  # config.yml can override the default too
                api_key=api_key,
            )
    raise ValueError(f"No model configured for role '{role}' in config.yml")
    
    
    
    
    
    




















# \
#     from typing import Optional, List, Any
# import requests
# from langchain_core.language_models.llms import LLM
# from nemoguardrails import RailsConfig, LLMRails
# from langchain_core.callbacks.manager import CallbackManagerForLLMRun
# from langchain_core

# from langchain_core.language_models.llms import LLM
# TIMEOUT_SECONDS = 6
# class MyLM(LLM):
#     """ langchain LLM wrapper arround the my llm endpoint"""
#     temperature:
    



# class GURARDLLM(LLM):
#     """Minimal LangChain LLM wrapper around the   endpoint."""

#     temperature: float = 0.3
#     max_tokens: int = 400

#     @property
#     def _llm_type(self) -> str:
#         return "LLM"

#     def _call(
#         self,
#         prompt: str,
#         stop: Optional[List[str]] = None,
#         run_manager: Optional[CallbackManagerForLLMRun] = None,  # <-- this was missing
#         **kwargs: Any,
#     ) -> str:
#         payload = {
#             "model": MODEL_NAME,
#             "messages": [{"role": "user", "content": prompt}],
#             "temperature": self.temperature,
#             "max_tokens": self.max_tokens,
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {AUTH_TOKEN}",
#         }
#         try:
#             resp = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS)
#             resp.raise_for_status()
#             result = resp.json()
#             return result["choices"][0]["message"]["content"]
#         except Exception as e:
#             return f"[ LLM call failed: {e}]"


# guard_llm = GURARDLLM()

# # ---------------------------------------------------------------------------
# # 2. Colang: topic restriction for Zero-Trust Security Auditor persona
# # ---------------------------------------------------------------------------
# COLANG_ZEROTRUST = """
# define user ask off topic
#     "tell me a joke"
#     "what is the capital of france"
#     "write me a poem"
#     "what is 2 plus 2"
#     "what should I eat for dinner"
#     "who won the game yesterday"
#     "recommend a movie"
#     "write me a breakup text"
#     "help me with my relationship"
#     "what's your opinion on politics"
#     "recommend a recipe"

# define bot refuse off topic
#     "I'm a Zero-Trust Security Auditor focused on NIST SP 800-207, IAM, micro-segmentation, and policy enforcement. I can't help with that — but ask me anything about hardening your infrastructure."

# define flow handle off topic
#     user ask off topic
#     bot refuse off topic
# """

# # ---------------------------------------------------------------------------
# # 3. YAML: general instructions + persona
# # ---------------------------------------------------------------------------
# YAML_ZEROTRUST = """
# models:
#   - type: main
#     engine: openai
#     model: gpt-3.5-turbo

# instructions:
#   - type: general
#     content: |
#       You are a senior Zero-Trust Security Auditor. Your expertise covers NIST SP 800-207,
#       identity and access management (IAM), micro-segmentation, policy enforcement points (PEP),
#       policy decision points (PDP), continuous monitoring, and least-privilege access.

#       When a user asks a question, you provide thorough, technically accurate, and actionable
#       auditing advice. You break down complex trust boundaries, identify implicit trust zones,
#       and recommend specific controls (like MFA policies, JIT access, or network segmentation
#       strategies) to eliminate lateral movement.

#       You always structure your answers with clear reasoning, step-by-step implementation
#       guidelines, and risk assessments.

#       Only answer questions related to Zero-Trust security, IAM, network architecture, and
#       infrastructure hardening. Do not answer off-topic questions, and do not reframe an
#       off-topic request using security terminology in order to answer it anyway.
# """

# # ---------------------------------------------------------------------------
# # 4. Build rails
# # ---------------------------------------------------------------------------
# config_zerotrust = RailsConfig.from_content(
#     colang_content=COLANG_ZEROTRUST,
#     yaml_content=YAML_ZEROTRUST
# )

# rails_zerotrust = LLMRails(config_zerotrust, llm=guard_llm)

# print("RAILS READY")


# # ---------------------------------------------------------------------------
# # 5. Chat wrapper (same pattern as your existing chat())
# # ---------------------------------------------------------------------------
# def chat(rails, message):
#     """Send a message through the rails and print input + output."""
#     print(f"\n{'─'*62}")
#     print(f"User : {message}")
#     response = rails.generate(messages=[{"role": "user", "content": message}])
#     content = response.get("content", str(response)) if isinstance(response, dict) else response
#     print(f"Bot  : {content}")
#     print(f"{'─'*62}")
#     return response


