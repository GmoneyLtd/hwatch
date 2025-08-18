#!/usr/bin/env python3
"""测试文件存储逻辑"""

import os
import shutil
from datetime import datetime
from core.config_loader import TaskConfig, ScheduleConfig, DeviceConfig, ConnectionConfig

def test_file_storage():
    """测试文件存储逻辑"""
    
    # 清理测试目录
    if os.path.exists("outfile"):
        shutil.rmtree("outfile")
    
    print("=== 测试文件存储逻辑 ===")
    
    # 创建测试任务和设备
    task = TaskConfig(
        alias="test_task",
        targets=["test_device"],
        protocol="ssh",
        schedule=ScheduleConfig(),
        storage="file"
    )
    
    device = DeviceConfig(
        name="test_device",
        ip="192.168.1.100",
        connection=ConnectionConfig()
    )
    
    # 模拟多次执行结果
    results = [
        {"raw_output": "First execution result"},
        {"cpu_usage": "85%", "memory_usage": "67%"},
        {"raw_output": "Third execution result"}
    ]
    
    # 模拟存储逻辑
    outfile_dir = "outfile"
    os.makedirs(outfile_dir, exist_ok=True)
    file_path = os.path.join(outfile_dir, f"{task.alias}_{device.name}.log")
    
    for i, result in enumerate(results, 1):
        print(f"\n第 {i} 次执行:")
        
        # 准备写入内容，包含时间戳和任务信息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content_lines = [
            f"=== {timestamp} ===",
            f"任务: {task.alias}",
            f"设备: {device.name} ({device.ip})",
            f"协议: {task.protocol}",
            "结果:"
        ]
        
        # 添加结果内容
        if "raw_output" in result:
            content_lines.append(result["raw_output"])
        else:
            # 如果有解析后的结果，也显示
            for key, value in result.items():
                content_lines.append(f"  {key}: {value}")
        
        content_lines.append("")  # 空行分隔
        
        # 追加写入文件
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(content_lines) + '\n')
        
        print(f"结果已追加到 {file_path}")
    
    # 显示最终文件内容
    print(f"\n=== 最终文件内容 ({file_path}) ===")
    with open(file_path, 'r', encoding='utf-8') as f:
        print(f.read())

if __name__ == "__main__":
    test_file_storage()