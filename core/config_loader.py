from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, ValidationError


# --- Data model definitions ---
class ScheduleConfig(BaseModel):
    frequency: int = 1
    mode: str | None = None
    seconds: int | None = None


class ParseConfig(BaseModel):
    regex: str
    calculate: list[str] | None = None


class TaskConfig(BaseModel):
    alias: str
    enabled: bool = True
    targets: list[str]
    protocol: str
    type: str | None = None
    oid: str | None = None
    command: list[str] | None = None
    schedule: ScheduleConfig
    parse: ParseConfig | None = None
    labels: list[str] | None = None
    storage: str | None = "sqlite"


class ConnectionDetails(BaseModel):
    username: str | None = None
    password: str | None = None  # Note: Plain text password security risk
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


# --- Loading functions ---
def load_config(config_path: str) -> AppConfig | None:
    """
    Load, validate and parse YAML configuration file from specified path.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        Optional[AppConfig]: Returns AppConfig object if loading and validation succeed, otherwise returns None.
    """
    logger.info(f"Starting to load configuration from {config_path}...")
    try:
        with open(config_path, encoding="utf-8") as f:
            data: dict[str, Any] | None = yaml.safe_load(f)

        if not data:
            logger.error("Configuration file is empty or format is incorrect.")
            return None

        config = AppConfig(**data)
        logger.success("Configuration loaded and validated successfully!")
        logger.debug(f"Loaded {len(config.devices)} devices and {len(config.tasks)} tasks.")

        # Load specific devices and tasks
        # print("-" * 50)
        # for device in config.devices:
        #     for task in config.tasks:
        #         print(f"Decice: {device.name} - Task: {task.alias}:\n{str(task)}")
        # print("-" * 50)

        return config

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"YAML configuration file format error: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Configuration data structure validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unknown error occurred while loading configuration: {e}")
        return None


def save_config(config: AppConfig, config_path: str) -> bool:
    """
    Save configuration to YAML file.

    Args:
        config (AppConfig): Configuration object to save.
        config_path (str): Path to the configuration file.

    Returns:
        bool: Returns True if save succeeds, otherwise returns False.
    """
    logger.info(f"Starting to save configuration to {config_path}...")
    try:
        # Convert Pydantic model to dictionary
        config_dict = config.model_dump()

        # Save to YAML file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)

        logger.success("Configuration saved successfully!")
        return True
    except Exception as e:
        logger.error(f"Error occurred while saving configuration: {e}")
        return False
