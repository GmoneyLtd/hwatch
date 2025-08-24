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
from core.connection_cache import get_connection_cache
from core.error_handler import error_handler

# from core.performance_monitor import performance_monitor

# SSH connection pool dictionary, key is (task_alias, device_name) tuple, value is connection object and last used time
_ssh_connection_pools: dict[tuple[str, str], dict[str, Any]] = {}

# SNMP engine pool dictionary, key is (device_ip, community) tuple, value is engine object and last used time
_snmp_engine_pools: dict[tuple[str, str], dict[str, Any]] = {}

# Regex compilation cache
_regex_cache: dict[str, re.Pattern] = {}

# Track last cleanup time to avoid frequent cleanup calls
_last_ssh_cleanup: float = 0
_last_snmp_cleanup: float = 0
CLEANUP_INTERVAL = 300  # Clean up every 5 minutes


async def _get_ssh_connection(task: TaskConfig, device: DeviceConfig) -> asyncssh.SSHClientConnection:
    """Get SSH connection from connection pool, create new connection if not exists or disconnected"""
    pool_key = (task.alias, device.name)
    conn_details = device.connection.ssh

    # Check if connection already exists in connection pool
    if pool_key in _ssh_connection_pools:
        conn_entry = _ssh_connection_pools[pool_key]
        conn = conn_entry["connection"]

        # Check if connection is still valid using cache
        connection_cache = get_connection_cache()

        async def check_connection_func(connection):
            # More comprehensive connection status check
            if (
                connection._transport is not None
                and not connection._transport.at_eof()
                and not connection._transport.is_closing()
            ):
                # Try sending a simple command to verify connection
                await asyncio.wait_for(connection.run("echo test", check=True), timeout=2)
                return True
            return False

        try:
            is_valid = await connection_cache.is_valid_cached(
                f"ssh_{pool_key[0]}_{pool_key[1]}", conn, check_connection_func
            )

            if is_valid:
                # Connection is valid, update last used time
                conn_entry["last_used"] = time.time()
                logger.debug(f"[SSH] Reusing existing connection: {task.alias} on {device.name}")
                return conn
            else:
                raise Exception("Connection validation failed")
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
    global _last_ssh_cleanup
    current_time = time.time()

    # Only clean up if enough time has passed since last cleanup
    if current_time - _last_ssh_cleanup < CLEANUP_INTERVAL:
        return

    _last_ssh_cleanup = current_time
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


def _get_snmp_engine(device: DeviceConfig) -> SnmpEngine:
    """Get SNMP engine from engine pool, create new engine if not exists or invalid"""
    conn_details = device.connection.snmp
    community = conn_details.community if conn_details else "public"
    pool_key = (device.ip, community)

    # Check if engine already exists in engine pool
    if pool_key in _snmp_engine_pools:
        engine_entry = _snmp_engine_pools[pool_key]
        engine = engine_entry["engine"]

        # Update last used time and return existing engine
        engine_entry["last_used"] = time.time()
        logger.debug(f"[SNMP] Reusing existing engine for {device.name} ({device.ip})")
        return engine

    # Create new SNMP engine
    logger.info(f"[SNMP] Creating new engine for {device.name} ({device.ip})")
    engine = SnmpEngine()

    # Add engine to pool
    _snmp_engine_pools[pool_key] = {
        "engine": engine,
        "last_used": time.time(),
        "device_ip": device.ip,
        "community": community,
        "device_name": device.name,
    }

    return engine


def _cleanup_snmp_engines():
    """Clean up timed out SNMP engines (unused for more than 5 minutes)"""
    global _last_snmp_cleanup
    current_time = time.time()

    # Only clean up if enough time has passed since last cleanup
    if current_time - _last_snmp_cleanup < CLEANUP_INTERVAL:
        return

    _last_snmp_cleanup = current_time
    expired_keys = []

    for pool_key, engine_entry in _snmp_engine_pools.items():
        if current_time - engine_entry["last_used"] > 300:  # 5 minutes = 300 seconds
            expired_keys.append(pool_key)

    for pool_key in expired_keys:
        engine_entry = _snmp_engine_pools[pool_key]
        engine = engine_entry["engine"]
        try:
            if engine.transportDispatcher is not None:
                engine.transportDispatcher.closeDispatcher()
            logger.info(
                f"[SNMP] Cleaning up timed out engine: {engine_entry['device_name']} ({engine_entry['device_ip']})"
            )
        except Exception as e:
            logger.warning(f"[SNMP] Error closing timed out engine: {e}")
        finally:
            del _snmp_engine_pools[pool_key]


async def _run_ssh_task(
    task: TaskConfig, device: DeviceConfig, command_timeout: int = 300, command_retry: int = 0
) -> str:
    """Execute single SSH collection task, supporting sequential execution of multiple commands.

    Args:
        task: Task configuration
        device: Device configuration
        command_timeout: Command execution timeout in seconds (default: 300 = 5 minutes)
        command_retry: Command retry count (default: 0 = no retry)
    """
    if not task.ssh:
        logger.error(f"[SSH] Task {task.alias} missing SSH configuration")
        return "ERROR: Missing SSH configuration"

    # Process command list from SSH configuration
    commands = [cmd for cmd in task.ssh.command if cmd.strip()]  # Filter empty commands

    if not commands:
        logger.warning(f"[SSH] Task {task.alias} has no valid commands")
        return "ERROR: No valid commands"

    logger.info(
        f"[SSH] Starting task execution {task.alias} on {device.name} ({device.ip}) - Command count: {len(commands)}, timeout: {command_timeout}s, retry: {command_retry}"
    )

    try:
        # Store all command execution results
        all_results = []
        conn = None  # Initialize connection as None
        successful_commands = 0  # Track successful commands

        # Execute each command sequentially
        for cmd_index, command in enumerate(commands, 1):
            logger.info(f"[SSH] Executing command {cmd_index}/{len(commands)}: {command}")

            # Execute single command (with retry mechanism)
            last_exception = None
            command_success = False

            for attempt in range(command_retry + 1):
                try:
                    # Check connection before each command
                    if not conn or conn._transport is None or conn._transport.is_closing():
                        conn = await _get_ssh_connection(task, device)

                    result = await asyncio.wait_for(conn.run(command, check=True), timeout=command_timeout)

                    if attempt > 0:
                        logger.info(f"[SSH] Command {cmd_index} executed successfully after {attempt + 1} attempts")

                    # Ensure returned is str type
                    stdout = result.stdout
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode("utf-8", errors="replace")

                    all_results.append(f"Command {cmd_index}: {command}\n{stdout or ''}")
                    command_success = True
                    successful_commands += 1
                    break

                except TimeoutError:
                    last_exception = Exception(f"Command execution timeout ({command_timeout} seconds)")
                    if attempt < command_retry:
                        wait_time = 2**attempt
                        logger.warning(
                            f"[SSH] Command {cmd_index} attempt {attempt + 1} timed out. Waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[SSH] Command {cmd_index} still timed out after {attempt + 1} attempts")

                except Exception as e:
                    last_exception = e
                    # More precise connection-related error detection
                    is_connection_error = (
                        isinstance(e, asyncssh.ConnectionLost | asyncssh.DisconnectError)
                        or "connection" in str(e).lower()
                        or "transport" in str(e).lower()
                        or "network" in str(e).lower()
                        or "broken pipe" in str(e).lower()
                    )

                    if is_connection_error:
                        conn = None
                        # Immediately remove invalid connection from pool
                        pool_key = (task.alias, device.name)
                        if pool_key in _ssh_connection_pools:
                            try:
                                invalid_conn = _ssh_connection_pools[pool_key]["connection"]
                                invalid_conn.close()
                                await invalid_conn.wait_closed()
                            except Exception:
                                pass  # Ignore errors during closing
                            del _ssh_connection_pools[pool_key]
                            logger.debug(
                                f"[SSH] Removed invalid connection from pool: {task.alias} on {device.name} - Error: {type(e).__name__}: {e}"
                            )
                    else:
                        logger.debug(f"[SSH] Command error (connection reusable): {type(e).__name__}: {e}")

                    if attempt < command_retry:
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

        # Log completion with appropriate level based on success count
        if successful_commands == len(commands):
            logger.success(
                f"[SSH] Successfully completed task {task.alias} on {device.name} - {successful_commands}/{len(commands)} commands successful"
            )
        elif successful_commands > 0:
            logger.warning(
                f"[SSH] Partially completed task {task.alias} on {device.name} - {successful_commands}/{len(commands)} commands successful"
            )
        else:
            logger.error(
                f"[SSH] Failed to complete task {task.alias} on {device.name} - 0/{len(commands)} commands successful"
            )

        return final_result

    except asyncio.CancelledError:
        # Handle graceful shutdown - don't log as error since it's expected
        logger.debug(f"[SSH] Task {task.alias} on {device.name} was cancelled during shutdown")
        return "CANCELLED: Task cancelled during shutdown"
    except Exception as e:
        error_msg = f"[SSH] Task {task.alias} on {device.name} execution failed: {e}"
        logger.error(error_msg)
        logger.error(f"[SSH] Detailed error information - Device IP: {device.ip}, Exception type: {type(e).__name__}")
        # Remove invalid connection from connection pool
        pool_key = (task.alias, device.name)
        _ssh_connection_pools.pop(pool_key, None)
        return f"ERROR: {e}"
    finally:
        # Only clean up periodically to reduce CPU overhead
        await _cleanup_ssh_connections()


async def _run_snmp_task(task: TaskConfig, device: DeviceConfig) -> str:
    """Execute single SNMP collection task, supporting mixed operation types per OID."""
    conn_details = device.connection.snmp

    if not task.snmp:
        logger.error(f"[SNMP] Task {task.alias} missing SNMP configuration")
        return "ERROR: Missing SNMP configuration"

    # Get OIDs and their corresponding types from SNMP configuration
    oids = [oid for oid in task.snmp.oid if oid.strip()]  # Filter empty OIDs
    snmp_types = task.snmp.type

    if not oids:
        logger.warning(f"[SNMP] Task {task.alias} has no valid OIDs")
        return "ERROR: No valid OIDs"

    logger.info(
        f"[SNMP] Starting task execution {task.alias} on {device.name} ({device.ip}) - OID count: {len(oids)} with mixed types: {snmp_types}"
    )

    try:
        # Get SNMP engine from pool (reuse existing or create new)
        snmp_engine = _get_snmp_engine(device)

        # Ensure conn_details is not None
        port = conn_details.port if conn_details else 161
        timeout = conn_details.timeout if conn_details else 10
        retry = conn_details.retry if conn_details else 3
        community = conn_details.community if conn_details else "public"

        # Fix first error: correctly pass parameters to UdpTransportTarget
        transport_target = await UdpTransportTarget.create((device.ip, port), timeout=timeout, retries=retry)

        # Store all OID execution results
        all_results = []
        successful_oids = 0  # Track successful OIDs

        # Execute each OID with its specific type
        for oid_index, (oid, snmp_type) in enumerate(zip(oids, snmp_types, strict=True), 1):
            logger.info(f"[SNMP] Processing OID {oid_index}/{len(oids)}: {oid} (type: {snmp_type})")

            # Execute single OID with its specific type (with retry mechanism)
            last_exception = None
            oid_success = False

            for attempt in range(retry + 1):
                try:
                    if snmp_type == "snmpwalk":
                        # Execute SNMP Walk
                        results = []
                        async for error_indication, error_status, error_index, var_binds in walk_cmd(
                            snmp_engine,
                            CommunityData(community, mpModel=0),  # v1
                            transport_target,
                            ContextData(),
                            ObjectType(ObjectIdentity(oid)),
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
                            ObjectType(ObjectIdentity(oid)),
                        )

                        if error_indication:
                            raise RuntimeError(error_indication)
                        elif error_status:
                            raise RuntimeError(
                                f"{error_status.prettyPrint()} at {(error_index and var_binds[int(error_index) - 1][0]) or '?'}"
                            )

                        result = var_binds[0][1].prettyPrint()

                    if attempt > 0:
                        logger.info(f"[SNMP] OID {oid_index} processed successfully after {attempt + 1} attempts")

                    all_results.append(f"OID {oid_index}: {oid} ({snmp_type})\n{result or ''}")
                    oid_success = True
                    successful_oids += 1
                    break

                except Exception as e:
                    last_exception = e
                    if attempt < retry:
                        wait_time = 2**attempt  # Exponential backoff
                        logger.warning(
                            f"[SNMP] OID {oid_index} attempt {attempt + 1} failed: {e}. Waiting {wait_time} seconds before retry..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"[SNMP] OID {oid_index} still failed after {attempt + 1} attempts: {e}")

            # If current OID execution failed, log error but continue executing next OID
            if not oid_success:
                error_msg = f"OID {oid_index}: {oid} ({snmp_type})\nERROR: {last_exception}"
                all_results.append(error_msg)
                logger.warning(f"[SNMP] OID {oid_index} execution failed, continuing to next OID")

        # Combine all OID results
        final_result = "\n\n".join(all_results)

        # Log completion with appropriate level based on success count
        if successful_oids == len(oids):
            logger.success(
                f"[SNMP] Successfully completed task {task.alias} on {device.name} - {successful_oids}/{len(oids)} OIDs successful"
            )
        elif successful_oids > 0:
            logger.warning(
                f"[SNMP] Partially completed task {task.alias} on {device.name} - {successful_oids}/{len(oids)} OIDs successful"
            )
        else:
            logger.error(
                f"[SNMP] Failed to complete task {task.alias} on {device.name} - 0/{len(oids)} OIDs successful"
            )

        return final_result

    except asyncio.CancelledError:
        # Handle graceful shutdown - don't log as error since it's expected
        logger.debug(f"[SNMP] Task {task.alias} on {device.name} was cancelled during shutdown")
        return "CANCELLED: Task cancelled during shutdown"
    except Exception as e:
        logger.error(f"[SNMP] Task {task.alias} on {device.name} execution failed: {e}")
        return f"ERROR: {e}"
    finally:
        # Only clean up periodically to reduce CPU overhead
        _cleanup_snmp_engines()


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
        result = None
        if operator == "+":
            result = original_value + operand
        elif operator == "-":
            result = original_value - operand
        elif operator == "*":
            result = original_value * operand
        elif operator == "/":
            if operand == 0:
                logger.warning(f"Division by zero error: {value} / 0")
                return None
            result = original_value / operand
        else:
            logger.warning(f"Unsupported operator: {operator}")
            return None

        # Round result to 3 decimal places
        return round(result, 3) if result is not None else None

    except (ValueError, TypeError) as e:
        logger.warning(f"Numeric calculation failed: {value} {operation} - {e}")
        return None


def _get_compiled_regex(pattern: str) -> re.Pattern:
    """Get compiled regex from cache or compile and cache it"""
    if pattern not in _regex_cache:
        try:
            _regex_cache[pattern] = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern} - {e}")
            raise
    return _regex_cache[pattern]


def _parse_output(output: str, task: TaskConfig) -> dict[str, Any] | None:
    """Parse output results with support for dynamic label generation. Returns None to indicate that this result should not be stored."""
    # Check if output is an error or cancellation
    if output.startswith("ERROR:"):
        logger.warning(f"Task {task.alias} execution error, not storing result: {output}")
        return None
    elif output.startswith("CANCELLED:"):
        logger.debug(f"Task {task.alias} was cancelled, not storing result: {output}")
        return None

    # Check if output contains only error messages (for multi-OID SNMP tasks)
    if "OID " in output and "ERROR:" in output:
        # Split by sections and check if all sections contain errors
        sections = [section.strip() for section in output.split("\n\n") if section.strip()]
        error_sections = 0
        total_sections = 0

        for section in sections:
            if "OID " in section:
                total_sections += 1
                if "ERROR:" in section:
                    error_sections += 1

        # If all OID sections contain errors, don't store the result
        if total_sections > 0 and error_sections == total_sections:
            logger.warning(f"Task {task.alias} all OIDs failed, not storing result")
            return None

    # If no labels, return original output directly
    if not task.labels:
        return {"raw_output": output}

    # Get parse configuration from appropriate task type
    parse_config = None
    if task.protocol == "ssh" and task.ssh:
        parse_config = task.ssh.parse
    elif task.protocol == "snmp" and task.snmp:
        parse_config = task.snmp.parse

    # If parse is None, means no regex matching needed, directly match results with labels
    if not parse_config or not parse_config.regex:
        # For multi-command (SSH) or multi-OID (SNMP) tasks, extract individual results
        if "Command " in output or "OID " in output:
            # Extract values from formatted output (Command X: ... or OID X: ...)
            lines = output.split("\n\n")  # Split by double newlines (separator between commands/OIDs)
            extracted_values = []

            for section in lines:
                if section.strip():
                    # Split each section by lines and get the content after the first line (which contains Command/OID info)
                    section_lines = section.strip().split("\n")
                    if len(section_lines) > 1:
                        # Join all lines except the first one (header line)
                        content = "\n".join(section_lines[1:]).strip()

                        # For SNMP tasks, check if this OID uses snmpwalk and generate dynamic labels
                        if (
                            "OID " in section
                            and task.protocol == "snmp"
                            and task.snmp
                            and "snmpwalk" in section_lines[0]
                        ):  # Check if header contains snmpwalk
                            # Split content by lines - each line is a separate value from snmpwalk
                            walk_values = [line.strip() for line in content.split("\n") if line.strip()]
                            extracted_values.extend(walk_values)  # Add all values from this OID
                        else:
                            extracted_values.append(content)
                    else:
                        extracted_values.append("")  # Empty if no content

            # Generate labels based on actual SNMP results structure
            result = _generate_labels_from_snmp_results(task, lines, parse_config)

            return result

        else:
            # Single value output - original logic for backward compatibility
            # If only one label, use entire output as value for that label
            if len(task.labels) == 1:
                raw_value = output.strip()

                # Check if calculation is needed
                if parse_config and parse_config.calculate and len(parse_config.calculate) > 0:
                    calculated_value = _calculate_value(raw_value, parse_config.calculate[0])
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
                    if (
                        parse_config
                        and parse_config.calculate
                        and i < len(parse_config.calculate)
                        and parse_config.calculate[i]
                    ):
                        calculated_value = _calculate_value(raw_value, parse_config.calculate[i])
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
    compiled_regex = _get_compiled_regex(parse_config.regex)
    match = compiled_regex.search(output)

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
        if parse_config.calculate and i < len(parse_config.calculate) and parse_config.calculate[i]:
            calculated_value = _calculate_value(value, parse_config.calculate[i])
            if calculated_value is None:
                logger.warning(f"Task {task.alias} label {label} calculation failed, not storing result")
                return None
            result[label] = str(calculated_value)
        else:
            result[label] = value

    return result


def _generate_labels_from_snmp_results(task: TaskConfig, result_sections: list[str], parse_config) -> dict[str, Any]:
    """Generate labels based on actual SNMP results, processing each OID section individually."""
    result = {}
    base_labels = task.labels or []

    if not task.snmp:
        logger.warning(f"Task {task.alias} missing SNMP configuration")
        return {"raw_output": "\n\n".join(result_sections)}

    oid_index = 0
    valid_results_count = 0

    for section in result_sections:
        if not section.strip():
            continue

        section_lines = section.strip().split("\n")
        if len(section_lines) < 1:
            continue

        # Extract header info and content
        header_line = section_lines[0]
        content = "\n".join(section_lines[1:]).strip() if len(section_lines) > 1 else ""

        # Skip if this is not an OID section
        if "OID " not in header_line:
            continue

        # Skip if this OID section contains an error
        if "ERROR:" in content:
            logger.debug(f"Task {task.alias} OID {oid_index + 1} contains error, skipping: {content}")
            oid_index += 1
            continue

        # Determine SNMP operation type from header
        is_snmpwalk = "snmpwalk" in header_line

        # Get base label for this OID
        if oid_index < len(base_labels):
            base_label = base_labels[oid_index]
        else:
            base_label = f"oid_{oid_index + 1}"

        if is_snmpwalk:
            # Split walk results by lines - each line is a separate value
            walk_values = [line.strip() for line in content.split("\n") if line.strip()]

            # Generate labels with suffixes for each walk result
            for i, value in enumerate(walk_values, 1):
                label = f"{base_label}.{i}"

                # Apply calculation if configured
                if (
                    parse_config
                    and parse_config.calculate
                    and oid_index < len(parse_config.calculate)
                    and parse_config.calculate[oid_index]
                ):
                    calculated_value = _calculate_value(value, parse_config.calculate[oid_index])
                    if calculated_value is None:
                        logger.warning(f"Task {task.alias} label {label} calculation failed, not storing result")
                        return {}
                    result[label] = str(calculated_value)
                else:
                    result[label] = value

            if walk_values:  # Only count if there were actual values
                valid_results_count += 1
        else:
            # Single value from snmpget
            if content:  # Only process if there's actual content
                # Apply calculation if configured
                if (
                    parse_config
                    and parse_config.calculate
                    and oid_index < len(parse_config.calculate)
                    and parse_config.calculate[oid_index]
                ):
                    calculated_value = _calculate_value(content, parse_config.calculate[oid_index])
                    if calculated_value is None:
                        logger.warning(f"Task {task.alias} label {base_label} calculation failed, not storing result")
                        return {}
                    result[base_label] = str(calculated_value)
                else:
                    result[base_label] = content

                valid_results_count += 1

        oid_index += 1

    # Return empty dict if no valid results were found
    if valid_results_count == 0:
        logger.warning(f"Task {task.alias} no valid OID results found, not storing data")
        return {}

    return result


async def run_task(
    task: TaskConfig, device: DeviceConfig, command_timeout: int = 300, command_retry: int = 0
) -> dict[str, Any] | None:
    """
    Run specified task and return parsed results.

    Args:
        task: Task configuration
        device: Device configuration
        command_timeout: Command execution timeout in seconds (default: 300 = 5 minutes)
        command_retry: Command retry count (default: 0 = no retry)

    Returns:
        A dictionary containing the raw output and parsed values, or None if task is disabled.
    """
    if not task.enabled:
        return None

    raw_output = ""
    if task.protocol == "ssh":
        raw_output = await _run_ssh_task(task, device, command_timeout, command_retry)
    elif task.protocol == "snmp":
        raw_output = await _run_snmp_task(task, device)
    else:
        logger.error(f"Unsupported task protocol: {task.protocol}")
        return None

    # Also include raw output in results for file storage convenience
    parsed_results = _parse_output(raw_output, task)
    return parsed_results


async def cleanup_all_connections():
    """Cleanup all SSH connections and SNMP engines for graceful shutdown"""
    logger.info("Starting cleanup of all connections...")

    # Cleanup SSH connections
    ssh_cleanup_count = 0
    for pool_key, conn_entry in list(_ssh_connection_pools.items()):
        conn = conn_entry["connection"]
        try:
            conn.close()
            await conn.wait_closed()
            ssh_cleanup_count += 1
            logger.debug(f"Closed SSH connection: {conn_entry['task']} on {conn_entry['device']}")
        except Exception as e:
            logger.warning(f"Error closing SSH connection: {e}")
        finally:
            del _ssh_connection_pools[pool_key]

    # Cleanup SNMP engines
    snmp_cleanup_count = 0
    for pool_key, engine_entry in list(_snmp_engine_pools.items()):
        engine = engine_entry["engine"]
        try:
            if engine.transportDispatcher is not None:
                engine.transportDispatcher.closeDispatcher()
            snmp_cleanup_count += 1
            logger.debug(f"Closed SNMP engine: {engine_entry['device_name']} ({engine_entry['device_ip']})")
        except Exception as e:
            logger.warning(f"Error closing SNMP engine: {e}")
        finally:
            del _snmp_engine_pools[pool_key]

    logger.info(
        f"Connection cleanup completed. Closed {ssh_cleanup_count} SSH connections and {snmp_cleanup_count} SNMP engines"
    )
