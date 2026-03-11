from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def ask_ai(message):

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {
                "role": "system",
                "content": "You are an OSINT assistant specialized in investigation."
            },
            {
                "role": "user",
                "content": message
            }
        ],
        temperature=0.6
    )

    return response.choices[0].message.content
