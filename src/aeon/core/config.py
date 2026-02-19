from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum

class TrustLevel(str, Enum):
    FULL = "full"
    RESTRICTED = "restricted"
    ISOLATED = "isolated"

class ModelConfig(BaseModel):
    provider: str = Field(..., description="LLM provider (openai, ollama, anthropic, etc)")
    name: str = Field(..., description="Model name (e.g. gpt-4o, phi3.5)")
    base_url: Optional[str] = Field(None, description="Base URL for local providers")
    api_key: Optional[str] = Field(None, description="API Key (can be env var)")
    temperature: float = 0.7

class BrowserConfig(BaseModel):
    enabled: bool = False
    headless: bool = True
    downloads_path: Optional[str] = None

class MemoryConfig(BaseModel):
    enabled: bool = True
    storage_path: str = "./memory.db"
    vector_store: Optional[str] = None # future use

class AutomationConfig(BaseModel):
    enabled: bool = False
    timezone: str = "UTC"

class WebhookConfig(BaseModel):
    enabled: bool = False
    path: str = "/webhook"
    secret: Optional[str] = None

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    webhooks: bool = False
    cors_origins: List[str] = ["*"]

class AgentConfig(BaseModel):
    name: str
    description: Optional[str] = None
    model: ModelConfig
    trust_level: TrustLevel = TrustLevel.RESTRICTED
    system_prompt: Optional[str] = None
    tools: List[str] = Field(default_factory=list, description="List of tool names/import paths")

class CapabilitiesConfig(BaseModel):
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)

class AeonConfig(BaseSettings):
    version: str = "1.0"
    agent: AgentConfig
    capabilities: CapabilitiesConfig = Field(default_factory=CapabilitiesConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    class Config:
        env_prefix = "AEON_"
        env_nested_delimiter = "__"
        case_sensitive = False

def load_config(path: str = "aeon.yaml") -> AeonConfig:
    import yaml
    import os
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found at {path}")
        
    with open(path, "r") as f:
        data = yaml.safe_load(f)
        
    return AeonConfig(**data)
