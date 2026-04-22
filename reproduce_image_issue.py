import asyncio
import os
import logging
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from reasoner.infrastructure.llm.image_generation import generate_images

logging.basicConfig(level=logging.INFO)

async def main():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in .env")
        return

    prompt = "A futuristic city with flying cars and neon lights"
    print(f"Generating images for: {prompt}")
    
    result = await generate_images(prompt, preset="budget", enhance=False)
    
    if result["success"]:
        print("Success!")
        for img in result["images"]:
            print(f"Model used: {img['model_used']}")
            print(f"Image data prefix: {img['image_data'][:50]}...")
    else:
        print(f"Failed: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
