"""
List available Gemini models to find the correct embedding model for v1beta API
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google import genai
from app.config import settings

def list_models():
    """List all available models in the Gemini API"""
    
    if not settings.gemini_api_key:
        print("❌ GEMINI_API_KEY not configured")
        return
    
    print("Connecting to Gemini API...")
    client = genai.Client(api_key=settings.gemini_api_key)
    
    print("\nListing all available models:\n")
    print("=" * 80)
    
    try:
        models = client.models.list()
        
        embedding_models = []
        generation_models = []
        
        for model in models:
            model_name = model.name
            supported_methods = getattr(model, 'supported_generation_methods', [])
            
            # Check if it's an embedding model
            if 'embedContent' in supported_methods or 'embedding' in model_name.lower():
                embedding_models.append((model_name, supported_methods))
            elif 'generateContent' in supported_methods:
                generation_models.append((model_name, supported_methods))
        
        print("\n📊 EMBEDDING MODELS:")
        print("-" * 80)
        if embedding_models:
            for name, methods in embedding_models:
                print(f"  ✓ {name}")
                print(f"    Methods: {', '.join(methods)}")
        else:
            print("  No embedding models found")
        
        print("\n💬 GENERATION MODELS:")
        print("-" * 80)
        for name, methods in generation_models[:5]:  # Show first 5
            print(f"  ✓ {name}")
        
        print(f"\n  ... and {len(generation_models) - 5} more generation models")
        
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")

if __name__ == "__main__":
    list_models()