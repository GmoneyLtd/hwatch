#!/usr/bin/env python3
"""测试SNMP类型支持的脚本"""

import asyncio
from core.config_loader import load_config, TaskConfig, DeviceConfig, ConnectionConfig, ConnectionDetails

async def test_snmp_types():
    """测试snmpget和snmpwalk类型"""
    
    # 创建测试设备配置
    test_device = DeviceConfig(
        name="test_device",
        ip="127.0.0.1",  # 使用本地地址进行测试
        connection=ConnectionConfig(
            snmp=ConnectionDetails(
                community="public",
                port=161,
                timeout=5,
                retry=1
            )
        )
    )
    
    # 测试snmpget类型的任务
    snmpget_task = TaskConfig(
        alias="test_snmpget",
        enabled=True,
        targets=["test_device"],
        protocol="snmp",
        type="snmpget",
        oid="1.3.6.1.2.1.1.1.0",  # sysDescr
        schedule={"frequency": 1},
        labels=["sysDescr"]
    )
    
    # 测试snmpwalk类型的任务
    snmpwalk_task = TaskConfig(
        alias="test_snmpwalk", 
        enabled=True,
        targets=["test_device"],
        protocol="snmp",
        type="snmpwalk",
        oid="1.3.6.1.2.1.1",  # system tree
        schedule={"frequency": 1},
        labels=["system_info"]
    )
    
    print("=== SNMP类型支持测试 ===")
    print(f"snmpget任务类型: {snmpget_task.type}")
    print(f"snmpwalk任务类型: {snmpwalk_task.type}")
    
    # 测试配置文件中的任务
    print("\n=== 配置文件中的SNMP任务 ===")
    config = load_config('config.yaml')
    if config:
        for task in config.tasks:
            if task.protocol == 'snmp':
                print(f"任务: {task.alias}")
                print(f"  类型: {task.type}")
                print(f"  OID: {task.oid}")
                print(f"  标签: {task.labels}")
                print()

if __name__ == "__main__":
    asyncio.run(test_snmp_types())