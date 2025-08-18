from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, ValidationError


# --- 数据模型定义 ---

class ScheduleConfig(BaseModel):
    frequency: int = 1
    mode: str | None = None
    seconds: int | None = None

class ParseConfig(BaseModel):
    regex: str
    labels: list[str]

class TaskConfig(BaseModel):
    alias: str
    enabled: bool = True
    targets: list[str]
    protocol: str
    type: str | None = None
    oid: str | None = None
    command: str | None = None
    schedule: ScheduleConfig
    parse: ParseConfig | None = None
    storage: str | None = 'sqlite'

class ConnectionDetails(BaseModel):
    username: str | None = None
    password: str | None = None # 注意: 明文密码安全风险
    port: int
    timeout: int = 10
    retry: int = 3
    community: str | None = None

class ConnectionConfig(BaseModel):
    ssh: ConnectionDetails | None = None
    snmp: ConnectionDetails | None = None

class DeviceConfig(BaseModel):
    name: str
    ip: str
    connection: ConnectionConfig

class AppConfig(BaseModel):
    devices: list[DeviceConfig]
    tasks: list[TaskConfig]

# --- 加载函数 ---

def load_config(config_path: str) -> AppConfig | None:
    """
    从指定路径加载、验证并解析YAML配置文件。

    Args:
        config_path (str): 配置文件的路径。

    Returns:
        Optional[AppConfig]: 如果加载和验证成功, 返回AppConfig对象, 否则返回None。
    """
    logger.info(f"开始从 {config_path} 加载配置...")
    try:
        with open(config_path, encoding='utf-8') as f:
            data: dict[str, Any] | None = yaml.safe_load(f)  # pyright: ignore[reportExplicitAny, reportAny]

        if not data:
            logger.error("配置文件为空或格式不正确。")
            return None

        config = AppConfig(**data)  # pyright: ignore[reportAny]
        logger.success("配置加载并验证成功!")
        logger.debug(f"加载了 {len(config.devices)} 个设备和 {len(config.tasks)} 个任务。")
        
        # 加载具体设备和任务的debug日志
        for device in config.devices:
            for task in config.tasks:
                logger.debug(f"Decice: {device.name} - Task: {task.alias}:\n{str(task)}")

        return config

    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"YAML配置文件格式错误: {e}")
        return None
    except ValidationError as e:
        logger.error(f"配置数据结构验证失败: {e}")
        return None
    except Exception as e:
        logger.error(f"加载配置时发生未知错误: {e}")
        return None


def save_config(config: AppConfig, config_path: str) -> bool:
    """
    将配置保存到YAML文件。

    Args:
        config (AppConfig): 要保存的配置对象。
        config_path (str): 配置文件的路径。

    Returns:
        bool: 保存成功返回True, 否则返回False。
    """
    logger.info(f"开始保存配置到 {config_path}...")
    try:
        # 将Pydantic模型转换为字典
        config_dict = config.model_dump()

        # 保存到YAML文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)

        logger.success("配置保存成功!")
        return True
    except Exception as e:
        logger.error(f"保存配置时发生错误: {e}")
        return False
