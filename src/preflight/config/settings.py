#settings.py
import json
from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from preflight.core.enums import Language
from preflight.config.paths import CONFIG_FILE

class PreflightSettings(BaseSettings):
    """
    Global configuration for Pre-Flight AI.
    Settings can be overridden via environment variables (e.g., PREFLIGHT_LLM_TIMEOUT_SECONDS=45)
    or by editing the global config.json file.
    """
    
    # -------------------------------------------------------------------------
    # AI & Model Configuration
    # -------------------------------------------------------------------------
    llm_model_name: str = Field(
        default="qwen3-4b-instruct", 
        description="Primary Ollama model for AI reasoning."
    )
    llm_fallback_model: str = Field(
        default="gemma3:4b", 
        description="Secondary fallback model if Qwen fails."
    )
    ollama_host: str = Field(
        default="http://127.0.0.1:11434", 
        description="Local URL for the Ollama inference server."
    )

    # -------------------------------------------------------------------------
    # Pipeline Time Budgets (Tiered Latency)
    # -------------------------------------------------------------------------
    tier0_timeout_seconds: int = Field(
        default=2, 
        description="Max time for Git diff extraction and Tree-sitter AST parsing."
    )
    tier1_timeout_seconds: int = Field(
        default=5, 
        description="Max time for Static Analysis, LSP, and ML Risk Prediction."
    )
    tier2_timeout_seconds: int = Field(
        default=15, 
        description="Max time for streaming the LLM popup narrative."
    )

    # -------------------------------------------------------------------------
    # Security, Privacy & Sync
    # -------------------------------------------------------------------------
    sync_mode: Literal["metadata", "full"] = Field(
        default="metadata", 
        description="'metadata' completely redacts code snippets before Firestore upload. 'full' uploads snippets."
    )
    fail_open: bool = Field(
        default=True, 
        description="CRITICAL: If True, any internal pipeline crash allows the push to continue. Never block a developer."
    )
    block_on_high_risk: bool = Field(
        default=False,
        description="If True, a 'High' risk prediction automatically sets the exit code to 1 (Cancel). Can be bypassed via Git."
    )

    # -------------------------------------------------------------------------
    # Cloud & Firebase Configuration
    # -------------------------------------------------------------------------
    firebase_project_id: str = Field(
        default="preflight-aaryan1910", 
        description="Firebase Project ID for direct Firestore REST API sync."
    )

    # -------------------------------------------------------------------------
    # Language Support Allowlist
    # -------------------------------------------------------------------------
    supported_languages: List[Language] = Field(
        default=[
            Language.PYTHON, 
            Language.JAVASCRIPT, 
            Language.TYPESCRIPT, 
            Language.JAVA, 
            Language.CPP
        ],
        description="Languages to actively parse and analyze. Others are ignored to save time."
    )

    model_config = SettingsConfigDict(
        env_prefix="PREFLIGHT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


def load_settings() -> PreflightSettings:
    """
    Load settings from defaults, overlay with config.json (if it exists), 
    and finally overlay with any environment variables.
    """
    settings = PreflightSettings()
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            # Merge JSON values over the defaults, maintaining Pydantic validation
            settings = PreflightSettings(**{**settings.model_dump(), **file_config})
        except Exception:
            # If the file is corrupted, safely fallback to defaults
            pass
            
    return settings

# Global singleton to be imported across the application
settings = load_settings()