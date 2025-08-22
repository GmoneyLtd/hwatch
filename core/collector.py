import asyncio
import re
import time
from typing import Any

import asyncssh
from loguru import logger
from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
    walk_cmd,
)

from core.config_loader import DeviceConfig, TaskConfig

# SSH connection pool dictionary, key is (task_alias, device_name) tuple, value is connection object and last used time
_ssh_connection_pools: dict[tuple[str, str], dict[str, Any]] = {}


async def _get_ssh_connection(task: TaskConfig, device: DeviceConfig) -> asyncssh.SSHClientConnection:
    """Get SSH connection from connection pool, create new connection if not exists or disconnected"""
    pool_key = (task.alias, device.name)
    conn_details = device.connection.ssh

    # Check if connection already exists in connection pool
    if pool_key in _ssh_connection_pools:
        conn_entry = _ssh_connection_pools[pool_key]
        conn = conn_entry["connection"]

        # Check if connection is still valid
        try:
            # More comprehensive connection status check
            if (
                conn._transport is not None
                and not conn._transport.at_eof()
                and not conn.is_closing()
                and not conn._transport.is_closing()
            ):
                # Try sending a simple command to verify connection
                try:
                    await asyncio.wait_for(conn.run("echo test", check=True), timeout=2)
                    # Connection is valid, update last used time
                    conn_entry["last_used"] = time.time()
                    logger.debug(f"[SSH] Reusing existing connection: {task.alias} on {device.name}")
                    return conn
                except Exception as test_e:
                    logger.debug(f"[SSH] Connection test failed: {task.alias} on {device.name} - {test_e}")
                    raise Exception("Connection test failed") from None
            else:
                raise Exception("Connection status check failed")
        except Exception:
            # Connection is disconnected or unavailable, clean up connection pool entry
            try:
                conn.close()
                await conn.wait_closed()
            except Exception:
                pass  # Ignore errors during closing
            del _ssh_connection_pools[pool_key]
            logger.info(f"[SSH] Cleaning up invalid connection and reconnecting: {task.alias} on {device.name}")

    # Create new connection (with retry mechanism)
    logger.info(f"[SSH] Establishing new connection: {task.alias} on {device.name}")

    last_exception = None
    # Ensure conn_details is not None
    retry = conn_details.retry if conn_details else 3
    for attempt in range(retry + 1):  # retry+1 attempts (1 initial attempt + retry retries)
        try:
            # Ensure conn_details is not None
            port = conn_details.port if conn_details else 22
            username = conn_details.username if conn_details else None
            password = conn_details.password if conn_details else None
            timeout = conn_details.timeout if conn_details else 10

            conn = await asyncssh.connect(
                device.ip,
                port=port,
                username=username,
                password=password,
                known_hosts=None,  # Should consider safer host key verification in production
                connect_timeout=timeout,
            )

            # Add connection to connection pool
            _ssh_connection_pools[pool_key] = {
                "connection": conn,
                "last_used": time.time(),
                "task": task.alias,
                "device": device.name,
            }

            if attempt > 0:
                logger.info(
                    f"[SSH] Connection {task.alias} on {device.name} established successfully after {attempt + 1} attempts"
                )

            return conn

        except Exception as e:
            last_exception = e
            # Ensure conn_details is not None
            retry = conn_details.retry if conn_details else 3
            if attempt < retry:
                wait_time = 2**attempt  # Exponential backoff
                logger.warning(
                    f"[SSH] Connection {task.alias} on {device.name} attempt {attempt + 1} failed: {e}. Waiting {wait_time} seconds before retry..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"[SSH] Connection {task.alias} on {device.name} still failed after {attempt + 1} attempts"
                )

    # If all attempts failed, raise the last exception
    if last_exception:
        raise last_exception
    else:
        raise Exception("Connection failed, but no specific exception information") from None


async def _cleanup_ssh_connections():
    """Clean up timed out SSH connections (unused for more than 10 minutes)"""
    current_time = time.time()
    expired_keys = []

    for pool_key, conn_entry in _ssh_connection_pools.items():
        if current_time - conn_entry["last_used"] > 600:  # 10 minutes = 600 seconds
            expired_keys.append(pool_key)

    for pool_key in expired_keys:
        conn_entry = _ssh_connection_pools[pool_key]
        conn = conn_entry["connection"]
        try:
            conn.close()
            await conn.wait_closed()
            logger.info(f"[SSH] Cleaning up timed out connection: {conn_entry['task']} on {conn_entry['device']}")
        except Exception as e:
            logger.warning(f"[SSH] Error closing timed out connection: {e}")
        finally:
            del _ssh_connection_pools[pool_key]


async def _run_ssh_task(task: TaskConfig, device: DeviceConfig) -> str:
    """Execute single SSH collection task, supporting sequential execution of multiple commands."""
    conn_details = device.connection.ssh

    # Process command list
    commands = []
    if isinstance(task.command, list):
        commands = [cmd for cmd in task.command if cmd.strip()]  # Filter empty commands
    elif isinstance(task.command, str):
        commands = [task.command.strip()] if task.command.strip() else []

    if not commands:
        logger.warning(f"[SSH] Task {task.alias} has no valid commands")
        return "ERROR: No valid commands"

    logger.info(
        f"[SSH] Starting task execution {task.alias} on {device.name} ({device.ip}) - Command count: {len(commands)}"
    )

    try:
        # Get SSH connection (from pool or create new)
        conn = await _get_ssh_connection(task, device)

        # Store all command execution results
        all_results = []

        # Execute each command sequentially
        for cmd_index, command in enumerate(commands, 1):
            logger.info(f"[SSH] Executing command {cmd_index}/{len(commands)}: {command}")

            # Execute single command (with retry mechanism)
            last_exception = None
            retry = conn_details.retry if conn_details else 3
            command_success = False

            for attempt in range(retry + 1):
                try:
                    timeout = conn_details.timeout if conn_details else 10
                    result = await asyncio.wait_for(conn.run(command, check=True), timeout=timeout)

                    if attempt > 0:
                        logger.info(f"[SSH] Command {cmd_index} executed successfully after {attempt + 1} attempts")

                    # Ensure returned is str type
                    stdout = result.stdout
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode("utf-8", errors="replace")

                    all_results.append(f"Command {cmd_index}: {command}\n{stdout or ''}")
                    command_success = True
                    break

                except TimeoutError:
                    timeout = conn_details.timeout if conn_details else 10
                    last_exception = Exception(f"Command execution timeout ({timeout} seconds)")
                    if attempt < retry:
                        wait_time = 2**attempt
                        logger.warning(
                            f"[SSH] Command {cmd_index} attempt {attempt + 1} timed out. Waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[SSH] Command {cmd_index} still timed out after {attempt + 1} attempts")

                except Exception as e:
                    last_exception = e
                    if attempt < retry:
                        wait_time = 2**attempt
                        logger.warning(
                            f"[SSH] Command {cmd_index} attempt {attempt + 1} failed: {e}. Waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[SSH] Command {cmd_index} still failed after {attempt + 1} attempts: {e}")

            # If current command execution failed, log error but continue executing next command
            if not command_success:
                error_msg = f"Command {cmd_index}: {command}\nERROR: {last_exception}"
                all_results.append(error_msg)
                logger.warning(f"[SSH] Command {cmd_index} execution failed, continuing to next command")

        # Combine all command results
        final_result = "\n\n".join(all_results)
        logger.success(
            f"[SSH] Successfully completed task {task.alias} on {device.name} - Executed {len(commands)} commands"
        )
        return final_result

    except Exception as e:
        error_msg = f"[SSH] Task {task.alias} on {device.name} execution failed: {e}"
        logger.error(error_msg)
        logger.error(f"[SSH] Detailed error information - Device IP: {device.ip}, Exception type: {type(e).__name__}")
        # Remove invalid connection from connection pool
        pool_key = (task.alias, device.name)
        _ssh_connection_pools.pop(pool_key, None)
        return f"ERROR: {e}"
    finally:
        # Periodically clean up timed out connections
        await _cleanup_ssh_connections()


async def _run_snmp_task(task: TaskConfig, device: DeviceConfig) -> str:
    """Execute single SNMP collection task."""
    conn_details = device.connection.snmp
    snmp_type = getattr(task, "type", "snmpget")  # Default to snmpget
    logger.info(
        f"[SNMP] Starting task execution {task.alias} on {device.name} ({device.ip}) - OID: {task.oid} - Type: {snmp_type}"
    )

    snmp_engine = SnmpEngine()
    try:
        # Ensure conn_details is not None
        port = conn_details.port if conn_details else 161
        timeout = conn_details.timeout if conn_details else 10
        retry = conn_details.retry if conn_details else 3
        community = conn_details.community if conn_details else "public"

        # Fix first error: correctly pass parameters to UdpTransportTarget
        transport_target = await UdpTransportTarget.create((device.ip, port), timeout=timeout, retries=retry)

        if snmp_type == "snmpwalk":
            # Execute SNMP Walk
            results = []
            async for error_indication, error_status, error_index, var_binds in walk_cmd(
                snmp_engine,
                CommunityData(community, mpModel=0),  # v1
                transport_target,
                ContextData(),
                ObjectType(ObjectIdentity(task.oid)),
                lexicographicMode=False,
                ignoreNonIncreasingOid=False,
            ):
                if error_indication:
                    raise RuntimeError(error_indication)
                elif error_status:
                    raise RuntimeError(
                        f"{error_status.prettyPrint()} at {(error_index and var_binds[int(error_index) - 1][0]) or '?'}"
                    )

                for var_bind in var_binds:
                    # Only get the value part, consistent with get_cmd
                    value_str = var_bind[1].prettyPrint()
                    results.append(value_str)

            result = "\n".join(results)
        else:
            # Execute SNMP Get (default behavior)
            error_indication, error_status, error_index, var_binds = await get_cmd(
                snmp_engine,
                CommunityData(community, mpModel=0),  # v1
                transport_target,
                ContextData(),
                ObjectType(ObjectIdentity(task.oid)),
            )

            if error_indication:
                raise RuntimeError(error_indication)
            elif error_status:
                raise RuntimeError(
                    f"{error_status.prettyPrint()} at {(error_index and var_binds[int(error_index) - 1][0]) or '?'}"
                )

            result = var_binds[0][1].prettyPrint()

        logger.success(f"[SNMP] Successfully completed task {task.alias} on {device.name}")
        return result

    except Exception as e:
        logger.error(f"[SNMP] Task {task.alias} on {device.name} execution failed: {e}")
        return f"ERROR: {e}"
    finally:
        # Fix second error: check if transportDispatcher is None
        if snmp_engine.transportDispatcher is not None:
            snmp_engine.transportDispatcher.closeDispatcher()


def _calculate_value(value: str, operation: str) -> float | None:
    """Perform mathematical operations.

    Args:
        value: Original numeric string
        operation: Operation expression, format like "+10", "*2", "/100", "-5"

    Returns:
        Calculated value, returns None if calculation fails
    """
    try:
        # Parse original value
        original_value = float(value)

        # Parse operator and operand
        if not operation or len(operation) < 2:
            return original_value

        operator = operation[0]
        operand_str = operation[1:]
        operand = float(operand_str)

        # Perform operation
        if operator == "+":
            return original_value + operand
        elif operator == "-":
            return original_value - operand
        elif operator == "*":
            return original_value * operand
        elif operator == "/":
            if operand == 0:
                logger.warning(f"Division by zero error: {value} / 0")
                return None
            return original_value / operand
        else:
            logger.warning(f"Unsupported operator: {operator}")
            return None

    except (ValueError, TypeError) as e:
        logger.warning(f"Numeric calculation failed: {value} {operation} - {e}")
        return None


def _parse_output(output: str, task: TaskConfig) -> dict[str, Any] | None:
    """Parse output results. Returns None to indicate that this result should not be stored."""
    # Check if output is an error
    if output.startswith("ERROR:"):
        logger.warning(f"Task {task.alias} execution error, not storing result: {output}")
        return None

    # If no labels, return original output directly
    if not task.labels:
        return {"raw_output": output}

    # If parse is None, means no regex matching needed, directly match results with labels
    if not task.parse or not task.parse.regex:
        # If only one label, use entire output as value for that label
        if len(task.labels) == 1:
            raw_value = output.strip()

            # Check if calculation is needed
            if task.parse and task.parse.calculate and len(task.parse.calculate) > 0:
                calculated_value = _calculate_value(raw_value, task.parse.calculate[0])
                if calculated_value is None:
                    logger.warning(f"Task {task.alias} calculation failed, not storing result")
                    return None
                return {task.labels[0]: str(calculated_value)}

            return {task.labels[0]: raw_value}

        # If multiple labels, try splitting output by lines
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
        result = {}

        # Match each line result with corresponding label
        for i, label in enumerate(task.labels):
            if i < len(lines):
                raw_value = lines[i]

                # Check if calculation is needed
                if task.parse and task.parse.calculate and i < len(task.parse.calculate) and task.parse.calculate[i]:
                    calculated_value = _calculate_value(raw_value, task.parse.calculate[i])
                    if calculated_value is None:
                        logger.warning(f"Task {task.alias} label {label} calculation failed, not storing result")
                        return None
                    result[label] = str(calculated_value)
                else:
                    result[label] = raw_value
            else:
                result[label] = ""  # Set to empty string if insufficient lines

        return result

    # Parse output using regular expression
    match = re.search(task.parse.regex, output)

    if not match:
        logger.warning(f"Task {task.alias} regex matched no content, not storing result.")
        return None  # Return None when match fails, indicating not to store

    groups = match.groups()

    if len(groups) != len(task.labels):
        logger.warning(f"Task {task.alias} regex capture group count does not match label count, not storing result.")
        return None  # Return None when match fails, indicating not to store

    result = {}
    for i, (label, value) in enumerate(zip(task.labels, groups, strict=False)):
        # Check if calculation is needed
        if task.parse.calculate and i < len(task.parse.calculate) and task.parse.calculate[i]:
            calculated_value = _calculate_value(value, task.parse.calculate[i])
            if calculated_value is None:
                logger.warning(f"Task {task.alias} label {label} calculation failed, not storing result")
                return None
            result[label] = str(calculated_value)
        else:
            result[label] = value

    return result


async def run_task(task: TaskConfig, device: DeviceConfig) -> dict[str, Any] | None:
    """
    Run specified task and return parsed results.

    Returns:
        A dictionary containing the raw output and parsed values, or None if task is disabled.
    """
    if not task.enabled:
        return None

    raw_output = ""
    if task.protocol == "ssh":
        raw_output = await _run_ssh_task(task, device)
    elif task.protocol == "snmp":
        raw_output = await _run_snmp_task(task, device)
    else:
        logger.error(f"Unsupported task protocol: {task.protocol}")
        return None

    # Also include raw output in results for file storage convenience
    parsed_results = _parse_output(raw_output, task)
    return parsed_results
