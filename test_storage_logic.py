#!/usr/bin/env python3
"""测试新的存储逻辑"""

import asyncio
import os
import shutil
from datetime import datetime
from core.config_loader import load_config, TaskConfig, ParseConfig, ScheduleConfig, DeviceConfig, ConnectionConfig, ConnectionDetails
from core.collector import _parse_output, run_task

async def test_storage_logic():
    """测试存储逻辑"""
    
    # 清理测试目录
    if os.path.exists("outfile"):
        shutil.rmtree("outfile")
    
    print("=== 测试存储逻辑 ===")
    
    # 测试场景1: SSH成功，有parse，匹配成功 - 应该存储
    print("\n1. SSH成功，有parse，匹配成功 - 应该存储")
    task1 = TaskConfig(
        alias="test_ssh_parse_success",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        parse=ParseConfig(regex=r"CPU: (\d+)%"),
        labels=["cpu_usage"]
    )
    output1 = "CPU: 85%"
    result1 = _parse_output(output1, task1)
    print(f"输入: {output1}")
    print(f"结果: {result1}")
    print(f"是否存储: {'是' if result1 is not None else '否'}")
    
    # 测试场景2: SSH成功，有parse，匹配失败 - 不应该存储
    print("\n2. SSH成功，有parse，匹配失败 - 不应该存储")
    task2 = TaskConfig(
        alias="test_ssh_parse_fail",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        parse=ParseConfig(regex=r"CPU: (\d+)%"),
        labels=["cpu_usage"]
    )
    output2 = "Memory: 67%"  # 不匹配CPU模式
    result2 = _parse_output(output2, task2)
    print(f"输入: {output2}")
    print(f"结果: {result2}")
    print(f"是否存储: {'是' if result2 is not None else '否'}")
    
    # 测试场景3: SSH成功，无parse - 应该存储
    print("\n3. SSH成功，无parse - 应该存储")
    task3 = TaskConfig(
        alias="test_ssh_no_parse",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        labels=["output"]
    )
    output3 = "Some command output"
    result3 = _parse_output(output3, task3)
    print(f"输入: {output3}")
    print(f"结果: {result3}")
    print(f"是否存储: {'是' if result3 is not None else '否'}")
    
    # 测试场景4: SSH失败 - 不应该存储
    print("\n4. SSH失败 - 不应该存储")
    task4 = TaskConfig(
        alias="test_ssh_error",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        labels=["output"]
    )
    output4 = "ERROR: Connection failed"
    result4 = _parse_output(output4, task4)
    print(f"输入: {output4}")
    print(f"结果: {result4}")
    print(f"是否存储: {'是' if result4 is not None else '否'}")
    
    # 测试场景5: SNMP成功，有parse，匹配成功 - 应该存储
    print("\n5. SNMP成功，有parse，匹配成功 - 应该存储")
    task5 = TaskConfig(
        alias="test_snmp_parse_success",
        targets=["device1"],
        protocol="snmp",
        schedule=ScheduleConfig(),
        parse=ParseConfig(regex=r"Gauge32:\s*(\d+)"),
        labels=["session_count"]
    )
    output5 = "Gauge32: 1234"
    result5 = _parse_output(output5, task5)
    print(f"输入: {output5}")
    print(f"结果: {result5}")
    print(f"是否存储: {'是' if result5 is not None else '否'}")

if __name__ == "__main__":
    asyncio.run(test_storage_logic())