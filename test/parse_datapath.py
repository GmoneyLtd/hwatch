#!/usr/bin/env python3
"""
解析 datapath_session.txt 文件并提取关键指标:
1. Current Entries 值
2. Maximum Entries 值
3. Current Entries/Maximum Entries 比值
4. Default queue 行的 Empty Count 值
"""

import re
import sys
import os


def parse_datapath_session(file_path):
    """
    解析 datapath session 文件并提取所需信息
    
    Args:
        file_path (str): 文件路径
    
    Returns:
        dict: 包含提取信息的字典
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 使用一个复杂的正则表达式提取所有需要的数据
    # 这个正则表达式会匹配包含所有我们需要的信息的整个区域
    pattern = r'\|\s*G\s*\|\s*\[000\]\s*\|\s*Current Entries\s+(\d+)\s*\|[\s\S]*?\|\s*G\s*\|\s*\[002\]\s*\|\s*Maximum Entries\s+(\d+)\s*\|[\s\S]*?\|\s*0\s*\|\s*1\s*\|\s*Default queue\s*\|[^|]+\|[^|]+\|\s*(\d+)'
    
    match = re.search(pattern, content)
    
    if match:
        current_entries = int(match.group(1))
        max_entries = int(match.group(2))
        default_queue_empty_count = int(match.group(3))
        ratio = current_entries / max_entries
        
        return {
            'current_entries': current_entries,
            'max_entries': max_entries,
            'ratio': ratio,
            'default_queue_empty_count': default_queue_empty_count
        }
    else:
        # 如果复杂正则无法匹配，则使用单独的正则表达式
        
        
        return {
            'current_entries': 'N/A',
            'max_entries': 'N/A',
            'ratio': 'N/A',
            'default_queue_empty_count': 'N/A'
        }


def main():
    file_path = 'test/datapath_session.txt'
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    
    try:
        result = parse_datapath_session(file_path)
        
        print(f"Current Entries: {result['current_entries']}")
        print(f"Maximum Entries: {result['max_entries']}")
        print(f"Current/Maximum: {result['ratio']:.6f}")
        print(f"Default queue Empty Count: {result['default_queue_empty_count']}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()