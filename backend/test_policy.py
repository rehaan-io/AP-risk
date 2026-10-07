import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_policy():
    from services.policy_extractor import extract_and_interpret_policy
    
    # Create a dummy policy text
    dummy_text = "All IT equipment purchases above 50000 INR require a Purchase Order. Exceptions apply to emergency purchases approved by the CIO."
    
    # Let's test just the LLM part first since that's the most likely failure point (JSON parsing)
    from services.llm_service import llm_provider
    print("Testing LLM Provider...")
    rules = await llm_provider.interpret_policy(dummy_text)
    print("Rules extracted:", rules)

if __name__ == "__main__":
    asyncio.run(test_policy())
