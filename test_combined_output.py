#!/usr/bin/env python3

import asyncio
import asyncssh
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_combined_output():
    """Test combining stdout and stderr to capture all output"""
    # Device configuration - adjust these values to match your setup
    host = "192.168.100.201"  # vmc device IP
    username = "admin"
    password = "Admin#123"
    port = 22
    command = "show datapath session counters"

    try:
        print(f"Connecting to {host}...")
        conn = await asyncssh.connect(
            host,
            port=port,
            username=username,
            password=password,
            known_hosts=None,
            connect_timeout=30,
        )

        print(f"Connected successfully: {not conn.is_closed()}")
        print(f"Executing command: {command}")

        # Execute command
        result = await conn.run(command, check=True, timeout=30)

        print("\n=== RESPONSE DETAILS ===")
        print(f"Result exit status: {result.exit_status}")
        print(f"Result stdout: {repr(result.stdout)}")
        print(f"Result stderr: {repr(result.stderr)}")

        # Combine stdout and stderr (our fix)
        stdout = result.stdout
        stderr = result.stderr
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        # Combine stdout and stderr to ensure we capture all output
        # Some devices send output to stderr instead of stdout
        combined_output = ""
        if stdout:
            combined_output += stdout
        if stderr:
            combined_output += stderr

        print(f"Combined output: {repr(combined_output)}")

        print("\n=== FORMATTED OUTPUT ===")
        if combined_output:
            print("COMBINED OUTPUT:")
            print(combined_output)
        else:
            print("No output received")

        conn.close()
        await conn.wait_closed()
        print("Connection closed")

    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")


if __name__ == "__main__":
    asyncio.run(test_combined_output())
