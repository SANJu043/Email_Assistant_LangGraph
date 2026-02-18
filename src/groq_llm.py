import os
import json
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
dotenv_path = base_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def llm_call_1(prompt: str, model: str = "openai/gpt-oss-120b") -> str:
    """
    Sends a prompt to Groq and returns raw text.
    Intended for STRICT JSON outputs (judge, eval, etc.)
    """
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=1024
    )

    return completion.choices[0].message.content.strip()

def generate_structured_json(prompt: str, model: str = "llama3-8b-8192") -> dict:
    """
    Calls Groq and guarantees JSON parsing.
    Raises error if model misbehaves.
    """

    response = llm_call(prompt, model=model)

    # Defensive cleaning
    clean = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Groq did not return valid JSON.\nRaw output:\n{response}"
        ) from e
