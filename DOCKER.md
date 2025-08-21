# Docker 部署指南

本文档介绍如何使用 Docker 部署 hwatch 应用。

## 文件说明

- `Dockerfile`: Docker 镜像构建文件
- `.dockerignore`: Docker 构建时忽略的文件
- `docker-compose.yml`: Docker Compose 配置文件
- `docker-build.sh`: 构建脚本
- `DOCKER.md`: 本说明文档

## 快速开始

### 方法一: 使用 Docker Compose (推荐)

1. 确保配置文件存在:
```bash
cp config_init.yaml config.yaml
# 根据需要修改 config.yaml
```

2. 启动服务:
```bash
docker-compose up -d
```

3. 查看日志:
```bash
docker-compose logs -f
```

4. 停止服务:
```bash
docker-compose down
```

### 方法二: 直接使用 Docker

1. 构建镜像:
```bash
./docker-build.sh
```

2. 运行容器:
```bash
docker run -d \
  --name hwatch \
  -p 8080:8080 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/outfile:/app/outfile \
  -v $(pwd)/hwatch.db:/app/hwatch.db \
  -e LOG_LEVEL=INFO \
  hwatch:latest
```

## 配置说明

### 环境变量

- `LOG_LEVEL`: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `PYTHONPATH`: Python 路径 (默认: /app)
- `PYTHONUNBUFFERED`: 禁用 Python 输出缓冲 (默认: 1)

### 数据卷挂载

- `./config.yaml:/app/config.yaml:ro`: 配置文件 (只读)
- `./log:/app/log`: 日志目录
- `./outfile:/app/outfile`: 输出文件目录
- `./hwatch.db:/app/hwatch.db`: SQLite 数据库文件

### 端口映射

- `8080:8080`: Web 服务端口

## 常用命令

### 查看运行状态
```bash
docker-compose ps
```

### 查看实时日志
```bash
docker-compose logs -f hwatch
```

### 进入容器
```bash
docker-compose exec hwatch bash
```

### 重启服务
```bash
docker-compose restart
```

### 更新镜像
```bash
docker-compose down
./docker-build.sh
docker-compose up -d
```

## 故障排除

### 1. 端口被占用
如果 8080 端口被占用，修改 `docker-compose.yml` 中的端口映射:
```yaml
ports:
  - "8081:8080"  # 改为其他端口
```

### 2. 配置文件不存在
确保 `config.yaml` 文件存在:
```bash
ls -la config.yaml
```

### 3. 权限问题
确保挂载的目录有正确的权限:
```bash
chmod 755 log outfile
```

### 4. 查看详细错误
```bash
docker-compose logs hwatch
```

## 生产环境建议

1. 使用外部数据库 (PostgreSQL/MySQL) 替代 SQLite
2. 配置日志轮转和清理策略
3. 设置资源限制
4. 使用 Docker Swarm 或 Kubernetes 进行集群部署
5. 配置健康检查和监控

## 安全注意事项

1. 不要在镜像中包含敏感信息
2. 使用非 root 用户运行容器
3. 定期更新基础镜像
4. 限制容器网络访问
5. 使用 secrets 管理敏感配置