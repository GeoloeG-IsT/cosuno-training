#!/usr/bin/env python3
"""List all available Gemini models."""
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"✅ API Key loaded: {api_key[:20]}...\n")

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("📋 Available Gemini Models:\n")
    for model in genai.list_models():
        print(f"  • {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"    Methods: {model.supported_generation_methods}")
        print()
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
