"""Shared harness for failure-matrix scenario scripts.

Re-seeds the database, starts the MCP server, runs a sequence of user
messages through the Anthropic tool-use loop, and logs every turn.
"""

import asyncio
import json
import os
import subprocess
import sys

import anthropic
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(DEMO_DIR, os.pardir, ".env"))

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


def reseed_db():
    subprocess.run(
        [sys.executable, os.path.join(DEMO_DIR, "db", "seed.py")],
        check=True,
        capture_output=True,
    )


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


def mcp_tools_to_anthropic(mcp_tools: list) -> list[dict]:
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in mcp_tools
    ]


async def call_mcp_tool(
    session: ClientSession, name: str, arguments: dict
) -> tuple[str, bool]:
    result = await session.call_tool(name, arguments)
    parts = []
    for block in result.content:
        if hasattr(block, "text"):
            parts.append(block.text)
        else:
            parts.append(str(block))
    return "\n".join(parts), bool(result.isError)


async def run_scenario(
    title: str,
    user_messages: list[str],
    between_messages=None,
):
    """Run a scenario end-to-end.

    Args:
        title: Scenario name for log headers.
        user_messages: User messages sent in sequence; each gets a full
                       tool-use loop before the next is sent.
        between_messages: Optional ``async def cb(msg_index)`` called
                         after each message completes (except the last).
    """
    reseed_db()

    client = anthropic.Anthropic()
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(DEMO_DIR, "mcp_server.py")],
        env={**os.environ},
        cwd=DEMO_DIR,
    )

    log_header(f"Scenario: {title}")

    try:
        async with stdio_client(server_params, errlog=sys.stderr) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                anthropic_tools = mcp_tools_to_anthropic(tools_result.tools)
                log_text(
                    "system",
                    f"MCP ready — {len(anthropic_tools)} tools: "
                    f"{', '.join(t['name'] for t in anthropic_tools)}",
                )

                messages: list[dict] = []

                for msg_idx, user_input in enumerate(user_messages):
                    log_text("user", user_input)
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
                                assistant_content.append(
                                    {"type": "text", "text": block.text}
                                )
                            elif block.type == "tool_use":
                                log_tool_call(block.name, block.id, block.input)
                                assistant_content.append(
                                    {
                                        "type": "tool_use",
                                        "id": block.id,
                                        "name": block.name,
                                        "input": block.input,
                                    }
                                )
                                tool_calls.append(block)

                        messages.append(
                            {"role": "assistant", "content": assistant_content}
                        )

                        if response.stop_reason == "end_turn":
                            break

                        if response.stop_reason == "tool_use" and tool_calls:
                            tool_results = []
                            transport_failed = False
                            for tc in tool_calls:
                                try:
                                    text, err = await call_mcp_tool(
                                        session, tc.name, tc.input
                                    )
                                except Exception as e:
                                    text = (
                                        f"Transport error: {type(e).__name__}: {e}"
                                    )
                                    err = True
                                    transport_failed = True
                                log_tool_result(tc.id, text, err)
                                tool_results.append(
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tc.id,
                                        "content": text,
                                        "is_error": err,
                                    }
                                )
                                if transport_failed:
                                    break
                            messages.append(
                                {"role": "user", "content": tool_results}
                            )
                            if transport_failed:
                                log_text(
                                    "system",
                                    "MCP transport failed — aborting turn loop.",
                                )
                                break
                        else:
                            break
                    else:
                        log_text(
                            "system", f"Reached max turns ({MAX_TURNS})."
                        )

                    if between_messages and msg_idx < len(user_messages) - 1:
                        await between_messages(msg_idx)

    except Exception as e:
        log_text("system", f"Fatal: {type(e).__name__}: {e}")

    log_header("Scenario complete")
