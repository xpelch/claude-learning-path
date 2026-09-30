"""Claude API lab: chat helpers (claude-learning-path).

Setup (in your lab folder):
  uv init && uv add anthropic python-dotenv      (or: pip install anthropic python-dotenv)
  Put ANTHROPIC_API_KEY=... in a .env file yourself and add .env to .gitignore.
  Optionally set ANTHROPIC_MODEL; check the API docs for current model ids.
"""
import os

from dotenv import load_dotenv
from anthropic import Anthropic
from anthropic.types import Message

load_dotenv()
client = Anthropic()
model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")


def add_user_message(messages, message):
    """Append a user turn: a string, a list of content blocks, or a Message."""
    messages.append({"role": "user", "content": message.content if isinstance(message, Message) else message})


def add_assistant_message(messages, message):
    """Append an assistant turn: a string, a list of content blocks, or a Message."""
    messages.append({"role": "assistant", "content": message.content if isinstance(message, Message) else message})


def chat(messages, system=None, temperature=1.0, stop_sequences=None, tools=None, max_tokens=1000):
    """Call the Messages API and return the full Message (use text_from_message for the text)."""
    params = {"model": model, "max_tokens": max_tokens, "messages": messages, "temperature": temperature}
    if system:
        params["system"] = system
    if stop_sequences:
        params["stop_sequences"] = stop_sequences
    if tools:
        params["tools"] = tools
    return client.messages.create(**params)


def text_from_message(message):
    return "\n".join(block.text for block in message.content if block.type == "text")
