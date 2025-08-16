# 📡 Hwatch - 轻量级运维采集平台

一个轻量级的网络设备信息采集与监控平台，支持通过 SSH 和 SNMP 协议并发执行任务。平台基于统一的异步引擎，具备精细化的任务调度、配置热更新、数据持久化以及一个功能丰富的 Web 控制面板。

---

## 🎯 核心功能

- ✅ **精细化任务调度**: 每个任务均可独立配置执行策略，包括执行次数、调度模式(`interval`/`delay`)和间隔时间。
- ✅ **配置热更新**: 监控 `config.yaml` 文件变化，使用 `watchdog` 实现配置的动态加载，无需重启服务。
- ✅ **Web控制面板**: 
    - **任务仪表盘**: 实时查看所有任务状态，并可在线启用或禁用任何任务。
    - **在线配置编辑器**: 提供一个可读写的配置页面，允许在线修改 `config.yaml`，并在保存时自动进行 YAML 格式校验。
    - **数据可视化**: 将采集到的数据以图表形式展示，便于趋势分析。
    - **任务文件**: 特定任务输出文件，提供文件预览和下载功能。
- ✅ **数据持久化**: 使用 `SQLite` 数据库存储所有采集结果。
- ✅ **连接复用**: SSH 连接复用机制，减少连接建立开销，并发采用协程，提高数据处理效率。
- ✅ **高性能**: 基于 **单进程异步模型**，Web服务、任务调度器、SSH/SNMP采集任务全部运行在同一个 asyncio 事件循环中，确保了极高的并发性能和较低的资源开销。
- ✅ **灵活的数据解析**: 支持基于正则表达式的键值对和表格形式的数据解析。
- ✅ **多种数据存储方式**: 支持 `sqlite` (数据库)、`file` (文件) 和 `null` (不存储) 三种方式。

---

## 🧱 技术架构

| 模块           | 技术栈                               | 说明                     |
|----------------|--------------------------------------|--------------------------|
| Web 框架       | uvicorn + FastAPI                   | 统一的异步 Web 框架与应用入口 |
| 后台调度       | asyncio + apscheduler                | 异步并发任务执行         |
| 配置管理       | YAML + Watchdog                      | 支持热更新和在线编辑     |
| SSH 采集       | asyncssh                             | 异步 SSH 命令执行        |
| SNMP 采集      | PySNMP (asyncio support)             | 异步 SNMP OID 查询       |
| 数据存储       | aiosqlite                            | 异步本地数据库           |
| 日志           | loguru                               | 程序及任务运行日志           |

---

## 🚀 快速开始

### 环境准备

确保已安装 Python 3.7+ 和 `uv` 包管理工具。

创建虚拟环境并安装依赖：
```bash
uv sync --frozen --no-cache
```

### 启动服务

```bash
# 运行并设置日志级别
python app.py --level debug
```

### 访问平台

打开浏览器并访问 `http://localhost:8080`，默认登录凭据为：
- 用户名: `admin`
- 密码: `admin`

---

## ⚙️ 功能详解

### 任务调度逻辑

每个任务的执行方式由其 `schedule` 块定义，包含三个核心字段：

- `frequency` (执行次数):
    - `0`: 无限循环执行。
    - `1`: 仅执行一次。
    - `n`: 总共执行 `n` 次。

- `mode` (调度模式):
    - `interval`: **固定间隔模式**。任务会严格按照 `seconds` 定义的间隔时间触发，类似于 `cron`。适合需要精确、周期性采样的数据（如 SNMP 轮询）。
    - `delay`: **完成后延迟模式**。任务会在上一次执行 **完成** 后，等待 `seconds` 指定的时间，再开始下一次。适合执行时间不固定的耗时任务（如 SSH show 命令）。

- `seconds` (时间/秒):
    - 配合 `mode` 使用，定义间隔或延迟的秒数。
    - 当 `frequency: 1` 时，此字段被忽略。

### 数据存储方式

每个任务的 `storage` 字段可以设为以下三种值：
1.  **`sqlite`**: 将采集或解析后的结构化数据存入 SQLite 数据库，便于查询和分析。
2.  **`file`**: 将任务执行返回的原始文本输出保存到文件中。
3.  **`null`**: 执行任务，但不存储任何返回结果。适用于执行一些操作型命令（如 `clear counters`）。

---

## 🧾 示例配置 (`config.yaml`)

```yaml
# ===================================================================
# Devices: 定义所有需要连接的网络设备
# ===================================================================
devices:
  - name: Router_A
    ip: 192.168.1.100
    connection:
      ssh:
        username: admin
        password: admin123  # 安全警告: 见下文安全建议
        port: 22
        timeout: 10
        retry: 3
      snmp:
        community: public
        port: 161
        timeout: 10
        retry: 3

  - name: Fortinet_60
    ip: 192.168.2.1
    connection:
      snmp:
        community: awatch
        port: 161
        timeout: 2
        retry: 0

# ===================================================================
# Tasks: 定义所有要执行的监控任务
# ===================================================================
tasks:
  # 任务1: (SNMP - 无限次, 固定频率) 获取Fortinet的CPU使用率
  - alias: check_fortinet_cpu_usage
    enabled: true
    targets: [Fortinet_60]
    protocol: snmp
    type: snmpwalk
    oid: 1.3.6.1.4.1.12356.101.4.4.2.1.2
    schedule:
      frequency: 0       # 0 = 无限次执行
      mode: interval     # 按固定间隔触发
      seconds: 5         # 每5秒一次
    storage: file

  # 任务2: (SSH - 无限次, 完成后延迟) 运行耗时的show tech-support
  - alias: run_router_a_tech_support
    enabled: true
    targets: [Router_A]
    protocol: ssh
    command: show tech-support
    schedule:
      frequency: 0       # 0 = 无限次执行
      mode: delay        # 在任务完成后，等待指定秒数
      seconds: 120       # 完成后等待2分钟
    storage: file

  # 任务3: (SSH - 执行1次) 获取Router_A的版本号
  - alias: get_router_a_version
    enabled: false
    targets: [Router_A]
    protocol: ssh
    command: show version
    schedule:
      frequency: 1       # 1 = 仅执行一次
    storage: sqlite

  # 任务4: (SSH - 执行1次, 无需存储)
  - alias: clear_router_a_counters
    enabled: false
    targets: [Router_A]
    protocol: ssh
    command: clear counters
    schedule:
      frequency: 1       # 1 = 仅执行一次
    storage: null
```

---

## 🔐 安全建议

- **强烈建议使用 SSH 密钥**: 在 `config.yaml` 中使用明文密码存在极大的安全风险。未来的版本将支持通过 SSH 密钥进行认证，这是更安全的选择。在实现该功能前，请严格控制配置文件的访问权限。
- **凭证管理**: 对于生产环境，建议将密码等敏感凭证从配置文件中移除，通过环境变量或专门的密钥管理服务（如 Vault）进行加载。

---

## 🛠️ 设计与实现要点

本节为后续代码开发提供指导。

### 1. 配置解析
- 应用启动时，需要解析 `config.yaml`，构建两个核心对象：`devices` 字典 (以 `name` 为 key) 和 `tasks` 列表。
- 启动任务时，根据任务的 `targets` 列表，到 `devices` 字典中查找对应的连接信息。这种分离的结构使得连接信息可以被多个任务复用。

### 2. 调度器实现
- 调度器 (`scheduler.py`) 需要能够根据每个任务的 `schedule` 块来决定其调度方式。
- **对于 `mode: interval`**: 可以直接使用 `apscheduler` 的 `IntervalTrigger`。
- **对于 `mode: delay`**: `apscheduler` 没有内建的 "delay" trigger。需要手动实现：创建一个 job，该 job 执行完业务逻辑后，在自己的代码末尾，动态地创建下一个同样逻辑的 job，并设置其 `run_date` 为 `now() + delay_seconds`。
- **对于 `frequency`**: 每次任务执行时，需要有一个计数器。当执行次数达到 `frequency` (且 `frequency` 不为0) 时，不再创建下一次的 job。

### 3. 数据库操作
- 在单进程模型下，所有数据库写操作都在同一个事件循环中，避免了多进程的锁问题，`aiosqlite` 可以安全使用。
- 建议创建一个数据库管理模块 (`database.py`)，提供统一的、异步的 `save_result()` 方法，供所有采集任务调用。

### 4. 前端资源
- 当前前端资源 (JS/CSS) 通过 CDN 加载。为提高可靠性和支持内网部署，未来应将这些资源库下载到本地 `static` 目录中，并修改模板文件从本地加载。

---

## 📁 项目结构

```
hwatch/
├── app.py                  # 项目入口脚本
├── pyproject.toml          # 项目依赖配置
├── README.md               # 项目说明文档
├── config.yaml             # 应用配置文件
├── core/                   # 主包目录
│   ├── __init__.py         # 包初始化文件
│   ├── collector.py        # 异步数据采集模块 (SSH/SNMP)
│   ├── database.py         # 异步数据库操作模块
│   ├── scheduler.py        # 异步任务调度器
│   └── web_server.py       # 异步Web服务
│   └── config_loader.py    # 配置加载与解析模块
│   └── watch.py            # 配置监控模块
├── views/                  # Web视图目录
│   ├── static/             # 静态资源文件（CSS, JS）
│   └── templates/          # HTML 模板文件
├── log/                    # 日志目录
└── outfile/                # 输出文件目录
```