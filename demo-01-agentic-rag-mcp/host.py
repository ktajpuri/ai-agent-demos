"""Thin host for the payments support assistant demo.

Explicit tool-use loop: Anthropic API -> parse tool_use blocks ->
route to MCP server over stdio -> feed tool_result blocks back.
Every turn is logged to stdout. No framework.
"""

import asyncio
import json
import os
import sys

import anthropic
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, os.pardir, ".env"))

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
MAX_TURNS = 10

SYSTEM_PROMPT = (
    "You are a payments support assistant. You have access to three tools:\n"
    "- search_policy: search internal policy documents for rules about refunds, disputes, escalation, etc.\n"
    "- lookup_order: look up an order by ID to see its status, amount, and any existing refunds.\n"
    "- issue_refund: issue a refund for an order (enforces business rules server-side).\n\n"
    "Always check policy before taking action when the request involves rules or eligibility. "
    "Always look up the order before issuing a refund. "
    "If a tool returns an error, explain it to the user — do not retry with the same arguments."
)

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def log_header(label: str):
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def log_text(role: str, text: str):
    print(f"\n[{role}] {text}")


def log_tool_call(name: str, tool_id: str, arguments: dict):
    print(f"\n  ┌─ tool_use: {name}")
    print(f"  │  id: {tool_id}")
    print(f"  │  args: {json.dumps(arguments, indent=2).replace(chr(10), chr(10) + '  │  ')}")
    print(f"  └─")


def log_tool_result(tool_id: str, content: str, is_error: bool):
    marker = "ERROR" if is_error else "result"
    preview = content[:500] + ("…" if len(content) > 500 else "")
    print(f"\n  ┌─ tool_result ({marker})")
    print(f"  │  id: {tool_id}")
    for line in preview.split("\n"):
        print(f"  │  {line}")
    print(f"  └─")


# ---------------------------------------------------------------------------
# MCP tool routing
# ---------------------------------------------------------------------------

def mcp_tools_to_anthropic(mcp_tools: list) -> list[dict]:
    """Convert MCP Tool objects to Anthropic tool-use format."""
    tools = []
    for t in mcp_tools:
        tools.append({
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        })
    return tools


async def call_mcp_tool(session: ClientSession, name: str, arguments: dict) -> tuple[str, bool]:
    """Call an MCP tool and return (content_text, is_error)."""
    result = await session.call_tool(name, arguments)
    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
        else:
            parts.append(str(block))
    text = "\n".join(parts)
    return text, bool(result.isError)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def run():
    client = anthropic.Anthropic()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(BASE_DIR, "mcp_server.py")],
        env={**os.environ},
        cwd=BASE_DIR,
    )

    log_header("Starting MCP server")

    async with stdio_client(server_params, errlog=sys.stderr) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            anthropic_tools = mcp_tools_to_anthropic(tools_result.tools)
            print(f"  MCP server ready — {len(anthropic_tools)} tools: "
                  f"{', '.join(t['name'] for t in anthropic_tools)}")

            messages: list[dict] = []

            log_header("Payments Support Assistant (type 'quit' to exit)")

            while True:
                try:
                    user_input = input("\nyou> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nGoodbye.")
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    print("Goodbye.")
                    break

                messages.append({"role": "user", "content": user_input})

                for turn in range(MAX_TURNS):
                    log_header(f"Turn {turn + 1}")

                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=SYSTEM_PROMPT,
                        tools=anthropic_tools,
                        messages=messages,
                    )

                    log_text("model", f"stop_reason={response.stop_reason}")

                    assistant_content = []
                    tool_calls = []

                    for block in response.content:
                        if block.type == "text":
                            log_text("assistant", block.text)
                            assistant_content.append({
                                "type": "text",
                                "text": block.text,
                            })
                        elif block.type == "tool_use":
                            log_tool_call(block.name, block.id, block.input)
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })
                            tool_calls.append(block)

                    messages.append({"role": "assistant", "content": assistant_content})

                    if response.stop_reason == "end_turn":
                        break

                    if response.stop_reason == "tool_use" and tool_calls:
                        tool_results = []
                        for tc in tool_calls:
                            content_text, is_error = await call_mcp_tool(
                                session, tc.name, tc.input
                            )
                            log_tool_result(tc.id, content_text, is_error)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tc.id,
                                "content": content_text,
                                "is_error": is_error,
                            })
                        messages.append({"role": "user", "content": tool_results})
                    else:
                        break
                else:
                    log_text("system", f"Reached max turns ({MAX_TURNS}), stopping.")


if __name__ == "__main__":
    asyncio.run(run())
