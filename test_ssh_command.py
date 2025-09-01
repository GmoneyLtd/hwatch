#!/usr/bin/env python3

import asyncio
import asyncssh
import sys
import os

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_ssh_command():
    """Test SSH command execution to see what output we get"""
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

        print("\n=== FORMATTED OUTPUT ===")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        else:
            print("No stdout received")

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        conn.close()
        await conn.wait_closed()
        print("Connection closed")

    except asyncssh.misc.DisconnectError as e:
        print(f"SSH disconnect error: {e}")
    except asyncssh.misc.ConnectionLost as e:
        print(f"SSH connection lost: {e}")
    except asyncio.TimeoutError:
        print("Command execution timed out")
    except Exception as e:
        print(f"General error: {e}")
        print(f"General error type: {type(e)}")


if __name__ == "__main__":
    asyncio.run(test_ssh_command())
