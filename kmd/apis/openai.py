from typing import Optional
from openai import OpenAI


def openai_completion(model: str, system_message: str, user_message: str) -> str:
    client = OpenAI()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    )

    output = completion.choices[0].message.content
    if not output:
        raise ValueError("No result from OpenAI: {completion}")

    return output
