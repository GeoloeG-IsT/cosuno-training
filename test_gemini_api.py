#!/usr/bin/env python3
"""Test Gemini API connection and list available models."""
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"✅ API Key loaded: {api_key[:20]}...\n")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    print("Testing Gemini models...")
    
    # Try with gemini-3-pro-preview first (older, more stable)
    models_to_test = [
        "gemini-3-pro-preview"
    ]
    
    for model in models_to_test:
        try:
            print(f"\nTesting {model}...", end=" ")
            llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=0.3
            )
            response = llm.invoke("Say 'Working!'")
            print(f"✅ Works! Response: {response.content}")
            break
        except Exception as e:
            print(f"❌ Failed: {str(e)[:80]}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
