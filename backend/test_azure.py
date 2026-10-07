import asyncio
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient

load_dotenv()

async def test_azure():
    endpoint = os.getenv("AZURE_DI_ENDPOINT")
    key = os.getenv("AZURE_DI_KEY")
    print(f"Endpoint: {endpoint}")
    
    if not endpoint or not key:
        print("Missing credentials!")
        return
        
    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    
    # Create a dummy PDF bytes
    dummy_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000219 00000 n \n0000000307 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n402\n%%EOF\n"
    
    try:
        async with client:
            poller = await client.begin_analyze_document(
                model_id="prebuilt-invoice",
                body=dummy_pdf,
                content_type="application/octet-stream"
            )
            result = await poller.result()
            print("Azure extraction success!")
            print(result)
    except Exception as e:
        print(f"Azure extraction failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test_azure())
