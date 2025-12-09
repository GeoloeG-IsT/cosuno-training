#!/usr/bin/env python3
"""Test the Gemini API key and available models."""

import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key loaded: {api_key[:20]}...{api_key[-10:] if api_key else 'NONE'}")
print()

try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("🔍 Available models:")
    for model in genai.list_models():
        print(f"  - {model.name}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"API key status: {'Present' if api_key else 'Missing'}")
