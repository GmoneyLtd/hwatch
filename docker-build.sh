#!/bin/bash

# Docker 构建脚本
set -e

echo "开始构建 hwatch Docker 镜像..."

# 构建镜像
docker buildx build --platform linux/amd64,linux/arm64 -t registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:0.1.0 -t registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:latest --load .

echo "构建完成!"
echo ""
