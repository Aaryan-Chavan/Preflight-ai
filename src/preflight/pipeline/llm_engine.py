import json
import urllib.request
import urllib.error
from typing import Tuple
from loguru import logger

from preflight.core.models import ChangeSet, PopupPayload, RiskLevel
from preflight.config.settings import settings

def _build_prompt(change_set: ChangeSet) -> str:
    """
    Constructs an optimized prompt strictly containing the code changes.
    We keep the prompt as small as possible to respect the Tier 1/2 Time Budgets.
    """
    lines = [
        f"You are Pre-Flight AI, an expert enterprise code reviewer.",
        f"Review the following Git push for repository '{change_set.repository_name}' on branch '{change_set.branch}'.",
        "Focus on critical bugs, security vulnerabilities, and architectural regressions.",
        "Do NOT complain about missing documentation or minor style issues.\n",
        "=== CODE CHANGES ==="
    ]

    for file in change_set.files:
        lines.append(f"\nFile: {file.new_path or file.old_path} ({file.change_kind.name})")
        for hunk in file.hunks:
            lines.append(f"Lines {hunk.new_start}-{hunk.new_start + hunk.new_lines}:")
            lines.append(hunk.content)

    return "\n".join(lines)

def _call_ollama(prompt: str, model_name: str, timeout: int) -> dict:
    """
    Calls the local Ollama API natively without requiring third-party HTTP libraries.
    Forces strict JSON output using Pydantic's schema generation.
    """
    url = f"{settings.ollama_host}/api/generate"
    
    # We pass Pydantic's exact schema to Ollama to guarantee a perfectly structured response
    payload = {
        "model": model_name,
        "prompt": prompt,
        "format": PopupPayload.model_json_schema(), 
        "stream": False,
        "options": {
            "temperature": 0.1, # Low temperature for deterministic analysis
            "num_predict": 512  # Cap output tokens for speed
        }
    }

    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode("utf-8"), 
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            return json.loads(result["response"])
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to Ollama: {e}")
    except json.JSONDecodeError:
        raise RuntimeError("Ollama returned malformed JSON despite schema enforcement.")

def analyze_changeset(change_set: ChangeSet) -> Tuple[PopupPayload, str]:
    """
    Executes the LLM review pipeline. 
    Implements a graceful failover to a secondary model if the primary fails.
    """
    prompt = _build_prompt(change_set)
    timeout = settings.tier1_timeout_seconds + settings.tier2_timeout_seconds
    
    # Attempt 1: Primary Model
    try:
        logger.debug(f"Calling primary model '{settings.llm_model_name}' (Timeout: {timeout}s)")
        response_data = _call_ollama(prompt, settings.llm_model_name, timeout)
    except Exception as e:
        logger.warning(f"Primary model failed: {e}. Falling back to '{settings.llm_fallback_model}'...")
        
        # Attempt 2: Fallback Model
        try:
            response_data = _call_ollama(prompt, settings.llm_fallback_model, timeout)
        except Exception as fallback_err:
            logger.error(f"Fallback model also failed: {fallback_err}. Failing open.")
            
            # FAIL-OPEN SAFTEY NET: 
            # If Ollama is completely down, we construct a safe 'pass' payload
            # so the developer's push is not blocked.
            return PopupPayload(
                risk_level=RiskLevel.LOW,
                confidence_percentage=0,
                summary="Pre-Flight AI engine is unreachable. Push safely allowed.",
                key_concerns=["Ensure Ollama is running locally."]
            ), "# AI Engine Unreachable\nCould not connect to the local Ollama instance."

    # Map the JSON dictionary cleanly back into our strict Pydantic model
    popup = PopupPayload(**response_data)
    
    # Generate the detailed markdown report
    # (In a V2, this could be a separate asynchronous stream, but for now we format the payload)
    detailed_md = f"# Pre-Flight AI Analysis\n\n**Risk Level:** {popup.risk_level.name}\n\n**Summary:**\n{popup.summary}\n\n**Key Concerns:**\n"
    for concern in popup.key_concerns:
        detailed_md += f"- {concern}\n"

    return popup, detailed_md