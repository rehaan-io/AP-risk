from typing import List, Dict, Any
from services.llm_service import llm_provider
import json

async def generate_risk_explanation(risk_data: List[Dict[str, Any]], role: str = "Finance Manager") -> str:
    """
    Uses the abstract LLM provider (currently Gemini) to explain the risks.
    Keeps architecture ready for Microsoft Foundry / MAI-Thinking-1.
    """
    if not risk_data:
        return "No significant risks detected."
    
    # We call the provider for the aggregated risks
    return await llm_provider.explain_risk(risk_data, role)
