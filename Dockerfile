# 使用官方 Python 3.12 镜像作为基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY . .

# 安装 uv 包管理器
RUN pip install uv

# 使用 uv 安装依赖
RUN uv sync --frozen

# 创建必要的目录
RUN mkdir -p log outfile

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["uv", "run", "python", "app.py"]