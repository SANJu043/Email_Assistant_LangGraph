import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

def groq_judge(prompt: str) -> dict:
    try:
        completion = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512
        )

        content = completion.choices[0].message.content.strip()

        if not content:
            return {}

        # Remove markdown wrappers
        content = content.replace("```json", "").replace("```", "").strip()

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try extracting JSON manually
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    return {}
            return {}

    except Exception as e:
        print("Groq Judge Error:", e)
        return {}
