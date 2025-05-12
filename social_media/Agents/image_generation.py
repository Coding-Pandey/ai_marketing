import openai
# openai.api_key = os.getenv("OPENAI_API_KEY")
from openai import OpenAI
import os
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) 
prompts ="""
Early Detection, Lifelong Protection\n\nIn a world where health is our most precious asset, taking proactive steps can mean the difference between a simple routine test and facing a formidable challenge. Our campaign, \"Early Detection, Lifelong Protection,\" is crafted to inspire individuals to seize control of their health destiny. By utilising our 99% accurate, non-invasive colon cancer screening test, you pave the way for a healthier tomorrow.\n\nImagine catching potential threats early, redirecting towards a life of peace and health. It’s more than just a test—it’s a commitment to a future unburdened by disease. Our campaign aims to enlighten busy professionals
"""

def generate_image(prompt):
    response = client.images.generate(
        model="dall-e-2",  # or "dall-e-2" if needed
        prompt=prompt,
        size="1024x1024",
        n=1
    )
    return response.data[0].url

data = generate_image(prompts)
print(data)