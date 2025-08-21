# HWatch - 网络设备监控系统

HWatch是一个基于Python的网络设备监控系统，支持通过SSH和SNMP协议采集设备数据，提供实时监控、数据存储和Web可视化界面。

## 🚀 主要特性

- **多协议支持**: SSH命令执行和SNMP数据采集
- **灵活调度**: 支持间隔模式(interval)和延迟模式(delay)的任务调度
- **数据解析**: 强大的正则表达式解析和数学运算功能
- **多种存储**: SQLite数据库存储和文件存储
- **实时监控**: Web界面实时图表展示
- **连接池**: SSH连接复用，提高性能
- **容错机制**: 完善的重试和错误处理

## 📋 系统要求

- Python 3.11+
- SQLite 3
- 网络设备支持SSH/SNMP协议

## 🛠️ 安装部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd hwatch
```

### 2. 安装依赖
```bash
# 使用uv (推荐)
uv sync

# 或使用pip
pip install -r requirements.txt
```

### 3. 配置文件
复制并编辑配置文件：
```bash
cp config_init.yaml config.yaml
```

### 4. 启动应用
```bash
python app.py
```

访问 http://localhost:8080 查看Web界面。

## ⚙️ 配置文件详解 (config.yaml)

### 设备配置 (devices)

每个设备包含基本信息和连接配置：

```yaml
devices:
- name: "Router_A"           # 设备标识符，必须唯一
  ip: "192.168.1.100"        # 设备IP地址
  connection:                # 连接配置
    ssh:                     # SSH连接配置
      username: "admin"      # SSH用户名
      password: "admin123"   # SSH密码
      port: 22              # SSH端口，默认22
      timeout: 10           # 连接超时时间(秒)
      retry: 3              # 重试次数
    snmp:                   # SNMP连接配置
      community: "public"    # SNMP团体名
      port: 161             # SNMP端口，默认161
      timeout: 10           # 超时时间(秒)
      retry: 3              # 重试次数
```

### 任务配置 (tasks)

#### 基础配置字段
```yaml
tasks:
- alias: "任务别名"          # 任务唯一标识符
  enabled: true            # 是否启用任务
  protocol: "ssh"          # 协议类型: ssh 或 snmp
  targets:                 # 目标设备列表
  - "Router_A"
  - "Fortinet_60"
  storage: "sqlite"        # 存储方式: sqlite, file, 或 null
```

#### 调度配置 (schedule)
```yaml
schedule:
  frequency: 0             # 执行次数限制，0表示无限制
  mode: "interval"         # 调度模式: interval 或 delay
  seconds: 60             # 执行间隔(秒)
```

**调度模式说明：**
- `interval`: 固定间隔执行，任务完成后立即安排下次执行
- `delay`: 延迟执行，任务完成后等待指定时间再执行下次

#### SSH任务配置

**单命令执行：**
```yaml
- alias: "get_router_version"
  enabled: true
  protocol: "ssh"
  command: 
  - "show version"
  targets: ["Router_A"]
  schedule:
    frequency: 1           # 仅执行一次
  storage: "sqlite"
```

**多命令执行：**
```yaml
- alias: "system_check"
  enabled: true
  protocol: "ssh"
  command: 
  - "get system status"
  - "get system arp"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 20
    mode: "delay"
    seconds: 120
  storage: "file"
```

**带数据解析的SSH任务：**
```yaml
- alias: "parse_system_info"
  enabled: true
  protocol: "ssh"
  command: 
  - "get system status"
  parse:
    regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
    calculate:
    - "/1000000"           # 第一个值除以1000000
    - "*10"               # 第二个值乘以10
  labels:
  - "BIOS_Version"
  - "Branch_Point"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "delay"
    seconds: 120
  storage: "sqlite"
```

#### SNMP任务配置

**SNMP Get (单值获取)：**
```yaml
- alias: "memory_usage"
  enabled: true
  protocol: "snmp"
  type: "snmpget"
  oid: "1.3.6.1.4.1.12356.101.4.1.4.0"
  labels: 
  - "fgSysMemUsage"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"
```

**SNMP Walk (多值获取)：**
```yaml
- alias: "processor_usage"
  enabled: true
  protocol: "snmp"
  type: "snmpwalk"
  oid: "1.3.6.1.4.1.12356.101.4.4.2.1.2"
  labels:
  - "fgProcessorUsage.1"
  - "fgProcessorUsage.2"
  - "fgProcessorUsage.3"
  - "fgProcessorUsage.4"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"
```

### 数据解析配置 (parse)

#### 正则表达式解析
```yaml
parse:
  regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
  calculate:
  - "/1000000"             # 第一个值除以1000000
  - "*10"                 # 第二个值乘以10
```

**正则表达式技巧：**
- 使用 `(?s)` 启用多行模式，让 `.` 匹配换行符
- 使用 `\\s*` 匹配可能的空白字符
- 使用 `.*?` 进行非贪婪匹配
- 捕获组 `()` 的数量必须与 `labels` 数量一致

#### 数学运算 (calculate)
支持的运算符：
- `"+数值"`: 加法运算，如 `"+100"`
- `"-数值"`: 减法运算，如 `"-50"`
- `"*数值"`: 乘法运算，如 `"*1024"`
- `"/数值"`: 除法运算，如 `"/1000"`

**使用场景：**
- 单位转换：字节转KB (`"/1024"`)
- 百分比转小数：(`"/100"`)
- 数值标准化：大数值缩放 (`"/1000000"`)

### 基于实际配置的完整示例

以下是基于项目实际配置文件的完整示例：

```yaml
devices:
- name: "Router_A"
  ip: "192.168.1.100"
  connection:
    ssh:
      username: "admin"
      password: "admin123"
      port: 22
      timeout: 10
      retry: 3
    snmp:
      community: "public"
      port: 161
      timeout: 10
      retry: 3

- name: "Fortinet_60"
  ip: "192.168.2.1"
  connection:
    ssh:
      username: "admin"
      password: "ChengduMicro@2025"
      port: 22
      timeout: 2
      retry: 0
    snmp:
      community: "awatch"
      port: 161
      timeout: 2
      retry: 0

tasks:
# SSH任务 - 系统信息采集带解析
- alias: "run_show_command"
  enabled: true
  protocol: "ssh"
  command: 
  - "get system status"
  - "get system arp"
  parse:
    regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
    calculate:
    - "/1000000"  # BIOS版本数值标准化
    - "*10"       # Branch point放大10倍
  labels:
  - "BIOS_Version"
  - "Branch_Point"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 20
    mode: "delay"
    seconds: 120
  storage: "file"

# SNMP任务 - CPU使用率监控
- alias: "fgProcessorUsage_per"
  enabled: true
  protocol: "snmp"
  type: "snmpwalk"
  oid: "1.3.6.1.4.1.12356.101.4.4.2.1.2"
  labels:
  - "fgProcessorUsage.1"
  - "fgProcessorUsage.2"
  - "fgProcessorUsage.3"
  - "fgProcessorUsage.4"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"

# SNMP任务 - 内存使用率监控
- alias: "fgSysMemUsage"
  enabled: true
  protocol: "snmp"
  type: "snmpget"
  oid: "1.3.6.1.4.1.12356.101.4.1.4.0"
  labels: 
  - "fgSysMemUsage"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"

# SSH任务 - 一次性执行
- alias: "get_router_a_version"
  enabled: false
  protocol: "ssh"
  command: 
  - "show version"
  targets: ["Router_A"]
  schedule:
    frequency: 1  # 仅执行一次
  storage: "sqlite"

# SSH任务 - 操作型命令(不存储结果)
- alias: "clear_router_a_counters"
  enabled: false
  protocol: "ssh"
  command: 
  - "clear counters"
  targets: ["Router_A"]
  schedule:
    frequency: 1
  storage: null  # 不存储结果
```

## 📊 Web界面使用

### 仪表板
- 实时显示所有启用任务的状态
- 图表展示历史数据趋势
- 鼠标悬停查看详细数值

### 任务管理
- 查看所有配置的任务
- 启用/禁用任务
- 实时编辑配置文件

### 数据查看
- SQLite存储的数据可在Web界面查看图表
- 文件存储的数据保存在 `outfile/` 目录

## 🔧 高级功能

### SSH连接池
系统自动管理SSH连接池，提高性能：
- 连接复用：相同任务和设备的连接会被复用
- 自动清理：超过10分钟未使用的连接会被自动清理
- 健康检查：使用前会检查连接状态

### 错误处理
- 连接失败自动重试
- 指数退避重试策略
- 详细的错误日志记录

### 数据存储
- **SQLite**: 结构化数据，支持图表展示
- **File**: 原始输出，便于调试和审计

## 📝 日志文件

- `log/scheduler.log`: 任务调度日志
- `outfile/*.log`: 文件存储模式的输出文件

## 🚨 注意事项

1. **安全性**: 配置文件包含明文密码，请妥善保管
2. **网络**: 确保监控主机能访问目标设备的SSH/SNMP端口
3. **性能**: 合理设置任务间隔，避免过于频繁的采集
4. **存储**: SQLite数据库会随时间增长，定期清理历史数据

## 🔍 故障排除

### 常见问题

**SSH连接失败**
- 检查IP地址、用户名、密码
- 确认SSH服务已启用
- 检查网络连通性

**SNMP无响应**
- 验证SNMP团体名
- 确认SNMP服务已启用
- 检查OID是否正确

**正则表达式不匹配**
- 使用调试模式查看原始输出
- 验证捕获组数量与labels一致
- 测试正则表达式语法

**数学运算失败**
- 确认原始值为数字格式
- 检查运算符语法
- 避免除零操作

## 📈 性能优化建议

1. **合理设置采集间隔**: 根据数据变化频率调整
2. **使用连接池**: SSH任务会自动复用连接
3. **批量命令**: 在单个SSH会话中执行多个命令
4. **存储选择**: 频繁查询的数据使用SQLite，调试数据使用文件

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

[添加许可证信息]