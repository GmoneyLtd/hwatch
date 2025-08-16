import yaml
import json

# 全局变量
config = None

def load_config():
    """从config.yaml文件加载配置到全局变量config中。"""
    global config
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # 使用更美观的方式打印配置信息
    print("配置文件内容:")
    print("=" * 50)
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print("=" * 50)

if __name__ == "__main__":
    load_config()