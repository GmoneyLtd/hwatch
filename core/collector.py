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

# SSH连接池字典, 键为 (task_alias, device_name) 元组, 值为连接对象和最后使用时间
_ssh_connection_pools: dict[tuple[str, str], dict[str, Any]] = {}


async def _get_ssh_connection(task: TaskConfig, device: DeviceConfig) -> asyncssh.SSHClientConnection:
    """从连接池获取SSH连接, 如果不存在或已断开则创建新连接"""
    pool_key = (task.alias, device.name)
    conn_details = device.connection.ssh

    # 检查连接池中是否已有连接
    if pool_key in _ssh_connection_pools:
        conn_entry = _ssh_connection_pools[pool_key]
        conn = conn_entry["connection"]

        # 检查连接是否仍然有效
        if conn._transport is not None and not conn._transport.at_eof():
            # 更新最后使用时间
            conn_entry["last_used"] = time.time()
            logger.debug(f"[SSH] 复用现有连接: {task.alias} on {device.name}")
            return conn
        else:
            # 连接已断开, 清理连接池条目
            del _ssh_connection_pools[pool_key]
            logger.debug(f"[SSH] 清理已断开连接: {task.alias} on {device.name}")

    # 创建新连接(带重试机制)
    logger.info(f"[SSH] 建立新连接: {task.alias} on {device.name}")

    last_exception = None
    # 确保conn_details不为None
    retry = conn_details.retry if conn_details else 3
    for attempt in range(retry + 1):  # retry+1 次尝试(1次初始尝试 + retry次重试)
        try:
            # 确保conn_details不为None
            port = conn_details.port if conn_details else 22
            username = conn_details.username if conn_details else None
            password = conn_details.password if conn_details else None
            timeout = conn_details.timeout if conn_details else 10

            conn = await asyncssh.connect(
                device.ip,
                port=port,
                username=username,
                password=password,
                known_hosts=None,  # 在生产中应考虑更安全的主机密钥验证
                connect_timeout=timeout,
            )

            # 将连接添加到连接池
            _ssh_connection_pools[pool_key] = {
                "connection": conn,
                "last_used": time.time(),
                "task": task.alias,
                "device": device.name,
            }

            if attempt > 0:
                logger.info(f"[SSH] 连接 {task.alias} on {device.name} 在第 {attempt + 1} 次尝试后成功建立")

            return conn

        except Exception as e:
            last_exception = e
            # 确保conn_details不为None
            retry = conn_details.retry if conn_details else 3
            if attempt < retry:
                wait_time = 2**attempt  # 指数退避
                logger.warning(
                    f"[SSH] 连接 {task.alias} on {device.name} 第 {attempt + 1} 次尝试失败: {e}. 等待 {wait_time} 秒后重试..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[SSH] 连接 {task.alias} on {device.name} 在 {attempt + 1} 次尝试后仍然失败")

    # 如果所有尝试都失败了, 抛出最后一个异常
    if last_exception:
        raise last_exception
    else:
        raise Exception("连接失败, 但没有具体的异常信息")


async def _cleanup_ssh_connections():
    """清理超时的SSH连接(超过10分钟未使用)"""
    current_time = time.time()
    expired_keys = []

    for pool_key, conn_entry in _ssh_connection_pools.items():
        if current_time - conn_entry["last_used"] > 600:  # 10分钟 = 600秒
            expired_keys.append(pool_key)

    for pool_key in expired_keys:
        conn_entry = _ssh_connection_pools[pool_key]
        conn = conn_entry["connection"]
        try:
            conn.close()
            await conn.wait_closed()
            logger.info(f"[SSH] 清理超时连接: {conn_entry['task']} on {conn_entry['device']}")
        except Exception as e:
            logger.warning(f"[SSH] 关闭超时连接时出错: {e}")
        finally:
            del _ssh_connection_pools[pool_key]


async def _run_ssh_task(task: TaskConfig, device: DeviceConfig) -> str:
    """执行单个SSH采集任务。"""
    conn_details = device.connection.ssh
    # 获取命令, 如果是列表则取第一个命令
    command = task.command[0] if isinstance(task.command, list) and task.command else ""
    logger.info(f"[SSH] 开始执行任务 {task.alias} on {device.name} ({device.ip}) - Command: {command}")
    try:
        # 获取SSH连接(从连接池或新建)
        conn = await _get_ssh_connection(task, device)

        # 执行命令(带重试机制)
        last_exception = None
        retry = conn_details.retry if conn_details else 3
        for attempt in range(retry + 1):
            try:
                # 获取命令, 如果是列表则取第一个命令
                command = task.command[0] if isinstance(task.command, list) and task.command else ""
                timeout = conn_details.timeout if conn_details else 10
                result = await asyncio.wait_for(conn.run(command, check=True), timeout=timeout)
                if attempt > 0:
                    logger.info(f"[SSH] 命令 {task.alias} on {device.name} 在第 {attempt + 1} 次尝试后成功执行")
                logger.success(f"[SSH] 成功完成任务 {task.alias} on {device.name}")
                # 确保返回的是 str 类型
                stdout = result.stdout
                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")
                return stdout or ""
            except TimeoutError:
                # 确保conn_details不为None
                timeout = conn_details.timeout if conn_details else 10
                retry = conn_details.retry if conn_details else 3

                last_exception = Exception(f"命令执行超时 ({timeout} 秒)")
                if attempt < retry:
                    wait_time = 2**attempt
                    logger.warning(
                        f"[SSH] 命令 {task.alias} on {device.name} 第 {attempt + 1} 次执行超时. 等待 {wait_time} 秒后重试..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[SSH] 命令 {task.alias} on {device.name} 在 {attempt + 1} 次尝试后仍然超时")
            except Exception as e:
                last_exception = e
                # 确保conn_details不为None
                retry = conn_details.retry if conn_details else 3
                if attempt < retry:
                    wait_time = 2**attempt
                    logger.warning(
                        f"[SSH] 命令 {task.alias} on {device.name} 第 {attempt + 1} 次执行失败: {e}. 等待 {wait_time} 秒后重试..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"[SSH] 命令 {task.alias} on {device.name} 在 {attempt + 1} 次尝试后仍然失败: {e}")

        # 如果所有尝试都失败了, 抛出最后一个异常
        if last_exception:
            raise last_exception
        else:
            raise Exception("命令执行失败, 但没有具体的异常信息")

    except Exception as e:
        logger.error(f"[SSH] 任务 {task.alias} on {device.name} 执行失败: {e}")
        # 从连接池中移除失效连接
        pool_key = (task.alias, device.name)
        _ssh_connection_pools.pop(pool_key, None)
        return f"ERROR: {e}"
    finally:
        # 定期清理超时连接
        await _cleanup_ssh_connections()


async def _run_snmp_task(task: TaskConfig, device: DeviceConfig) -> str:
    """执行单个SNMP采集任务。"""
    conn_details = device.connection.snmp
    snmp_type = getattr(task, "type", "snmpget")  # 默认为snmpget
    logger.info(
        f"[SNMP] 开始执行任务 {task.alias} on {device.name} ({device.ip}) - OID: {task.oid} - Type: {snmp_type}"
    )

    snmp_engine = SnmpEngine()
    try:
        # 确保conn_details不为None
        port = conn_details.port if conn_details else 161
        timeout = conn_details.timeout if conn_details else 10
        retry = conn_details.retry if conn_details else 3
        community = conn_details.community if conn_details else "public"

        # 修复第一个错误: 正确传递参数给UdpTransportTarget
        transport_target = await UdpTransportTarget.create((device.ip, port), timeout=timeout, retries=retry)

        if snmp_type == "snmpwalk":
            # 执行SNMP Walk
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
                    # 只获取数值部分, 与get_cmd保持一致
                    value_str = var_bind[1].prettyPrint()
                    results.append(value_str)

            result = "\n".join(results)
        else:
            # 执行SNMP Get (默认行为)
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

        logger.success(f"[SNMP] 成功完成任务 {task.alias} on {device.name}")
        return result

    except Exception as e:
        logger.error(f"[SNMP] 任务 {task.alias} on {device.name} 执行失败: {e}")
        return f"ERROR: {e}"
    finally:
        # 修复第二个错误: 检查transportDispatcher是否为None
        if snmp_engine.transportDispatcher is not None:
            snmp_engine.transportDispatcher.closeDispatcher()


def _parse_output(output: str, task: TaskConfig) -> dict[str, Any] | None:
    """解析输出结果。返回None表示不应该存储此结果。"""
    # 检查输出是否为错误
    if output.startswith("ERROR:"):
        logger.warning(f"任务 {task.alias} 执行出错, 不存储结果: {output}")
        return None

    # 如果没有标签, 直接返回原始输出
    if not task.labels:
        return {"raw_output": output}

    # 如果parse为None, 意味着不需要正则匹配, 直接将结果与labels匹配
    if not task.parse or not task.parse.regex:
        # 如果只有一个标签, 直接将整个输出作为该标签的值
        if len(task.labels) == 1:
            return {task.labels[0]: output.strip()}

        # 如果有多个标签, 尝试按行分割输出
        lines = [line.strip() for line in output.strip().split("\n") if line.strip()]
        result = {}

        # 将每行结果与对应的标签匹配
        for i, label in enumerate(task.labels):
            if i < len(lines):
                result[label] = lines[i]
            else:
                result[label] = ""  # 如果行数不够, 设为空字符串

        return result

    # 使用正则表达式解析输出
    match = re.search(task.parse.regex, output)
    print("-" * 50)
    print(output)
    print(task.parse.regex)
    print("-" * 50)
    if not match:
        logger.warning(f"任务 {task.alias} 的正则未匹配到任何内容, 不存储结果。")
        return None  # 匹配失败时返回None, 表示不存储

    groups = match.groups()

    if len(groups) != len(task.labels):
        logger.warning(f"任务 {task.alias} 的正则捕获组数量与标签数量不匹配, 不存储结果。")
        return None  # 匹配失败时返回None, 表示不存储

    return dict(zip(task.labels, groups, strict=False))


async def run_task(task: TaskConfig, device: DeviceConfig) -> dict[str, Any] | None:
    """
    运行指定任务并返回解析后的结果。

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
        logger.error(f"不支持的任务协议: {task.protocol}")
        return None

    # 将原始输出也加入结果, 便于文件存储
    parsed_results = _parse_output(raw_output, task)
    return parsed_results
