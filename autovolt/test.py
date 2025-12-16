import os
from openai import OpenAI

# Replace with your actual key
API_KEY = "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"  # Or get from environment
# Or: API_KEY = os.environ.get('OPENAI_API_KEY')

try:
    client = OpenAI(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    
    print("✅ SUCCESS!")
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")