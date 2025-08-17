import asyncssh
import re
from pysnmp.hlapi.asyncio import (
    get_cmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
)
from loguru import logger
from typing import Dict, Any, Optional

from core.config_loader import TaskConfig, DeviceConfig

async def _run_ssh_task(task: TaskConfig, device: DeviceConfig) -> str:
    """执行单个SSH采集任务。"""
    conn_details = device.connection.ssh
    logger.info(f"[SSH] 开始执行任务 {task.alias} on {device.name} ({device.ip}) - Command: {task.command}")
    try:
        async with asyncssh.connect(
            device.ip,
            port=conn_details.port,
            username=conn_details.username,
            password=conn_details.password,
            known_hosts=None,  # 在生产中应考虑更安全的主机密钥验证
            connect_timeout=conn_details.timeout
        ) as conn:
            result = await conn.run(task.command, check=True)
            logger.success(f"[SSH] 成功完成任务 {task.alias} on {device.name}")
            return result.stdout
    except Exception as e:
        logger.error(f"[SSH] 任务 {task.alias} on {device.name} 执行失败: {e}")
        return f"ERROR: {e}"

async def _run_snmp_task(task: TaskConfig, device: DeviceConfig) -> str:
    """执行单个SNMP采集任务。"""
    conn_details = device.connection.snmp
    logger.info(f"[SNMP] 开始执行任务 {task.alias} on {device.name} ({device.ip}) - OID: {task.oid}")
    
    snmp_engine = SnmpEngine()
    try:
        # 修复第一个错误：正确传递参数给UdpTransportTarget
        transport_target = await UdpTransportTarget.create(
            (device.ip, conn_details.port), 
            timeout=conn_details.timeout, 
            retries=conn_details.retry
        )
        
        error_indication, error_status, error_index, var_binds = await get_cmd(
            snmp_engine,
            CommunityData(conn_details.community, mpModel=0), # v1
            transport_target,
            ContextData(),
            ObjectType(ObjectIdentity(task.oid))
        )

        if error_indication:
            raise RuntimeError(error_indication)
        elif error_status:
            raise RuntimeError(f'{error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or "?"}')
        
        result = var_binds[0][1].prettyPrint()
        logger.success(f"[SNMP] 成功完成任务 {task.alias} on {device.name}")
        return result

    except Exception as e:
        logger.error(f"[SNMP] 任务 {task.alias} on {device.name} 执行失败: {e}")
        return f"ERROR: {e}"
    finally:
        # 修复第二个错误：检查transportDispatcher是否为None
        if snmp_engine.transportDispatcher is not None:
            snmp_engine.transportDispatcher.closeDispatcher()


def _parse_output(output: str, task: TaskConfig) -> Dict[str, Any]:
    """使用正则表达式解析输出。"""
    if not task.parse or not task.parse.regex:
        return {"raw_output": output}

    match = re.search(task.parse.regex, output)
    if not match:
        logger.warning(f"任务 {task.alias} 的正则未匹配到任何内容。返回原始输出。")
        return {"raw_output": output}

    groups = match.groups()
    if len(groups) != len(task.parse.labels):
        logger.warning(f"任务 {task.alias} 的正则捕获组数量与标签数量不匹配。")
        return {"raw_output": output}

    return dict(zip(task.parse.labels, groups))


async def run_task(task: TaskConfig, device: DeviceConfig) -> Optional[Dict[str, Any]]:
    """
    运行指定任务并返回解析后的结果。

    Returns:
        A dictionary containing the raw output and parsed values, or None if task is disabled.
    """
    if not task.enabled:
        return None

    raw_output = ""
    if task.protocol == 'ssh':
        raw_output = await _run_ssh_task(task, device)
    elif task.protocol == 'snmp':
        raw_output = await _run_snmp_task(task, device)
    else:
        logger.error(f"不支持的任务协议: {task.protocol}")
        return None

    # 将原始输出也加入结果，便于文件存储
    parsed_results = _parse_output(raw_output, task)