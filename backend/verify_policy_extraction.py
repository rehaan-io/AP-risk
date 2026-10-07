import asyncio
import json
import os
from services.policy_extractor import extract_and_interpret_policy

# Ensure the env var is loaded for the test
from dotenv import load_dotenv
load_dotenv()

async def main():
    policy_text = """
    All purchases above INR 50,000 require an approved purchase order.
    IT equipment purchases above INR 40,000 also require a purchase order.
    Emergency purchases may bypass the purchase-order requirement when CFO approval has been obtained.
    Invoices may exceed the approved PO value by no more than 3 percent.
    Invoice quantity may exceed the PO quantity by no more than 5 percent.
    Vendor prices more than 8 percent above historical comparable prices require review.
    Transactions from the same vendor and category occurring within 14 days should be evaluated together for possible invoice splitting.
    Purchases between INR 50,001 and INR 100,000 require Department Head approval.
    Purchases above INR 100,000 require Finance Controller approval.
    """
    
    print("Testing extraction...")
    text, rules = await extract_and_interpret_policy('procurement_policy.txt', policy_text.encode('utf-8'))
    
    print(f"Extraction complete! Found {len(rules)} rules.")
    
    for idx, rule in enumerate(rules):
        print(f"\n--- Rule {idx+1} ---")
        print(json.dumps(rule, indent=2))
        
    assert len(rules) >= 9, f"Expected at least 9 rules, but got {len(rules)}"
    print("\nSUCCESS: Extracted sufficient number of rules from a single text block.")

if __name__ == "__main__":
    asyncio.run(main())
