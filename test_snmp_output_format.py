#!/usr/bin/env python3
"""测试SNMP输出格式的脚本"""

import asyncio
from core.collector import _run_snmp_task
from core.config_loader import TaskConfig, DeviceConfig, ConnectionConfig, ConnectionDetails


async def test_snmp_output_format():
    """测试snmpget和snmpwalk的输出格式"""

    # 创建测试设备配置
    test_device = DeviceConfig(
        name="Fortinet_60",
        ip="192.168.2.1",
        connection=ConnectionConfig(snmp=ConnectionDetails(community="awatch", port=161, timeout=2, retry=0)),
    )

    # 测试snmpget类型的任务
    snmpget_task = TaskConfig(
        alias="test_snmpget",
        enabled=True,
        targets=["Fortinet_60"],
        protocol="snmp",
        type="snmpget",
        oid="1.3.6.1.4.1.12356.101.4.1.8.0",  # fgSysSesCount
        schedule={"frequency": 1},
        labels=["fgSysSesCount"],
    )

    # 测试snmpwalk类型的任务
    snmpwalk_task = TaskConfig(
        alias="test_snmpwalk",
        enabled=True,
        targets=["Fortinet_60"],
        protocol="snmp",
        type="snmpwalk",
        oid="1.3.6.1.4.1.12356.101.4.4.2.1.2",  # fgProcessorUsage
        schedule={"frequency": 1},
        labels=["fgProcessorUsage"],
    )

    print("=== SNMP输出格式测试 ===")

    # 测试snmpget输出
    print("\n--- snmpget输出格式 ---")
    get_result = await _run_snmp_task(snmpget_task, test_device)
    print(f"snmpget结果: '{get_result}'")
    print(f"snmpget结果类型: {type(get_result)}")
    print(f"snmpget是否包含OID: {'=' in get_result}")

    # 测试snmpwalk输出
    print("\n--- snmpwalk输出格式 ---")
    walk_result = await _run_snmp_task(snmpwalk_task, test_device)
    print(f"snmpwalk结果: '{walk_result}'")
    print(f"snmpwalk结果类型: {type(walk_result)}")
    print(f"snmpwalk是否包含OID: {'=' in walk_result}")

    # 分析walk结果的行数
    if walk_result and not walk_result.startswith("ERROR:"):
        walk_lines = walk_result.strip().split("\n")
        print(f"snmpwalk行数: {len(walk_lines)}")
        print("snmpwalk各行内容:")
        for i, line in enumerate(walk_lines, 1):
            print(f"  行{i}: '{line}'")


if __name__ == "__main__":
    asyncio.run(test_snmp_output_format())
