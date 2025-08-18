#!/usr/bin/env python3
"""测试新的解析逻辑"""

from core.config_loader import load_config, TaskConfig, ParseConfig, ScheduleConfig
from core.collector import _parse_output

def test_parse_logic():
    """测试不同场景下的解析逻辑"""
    
    # 测试场景1: parse为None，单个标签
    print("=== 测试场景1: parse为None，单个标签 ===")
    task1 = TaskConfig(
        alias="test1",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        labels=["cpu_usage"]
    )
    output1 = "85%"
    result1 = _parse_output(output1, task1)
    print(f"输入: {output1}")
    print(f"结果: {result1}")
    print()
    
    # 测试场景2: parse为None，多个标签
    print("=== 测试场景2: parse为None，多个标签 ===")
    task2 = TaskConfig(
        alias="test2",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        labels=["cpu_usage", "memory_usage", "disk_usage"]
    )
    output2 = "85%\n67%\n45%"
    result2 = _parse_output(output2, task2)
    print(f"输入: {output2}")
    print(f"结果: {result2}")
    print()
    
    # 测试场景3: 有parse和regex，单个标签
    print("=== 测试场景3: 有parse和regex，单个标签 ===")
    task3 = TaskConfig(
        alias="test3",
        targets=["device1"],
        protocol="snmp",
        schedule=ScheduleConfig(),
        parse=ParseConfig(regex=r"Gauge32:\s*(\d+)"),
        labels=["session_count"]
    )
    output3 = "Gauge32: 1234"
    result3 = _parse_output(output3, task3)
    print(f"输入: {output3}")
    print(f"结果: {result3}")
    print()
    
    # 测试场景4: 有parse和regex，多个标签
    print("=== 测试场景4: 有parse和regex，多个标签 ===")
    task4 = TaskConfig(
        alias="test4",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        parse=ParseConfig(regex=r"CPU: (\d+)%, Memory: (\d+)%"),
        labels=["cpu", "memory"]
    )
    output4 = "CPU: 85%, Memory: 67%"
    result4 = _parse_output(output4, task4)
    print(f"输入: {output4}")
    print(f"结果: {result4}")
    print()
    
    # 测试场景5: 没有标签
    print("=== 测试场景5: 没有标签 ===")
    task5 = TaskConfig(
        alias="test5",
        targets=["device1"],
        protocol="ssh",
        schedule=ScheduleConfig()
    )
    output5 = "Some raw output"
    result5 = _parse_output(output5, task5)
    print(f"输入: {output5}")
    print(f"结果: {result5}")
    print()

if __name__ == "__main__":
    test_parse_logic()