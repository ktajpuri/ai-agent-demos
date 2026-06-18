"""Scenario 6: Transport failure.

The MCP server process is killed between the first and second message.
The first lookup succeeds normally; the second request triggers a tool
call that hits a dead transport.

Observe: does the host crash, hang, or surface a meaningful error?
"""

import asyncio
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import log_header, run_scenario


async def _kill_mcp_server(msg_index: int):
    """Kill the MCP server subprocess after the first message."""
    if msg_index != 0:
        return

    log_header("INJECTING FAULT: Killing MCP server process")
    result = subprocess.run(
        ["pgrep", "-f", "mcp_server.py"],
        capture_output=True,
        text=True,
    )
    my_pid = os.getpid()
    for pid_str in result.stdout.strip().split("\n"):
        pid_str = pid_str.strip()
        if pid_str and int(pid_str) != my_pid:
            os.kill(int(pid_str), signal.SIGKILL)
            print(f"  Killed process {pid_str}")
    await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(
        run_scenario(
            title="6 · Transport failure",
            user_messages=[
                "Look up order ORD-001",
                "Now issue a full refund for order ORD-001",
            ],
            between_messages=_kill_mcp_server,
        )
    )
