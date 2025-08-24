import io
import time
from datetime import datetime
from string import Template
from typing import Any

from core.config_loader import DeviceConfig, TaskConfig


class StringTemplateCache:
    """字符串模板缓存, 减少重复的字符串格式化操作"""

    def __init__(self):
        self.templates = {
            "file_header": Template(
                "=================== $timestamp ===================\n"
                "Task: $task_alias\n"
                "Device: $device_name ($device_ip)\n"
                "Protocol: $protocol\n"
            ),
            "ssh_info": Template("Command: $commands\n"),
            "snmp_info": Template("OID: $oids\nType: $types\n"),
            "results_header": "Results:\n",
            "file_footer": Template("\n+------------------ $timestamp ------------------+\n\n\n"),
        }

        # 预编译的时间格式化函数
        self._time_format = "%Y-%m-%d %H:%M:%S.%f"

    def format_timestamp(self, dt: datetime) -> str:
        """高效的时间戳格式化"""
        return dt.strftime(self._time_format)[:-3]  # 去掉最后3位微秒

    def format_file_content(
        self, task: TaskConfig, device: DeviceConfig, results: dict[str, Any], start_time: datetime, end_time: datetime
    ) -> str:
        """高效构建文件内容"""
        # 使用StringIO减少字符串拼接开销
        buffer = io.StringIO()

        # 格式化时间戳
        start_time_str = self.format_timestamp(start_time)
        end_time_str = self.format_timestamp(end_time)

        # 构建文件头
        header = self.templates["file_header"].substitute(
            timestamp=start_time_str,
            task_alias=task.alias,
            device_name=device.name,
            device_ip=device.ip,
            protocol=task.protocol,
        )
        buffer.write(header)

        # 添加协议特定信息
        if task.protocol == "ssh" and task.ssh:
            ssh_info = self.templates["ssh_info"].substitute(commands=str(task.ssh.command))
            buffer.write(ssh_info)
        elif task.protocol == "snmp" and task.snmp:
            snmp_info = self.templates["snmp_info"].substitute(oids=str(task.snmp.oid), types=str(task.snmp.type))
            buffer.write(snmp_info)

        # 添加结果
        buffer.write(self.templates["results_header"])

        if "raw_output" in results:
            buffer.write(results["raw_output"])
        else:
            for key, value in results.items():
                buffer.write(f"{key}: {value}\n")

        # 添加文件尾
        footer = self.templates["file_footer"].substitute(timestamp=end_time_str)
        buffer.write(footer)

        return buffer.getvalue()


# 全局模板缓存实例
_template_cache: StringTemplateCache | None = None


def get_template_cache() -> StringTemplateCache:
    """获取全局模板缓存实例"""
    global _template_cache
    if _template_cache is None:
        _template_cache = StringTemplateCache()
    return _template_cache
