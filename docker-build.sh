#!/bin/bash

# Docker 构建脚本
set -e

echo "开始构建 hwatch Docker 镜像..."

# 构建镜像
docker build -t hwatch:latest .

echo "构建完成!"
echo ""
echo "使用方法:"
echo "1. 直接运行: docker run -p 8080:8080 -v \$(pwd)/config.yaml:/app/config.yaml:ro hwatch:latest"
echo "2. 使用 docker-compose: docker-compose up -d"
echo ""
echo "访问地址: http://localhost:8080"