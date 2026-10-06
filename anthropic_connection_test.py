"""Exchange workload identity credentials and verify a Claude Messages request."""

import os
import sys

from worker import AnthropicProvider, WorkerError


def main():
    if not os.environ.get("ANTHROPIC_IDENTITY_TOKEN_FILE"):
        print("Error: Set ANTHROPIC_IDENTITY_TOKEN_FILE for the federation test.", file=sys.stderr)
        return 1
    try:
        provider = AnthropicProvider()
    except WorkerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    try:
        message = provider.client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello, Claude"}],
        )
        text = "\n".join(block.text for block in message.content if block.type == "text")
        if message.stop_reason != "end_turn" or not text.strip():
            raise WorkerError("Claude returned an incomplete or empty greeting.")
        print("Workload identity exchange and Claude Messages request succeeded.")
        print(text)
        return 0
    except (provider.sdk.AnthropicError, WorkerError, OSError, ValueError):
        print(
            "Error: Anthropic connection test failed. Check the authentication stream, "
            "rule claims, identity IDs, and model access.",
            file=sys.stderr,
        )
        return 1
    finally:
        provider.close()


if __name__ == "__main__":
    sys.exit(main())
