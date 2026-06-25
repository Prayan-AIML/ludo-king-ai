#!/usr/bin/env python3
"""
Interactive terminal chat with an OpenAI model.

- Remembers everything you said earlier *within the same run* (session memory).
- Forgets everything once you quit. Nothing is saved to disk.
"""

import os
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit(
        "The 'openai' package isn't installed.\n"
        "Run:  pip install openai"
    )

MODEL = "gpt-5.4-nano"   # change this if you want a different model


def get_api_key() -> str:
    # Use the OPENAI_API_KEY environment variable if it's set,
    # otherwise just ask you to paste it in.
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()
    key = input("Paste your OpenAI API key and press Enter: ").strip()
    if not key:
        sys.exit("No API key provided. Exiting.")
    return key


def main() -> None:
    client = OpenAI(api_key=get_api_key())

    # This list is the "memory". Each message you send and each reply
    # gets appended, so the model sees the whole conversation every turn.
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

    print(f"\nChatting with {MODEL}. Type 'quit' or 'exit' to stop.")
    print("(Your conversation is remembered until you quit.)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
            )
        except Exception as e:
            print(f"\n[Error talking to the API] {e}\n")
            # Drop the failed message so we don't resend a broken state.
            messages.pop()
            continue

        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

        print(f"\n{MODEL}: {reply}\n")


if __name__ == "__main__":
    main()
