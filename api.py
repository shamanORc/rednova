from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

history = {}

def ask_ai(user_id, message):

    if user_id not in history:
        history[user_id] = [
            {
                "role": "system",
                "content": "You are a friendly cybersecurity and OSINT assistant that talks naturally with users."
            }
        ]

    history[user_id].append({
        "role": "user",
        "content": message
    })

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=history[user_id],
        temperature=0.7
    )

    reply = response.choices[0].message.content

    history[user_id].append({
        "role": "assistant",
        "content": reply
    })

    return reply
