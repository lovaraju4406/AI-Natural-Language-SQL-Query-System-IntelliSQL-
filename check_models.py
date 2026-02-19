from dotenv import load_dotenv
load_dotenv()

from google import genai
import os

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("Available models:")
for model in client.models.list():
    print(model.name)