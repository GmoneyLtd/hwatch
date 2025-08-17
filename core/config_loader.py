
from typing import List, Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError
from loguru import logger

# --- 数据模型定义 ---

class ScheduleConfig(BaseModel):
    frequency: int = 1
    mode: Optional[str] = None
    seconds: Optional[int] = None

class ParseConfig(BaseModel):
    regex: str
    labels: List[str]

class TaskConfig(BaseModel):
    alias: str
    enabled: bool = True
    targets: List[str]
    protocol: str
    type: Optional[str] = None
    oid: Optional[str] = None
    command: Optional[str] = None
    schedule: ScheduleConfig
    parse: Optional[ParseConfig] = None
    storage: Optional[str] = 'sqlite'

class ConnectionDetails(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None # 注意：明文密码安全风险
    port: int
    timeout: int = 10
    retry: int = 3
    community: Optional[str] = None

class ConnectionConfig(BaseModel):
    ssh: Optional[ConnectionDetails] = None
    snmp: Optional[ConnectionDetails] = None

class DeviceConfig(BaseModel):
    name: str
    ip: str
    connection: ConnectionConfig

class AppConfig(BaseModel):
    devices: List[DeviceConfig]
    tasks: List[TaskConfig]

# --- 加载函数 ---

def load_config(config_path: str) -> Optional[AppConfig]:
    """
    从指定路径加载、验证并解析YAML配置文件。

    Args:
        config_path (str): 配置文件的路径。

    Returns:
        Optional[AppConfig]: 如果加载和验证成功，返回AppConfig对象，否则返回None。
    """
    logger.info(f"开始从 {config_path} 加载配置...")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            logger.error("配置文件为空或格式不正确。")
            return None

        config = AppConfig(**data)
        logger.success("配置加载并验证成功！")
        logger.debug(f"加载了 {len(config.devices)} 个设备和 {len(config.tasks)} 个任务。")
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

