"""
Run this to find which Gemini image model works with your API key:
  py test_gemini.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: GOOGLE_API_KEY not set in .env")
    exit(1)

client = genai.Client(api_key=api_key)

# Step 1: List available models
print("=== Available models (image-related) ===")
try:
    models = client.models.list()
    for m in models:
        name = getattr(m, 'name', '') or ''
        if any(x in name.lower() for x in ['image', 'imagen', 'flash', 'vision']):
            print(f"  {name}")
except Exception as e:
    print(f"  Could not list models: {e}")

# Step 2: Try each candidate model
print("\n=== Testing image generation models ===")

# Try Imagen models via generate_images
imagen_models = [
    'imagen-3.0-generate-002',
    'imagen-3.0-generate-001',
    'imagen-4.0-generate-001',
]
for model in imagen_models:
    try:
        response = client.models.generate_images(
            model=model,
            prompt='A simple blue circle on white background',
            config=types.GenerateImagesConfig(number_of_images=1)
        )
        img = response.generated_images[0].image.image_bytes
        print(f"  ✅ {model} WORKS — got {len(img)} bytes")
        break
    except Exception as e:
        print(f"  ❌ {model}: {str(e)[:80]}")

# Try all image-capable Gemini models via generate_content
gemini_models = [
    'gemini-2.5-flash-image',
    'gemini-3.1-flash-image-preview',
    'gemini-3-pro-image-preview',
    'gemini-3.1-flash-lite-preview',
    'gemini-3-flash-preview',
    'gemini-2.0-flash',
    'gemini-2.5-flash',
]
for model in gemini_models:
    try:
        response = client.models.generate_content(
            model=model,
            contents='Draw a simple blue circle on a white background.',
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        got_image = False
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                print(f"  ✅ {model} WORKS — got image ({len(part.inline_data.data)} bytes)")
                got_image = True
                break
        if not got_image:
            print(f"  ⚠  {model}: no error but no image returned (text only)")
    except Exception as e:
        print(f"  ❌ {model}: {str(e)[:100]}")

# Also try imagen-4 with generate_images
print("\n=== Testing imagen-4 with generate_images ===")
for model in ['imagen-4.0-generate-001', 'imagen-4.0-fast-generate-001', 'imagen-4.0-ultra-generate-001']:
    try:
        response = client.models.generate_images(
            model=model,
            prompt='A simple blue circle on white background',
            config=types.GenerateImagesConfig(number_of_images=1)
        )
        img = response.generated_images[0].image.image_bytes
        print(f"  ✅ {model} WORKS — got {len(img)} bytes")
    except Exception as e:
        print(f"  ❌ {model}: {str(e)[:100]}")

print("\nDone. Share the output above and I'll update gemini_gen.py to use the working model.")
