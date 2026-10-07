import os
import json
from typing import Dict, Any, List
from google import genai
from google.genai import types
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from schemas.gemini_schemas import LLMPolicyResponse

class LLMProvider:
    async def interpret_policy(self, policy_text: str) -> List[Dict[str, Any]]:
        """
        Interprets policy text and returns a list of canonical policy rules.
        """
        raise NotImplementedError

    async def explain_risk(self, risk_data: Dict[str, Any], role: str) -> str:
        """
        Takes structured risk evidence and outputs a role-tailored human-readable explanation.
        """
        raise NotImplementedError

class GeminiProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    @retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(5))
    async def interpret_policy(self, policy_text: str) -> List[Dict[str, Any]]:
        if not self.client:
            return [{'rule_type': 'POLICY_EXTRACTION_FAILED', 'status': 'REQUIRES_CONFIRMATION', 'reason': 'LLM Not configured'}]
        
        prompt = f"""You are an expert AI policy interpreter for an Accounts Payable Risk & Exception Management System.
        Your task is to analyze the following company policy document extract and convert it into structured canonical rules.
        
        CRITICAL INSTRUCTIONS:
        1. Extract rules from ALL formats: prose, paragraphs, bullet points, exceptions, and tables.
        2. DO NOT lose paragraphs or literary content. If a policy states 'All purchases above 50K require a PO except emergency purchases', you MUST capture both the rule and the exception.
        3. Extract Approval Hierarchies (e.g. 0-50k = Manager, 50k+ = Controller).
        4. If the policy defines specific percentages, tolerances, caps, or limits (e.g. 'Price variance must not exceed 8%'), extract them exactly.
        5. Respect SCORING and SCOPES. If a tolerance is only for 'IT Equipment', set scope.company_wide=false and scope.category='IT Equipment'.
        6. PRESERVE SOURCE: Include the exact original text snippets where you found the rule.
        
        RULE TYPES MAPPING TO RISK ENGINE:
        - PO_REQUIRED: Use for purchase order thresholds and requirements.
        - TOLERANCE: Use for price, quantity, or amount variance tolerances. (Set conditions.type to 'price_variance', 'quantity_variance', or 'amount_variance').
        - INVOICE_SPLITTING: Use for rules about splitting invoices within a time window (Set conditions.aggregation_window_days).
        - APPROVAL_LIMIT: Use for manual approval routing thresholds and roles.
        - CUSTOM_POLICY_RULE: Only use if the rule is highly bespoke and cannot map to the above.
        
        Policy Extract:
        {policy_text}
        """
        
        try:
            # We use gemini-3.5-flash for faster response
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LLMPolicyResponse,
                    temperature=0.1
                ),
            )
            
            # The response.text is guaranteed by Gemini to match LLMPolicyResponse JSON schema
            validated_data = LLMPolicyResponse.model_validate_json(response.text)
            
            # Convert Pydantic models to dicts for the database
            return [rule.model_dump(exclude_none=True) for rule in validated_data.rules]
            
        except Exception as e:
            print(f"Gemini Policy Interpretation Error: {e}")
            # Reraise exception if it's an API error so tenacity can retry
            if "503" in str(e) or "429" in str(e):
                raise
            return [{'rule_type': 'POLICY_EXTRACTION_FAILED', 'status': 'REQUIRES_CONFIRMATION', 'confidence': 0.0, 'reason': str(e)}]

    async def explain_risk(self, risk_data: Dict[str, Any], role: str) -> str:
        if not self.client:
            return "Risk explanation unavailable (LLM not configured)."
        
        prompt = f"""You are an Accounts Payable risk explanation assistant.
        The deterministic risk engine has already analyzed this invoice.
        
        Do NOT perform your own risk calculation.
        Do NOT invent facts.
        Do NOT introduce a new risk that is not present in the supplied evidence.
        
        Explain clearly:
        1. What is wrong with this invoice.
        2. Which invoice ID is affected.
        3. What evidence caused the flag.
        4. Which policy/rule was violated or triggered.
        5. What the reviewer should verify.
        
        Keep the explanation concise and suitable for a finance employee (2-5 concise sentences).
        
        Input Data:
        {json.dumps(risk_data, indent=2)}
        """
        
        try:
            # We use gemini-3.5-flash to bypass global 503 load on 3.8-flash
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                ),
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini Explanation Error: {e}")
            return "Risk explanation could not be generated."

# Global singleton
llm_provider = GeminiProvider()
