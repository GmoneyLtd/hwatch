# 📡 Hwatch - 轻量级运维采集平台

一个轻量级的网络设备信息采集与监控平台，支持通过 SSH 和 SNMP 协议并发执行任务。平台具备精细化的任务调度、配置热更新、数据持久化以及一个功能丰富的 Web 控制面板。

---

## 🎯 核心功能

- ✅ **精细化任务调度**: 每个任务均可独立配置执行策略，包括执行次数和间隔时间。
- ✅ **配置热更新**: 监控 `config.yaml` 文件变化，使用 `watchdog` 实现配置的动态加载，无需重启服务。
- ✅ **Web控制面板**: 
    - **任务仪表盘**: 实时查看所有任务状态，并可在线启用或禁用任何任务。
    - **在线配置编辑器**: 提供一个可读写的配置页面，允许在线修改 `config.yaml`，并在保存时自动进行 YAML 格式校验。
    - **数据可视化**: 将采集到的数据以图表形式展示，便于趋势分析。
    - **任务文件**: 特定任务输出文件，提供文件预览和下载功能。
- ✅ **数据持久化**: 使用 `SQLite` 数据库存储所有采集结果。
- ✅ **连接复用**: SSH 连接复用机制，减少连接建立开销，并发采用协程，提高数据处理效率，SNMP模块采用协程并发，提高数据处理效率， snmp采用v2基于udp通行无需考虑连接复用。
- ✅ **性能**: ssh，snmp及web采用独立的进程运行，提高程序效率
- ✅ **灵活的数据解析**: 支持键值对和表格形式的数据解析。
- ✅ **多种数据存储方式**: 支持 SQLite 数据库存储和文件存储。

---

## 🧱 异步实现技术架构

| 模块           | 技术栈                               | 说明                     |
|----------------|--------------------------------------|--------------------------|
| Web 框架       | uvicorn + FastAPI                   | 异步 Web 框架            |
| 后台调度       | asyncio + apscheduler                | 异步并发任务执行         |
| 配置管理       | YAML + Watchdog                      | 支持热更新和在线编辑     |
| SSH 采集       | asyncssh                             | 异步 SSH 命令执行        |
| SNMP 采集      | PySNMP (asyncio support)             | 异步 SNMP OID 查询       |
| 数据存储       | aiosqlite                            | 异步本地数据库           |
| 日志       | loguru                            | 程序及任务运行日志           |

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

每个任务都遵循下表的调度规则：

| `frequency` | `interval` | 含义                                 |
|-------------|------------|--------------------------------------|
| 0           | 0          | 启动后仅执行一次。                   |
| 0           | >0         | 无限循环执行，每次间隔 `interval` 秒, 第一次执行完等待 `interval` 秒后开始执行。 |
| >0          | >0         | 总共执行 `frequency` 次，每次间隔 `interval` 秒, 第一次执行完等待 `interval` 秒后开始执行第二次执行直到完成`frequency`次。 |
| >0          | 0          | 立即连续执行 `frequency` 次（无间隔）。 |

### Web 控制变量

每个任务都支持 `enabled: true/false` 变量来控制其运行状态。你可以通过 Web 控制面板的"启用/禁用"按钮轻松切换，更改会即时生效。

### 数据解析功能

基于文本的正则匹配

### 数据存储方式

支持两种数据存储方式：
1. **SQLite 数据库** (`storage: sqlite`)：结构化存储，便于查询和分析
2. **文件存储** (`storage: file`)：将原始输出保存到文件中

---

## 🧾 示例配置 (`config.yaml`)


---

## 📁 项目结构

```
hwatch/
├── app.py                  # 项目入口脚本
├── pyproject.toml          # 项目依赖配置
├── README.md               # 项目说明文档
├── core/                   # 主包目录
│   ├── __init__.py         # 包初始化文件
│   ├── async_mode/         # 异步版本模块
│   │   ├── __init__.py
│   │   ├── hwatch.py    # 模块入口文件
│   │   ├── collector.py # 异步数据采集模块
│   │   ├── database.py  # 异步数据库操作模块
│   │   ├── scheduler.py # 异步任务调度器
│   │   └── web_server.py # 异步Web服务
│   ├── utils/              # 工具模块
│       ├── __init__.py
│       ├── watch.py        # 配置监控模块
│       └── ulog.py         # 日志统一模块
├── test/                   # 测试文件目录 
├── views/                  # Web视图目录
│   ├── static/             # 静态资源文件（CSS, JS）
│   └── templates/          # HTML 模板文件
├── log/                    # 日志目录
└── outfile/                 # 输出文件目录, 对应配置文件中的storage: file
```

---


## 🔄 异步实现详解



### 特点：
- 高并发性能，适合大规模监控场景
- 异步IO模型，资源占用更少
- 更好的可扩展性，支持大量设备并发采集
- 更复杂的编程模型，调试相对困难

---



### 实现细节

异步版本使用了以下技术：

1. **asyncssh**：异步 SSHv2 协议库，基于 Python asyncio 框架
2. **pysnmp asyncio**：PySNMP 库的异步支持
3. **aiosqlite**：异步 SQLite 数据库操作库
4. **asyncio.gather**：并发执行多个采集任务
5. **连接池**：复用异步连接以减少开销
6. **信号量**：控制并发任务数量，防止资源耗尽
7. **上下文管理器**：确保资源正确释放

### 优势

- 更少的线程开销
- 更高的并发能力
- 更低的内存占用
- 更好的可扩展性
- 精细的资源控制和监控
- 优化的日志记录和处理

---

## 🛠️ 开发与维护

### 添加新功能

1. 修改 [config.yaml](file:///Users/nice/Jinlin/PythonCase/hwatch/config.yaml) 文件添加新的设备或任务
2. 通过 Web 界面的配置编辑器进行在线修改

### 查看日志

日志文件位于 [log/](file:///Users/nice/Jinlin/PythonCase/hwatch/log) 目录下：
- `collector.log`：数据采集相关日志
- `web_server.log`：Web相关日志
- `scheduler.log`：任务调度及执行相关日志
- `database.log`：数据库日志
- `watchdog.log`：watchdog 日志
- `app.log`：主进程日志


### 数据库管理

采集的数据存储在 [hwatch.db](file:///Users/nice/Jinlin/PythonCase/hwatch/hwatch.db) SQLite 数据库中，可以使用 SQLite 工具查看和分析。
