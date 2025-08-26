"""
Plutus Configuration Management
==============================

Centralized configuration for the Plutus AI system including API keys,
model settings, database connections, and operational parameters.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Find .env file in project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
    else:
        print(f"⚠️ No .env file found at {env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed - environment variables from system only")

@dataclass
class PlutusConfig:
    """
    Central configuration for Plutus system
    """
    
    # Claude API Configuration
    anthropic_api_key: Optional[str] = None
    claude_model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4000
    temperature: float = 0.1
    request_timeout: float = 30.0
    max_retries: int = 3
    
    # Cost Management
    cost_per_input_token: float = 0.000003   # $3 per million tokens
    cost_per_output_token: float = 0.000015  # $15 per million tokens
    daily_cost_limit: float = 50.0           # $50 daily limit
    
    # Database Configuration
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    
    # Memory Management
    max_conversation_length: int = 100
    context_ttl_seconds: int = 3600
    memory_database_path: str = "plutus_memory.db"
    
    # Agent Configuration
    max_parallel_agents: int = 5
    agent_timeout_seconds: float = 30.0
    enable_agent_caching: bool = True
    
    # Monitoring & Observability
    enable_logging: bool = True
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = False
    
    # Integration Settings
    integration_mode: bool = True  # True when running inside Wealthify
    standalone_mode: bool = False  # True when running as standalone service
    
    # Test Data Paths (for standalone testing)
    sample_users_path: str = "data/sample_users.json"
    sample_questions_path: str = "data/sample_questions.json"
    
    # Security
    enable_pii_scrubbing: bool = True
    encrypt_sensitive_data: bool = True
    
    def __post_init__(self):
        """Initialize configuration from environment variables"""
        
        # Load from environment
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", self.anthropic_api_key)
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.redis_url = os.getenv("REDIS_URL", self.redis_url)
        
        # Integration mode detection
        self.integration_mode = os.getenv("PLUTUS_INTEGRATION_MODE", "true").lower() == "true"
        self.standalone_mode = not self.integration_mode
        
        # Validate required settings
        self.validate()
    
    def validate(self):
        """Validate configuration settings"""
        
        if not self.anthropic_api_key:
            print("⚠️  ANTHROPIC_API_KEY not found - will run in simulation mode")
            print("   Add ANTHROPIC_API_KEY to environment variables for AI-powered responses")
        
        # Skip file validation in integration mode (files not needed when integrated)
        if self.standalone_mode:
            # Only validate sample files when running standalone
            project_root = Path(__file__).parent.parent.parent.parent
            sample_users_path = str(project_root / "data/sample_users.json")
            sample_questions_path = str(project_root / "data/sample_questions.json")
            
            if not Path(sample_users_path).exists():
                print(f"⚠️  Sample users file not found: {sample_users_path}")
            
            if not Path(sample_questions_path).exists():
                print(f"⚠️  Sample questions file not found: {sample_questions_path}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "claude_model": self.claude_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "max_conversation_length": self.max_conversation_length,
            "context_ttl_seconds": self.context_ttl_seconds,
            "max_parallel_agents": self.max_parallel_agents,
            "agent_timeout_seconds": self.agent_timeout_seconds,
            "daily_cost_limit": self.daily_cost_limit,
            "integration_mode": self.integration_mode,
            "standalone_mode": self.standalone_mode,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "PlutusConfig":
        """Create config from dictionary"""
        return cls(**config_dict)
    
    @classmethod
    def development(cls) -> "PlutusConfig":
        """Development configuration preset"""
        return cls(
            claude_model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_conversation_length=50,
            context_ttl_seconds=1800,  # 30 minutes
            daily_cost_limit=10.0,     # $10 for development
            enable_logging=True,
            log_level="DEBUG",
            enable_metrics=True,
            enable_tracing=True
        )
    
    @classmethod
    def production(cls) -> "PlutusConfig":
        """Production configuration preset"""
        return cls(
            claude_model="claude-3-5-sonnet-20241022",
            temperature=0.1,
            max_conversation_length=100,
            context_ttl_seconds=3600,  # 1 hour
            daily_cost_limit=200.0,    # $200 for production
            enable_logging=True,
            log_level="INFO",
            enable_metrics=True,
            enable_tracing=True,
            encrypt_sensitive_data=True
        )

# Global config instance
config = PlutusConfig.development()

def get_config() -> PlutusConfig:
    """Get the global configuration instance"""
    return config

def set_config(new_config: PlutusConfig):
    """Set the global configuration instance"""
    global config
    config = new_config