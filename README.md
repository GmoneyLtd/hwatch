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

## 🔐 Web账户管理

### 默认登录信息
- **用户名**: `admin`
- **密码**: `123456`

### 自定义账户配置
通过环境变量自定义登录账户：

```bash
# 设置自定义用户名和密码
export WEB_USERNAME=myuser
export WEB_PASSWORD=mypassword

# 启动应用
python app.py
```

### 会话管理机制
- **会话时长**: 8小时绝对过期时间
- **安全令牌**: 使用加密安全的随机令牌
- **自动清理**: 系统自动清理过期会话
- **浏览器关闭**: 会话在浏览器关闭时自动清除
- **并发登录**: 支持多用户同时登录

### 安全特性
- 密码哈希存储（使用bcrypt）
- 会话令牌加密
- 自动登出机制
- 防止会话劫持

## 📋 日志系统配置

### 日志级别设置

**优先级顺序（从高到低）：**
1. **环境变量 `LOG_LEVEL`**（最高优先级）
2. **命令行参数 `--level`**（中等优先级）
3. **默认值 `WARNING`**（最低优先级）

### 使用方式

**方式1：环境变量设置（推荐）**
```bash
# 设置日志级别
export LOG_LEVEL=INFO
python app.py

# 支持的级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**方式2：命令行参数**
```bash
# 临时设置日志级别
python app.py --level DEBUG

# 查看帮助信息
python app.py --help
```

**方式3：组合使用**
```bash
# 环境变量优先级更高，会忽略命令行参数
export LOG_LEVEL=ERROR
python app.py --level DEBUG  # 实际使用ERROR级别
```

### 日志级别说明

| 级别 | 用途 | 输出内容 |
|------|------|----------|
| `DEBUG` | 开发调试 | 详细的调试信息、变量值、执行流程 |
| `INFO` | 一般信息 | 应用启动、任务执行、配置加载等 |
| `WARNING` | 警告信息 | 配置问题、连接异常、重试操作等 |
| `ERROR` | 错误信息 | 任务失败、连接错误、解析失败等 |
| `CRITICAL` | 严重错误 | 系统崩溃、致命错误等 |

### 日志文件位置

```
log/
├── app.log          # 应用主日志（按日期轮转）
├── scheduler.log    # 任务调度日志
└── error.log        # 错误日志（ERROR级别及以上）
```

### 日志配置特性

- **自动轮转**: 日志文件按日期自动轮转
- **大小限制**: 单个日志文件最大10MB
- **保留策略**: 保留最近7天的日志文件
- **格式统一**: 时间戳 | 级别 | 模块 | 消息内容
- **彩色输出**: 控制台输出支持颜色区分级别

### 日志使用建议

**开发环境：**
```bash
export LOG_LEVEL=DEBUG
```

**生产环境：**
```bash
export LOG_LEVEL=WARNING
```

**故障排查：**
```bash
export LOG_LEVEL=INFO
```

## 📊 Web界面使用

### 登录访问
1. 启动应用后访问 http://localhost:8080
2. 使用默认账户或自定义账户登录
3. 会话有效期8小时，到期需重新登录

### 仪表板功能
- **实时监控**: 显示所有启用任务的执行状态
- **数据图表**: 历史数据趋势可视化展示
- **详细信息**: 鼠标悬停查看具体数值和时间
- **设备状态**: 显示设备连接状态和最后更新时间

### 任务管理
- **任务列表**: 查看所有配置的任务及其状态
- **启用控制**: 动态启用/禁用任务
- **配置编辑**: 实时编辑配置文件（需重启生效）
- **执行历史**: 查看任务执行历史和结果

### 数据查看
- **SQLite数据**: 在Web界面查看图表和历史趋势
- **文件数据**: 原始输出保存在 `outfile/` 目录
- **实时更新**: 数据自动刷新，无需手动刷新页面
- **导出功能**: 支持数据导出为CSV格式

## 🔧 高级功能

### SSH连接池
系统自动管理SSH连接池，提高性能：
- **连接复用**: 相同任务和设备的连接会被复用
- **自动清理**: 超过10分钟未使用的连接会被自动清理
- **健康检查**: 使用前会检查连接状态
- **并发控制**: 每个设备最多维护5个并发连接

### 错误处理机制
- **自动重试**: 连接失败时按配置进行重试
- **指数退避**: 重试间隔采用指数退避策略（2^attempt秒）
- **超时控制**: 连接和命令执行都有独立的超时设置
- **详细日志**: 记录所有错误信息便于故障排查

### 数据存储策略
- **SQLite**: 结构化数据存储，支持图表展示和历史查询
- **File**: 原始输出存储，便于调试和数据审计
- **Null**: 不存储结果，适用于操作型命令

### 任务调度机制
- **Interval模式**: 固定间隔执行，基于任务开始时间计算下次执行
- **Delay模式**: 延迟执行，任务完成后等待指定时间再执行
- **频次控制**: 支持限制任务执行次数
- **智能增量更新**: 配置文件变更时只刷新变更的任务，保持其他任务运行状态

### 🔄 增量更新机制

#### 工作原理
系统通过任务签名（MD5哈希）智能识别配置变更，实现精确的增量更新：

1. **任务签名生成**: 为每个任务的关键配置生成MD5签名
2. **配置对比**: 新旧配置对比，精确识别变更类型
3. **分类处理**: 根据变更类型执行不同的更新策略
4. **状态保持**: 未变更的任务保持运行状态不受影响

#### 变更类型处理

| 变更类型 | 处理策略 | 影响范围 |
|----------|----------|----------|
| **新增任务** | 直接添加到调度器 | 仅新任务 |
| **删除任务** | 移除所有相关作业和计数 | 仅删除的任务 |
| **修改任务** | 先移除再重新添加 | 仅修改的任务 |
| **未变更任务** | 保持原状 | 无影响 |

#### 任务签名包含的配置
- 任务基本信息：alias、enabled、protocol、targets、storage
- 调度配置：frequency、mode、seconds
- 协议特定配置：SSH命令、SNMP OID和类型
- 解析配置：正则表达式、数学运算、标签

#### 增量更新日志示例
```
检测到配置变更, 开始重载...
开始增量更新任务调度...
检测到配置变更: 新增1个, 删除0个, 修改2个, 未变更5个
已删除任务: old_task
已更新任务: fgSysMemUsage
已更新任务: fgProcessorUsage_per
已添加任务: new_monitoring_task
增量更新完成! 共处理 4 个变更
配置重载和任务增量更新成功!
```

#### 性能优势
- **减少中断**: 运行中的任务不会被无故重启
- **提高稳定性**: 避免全量刷新导致的连接重建和数据丢失
- **节约资源**: 只处理真正变更的任务，减少系统开销
- **更快响应**: 增量更新比全量更新响应更快
- **连接保持**: SSH连接池中的连接得以保持，避免重新建立连接

#### 防重复机制
系统具有完善的防重复处理机制：
- **文件系统事件**: 编辑器保存可能触发多个文件系统事件
- **配置对比**: 第二次检测如无实际变更会跳过处理
- **日志记录**: 清晰记录每次检测结果，便于调试

#### 使用建议
1. **批量修改**: 建议一次性完成多个配置修改，减少频繁更新
2. **测试验证**: 修改后观察日志确认更新结果
3. **备份配置**: 重要变更前备份配置文件
4. **监控影响**: 关注修改后任务的执行状态和性能表现

## 📝 系统日志文件

### 日志文件结构
```
log/
├── app.log              # 应用主日志
├── scheduler.log        # 任务调度专用日志
├── error.log           # 错误级别日志
└── debug.log           # 调试级别日志（仅DEBUG模式）

outfile/
├── task_alias_device_name.log    # 文件存储模式的任务输出
└── ...
```

### 日志内容说明
- **应用启动**: 系统初始化、配置加载、服务启动信息
- **任务执行**: 每个任务的执行状态、耗时、结果统计
- **连接管理**: SSH/SNMP连接的建立、复用、清理过程
- **错误信息**: 连接失败、命令执行失败、解析错误等
- **性能指标**: 任务执行时间、连接池状态、内存使用等

## 🚨 重要注意事项

### 安全考虑
1. **配置文件安全**: `config.yaml`包含设备密码，请设置适当的文件权限
2. **网络安全**: 确保监控网络的安全性，避免密码泄露
3. **Web访问**: 生产环境建议配置HTTPS和强密码
4. **日志安全**: 日志文件可能包含敏感信息，注意访问控制

### 网络要求
1. **连通性**: 监控主机必须能访问目标设备的SSH/SNMP端口
2. **防火墙**: 确保相关端口（SSH:22, SNMP:161）已开放
3. **带宽**: 频繁采集可能产生网络流量，注意带宽规划
4. **延迟**: 网络延迟会影响任务执行时间，合理设置超时值

### 性能建议
1. **采集间隔**: 根据数据变化频率和网络条件合理设置
2. **并发控制**: 避免同时执行过多任务导致资源竞争
3. **存储选择**: 频繁查询用SQLite，调试审计用文件存储
4. **数据清理**: 定期清理历史数据避免数据库过大

### 维护建议
1. **定期备份**: 备份配置文件和重要数据
2. **日志轮转**: 系统会自动轮转日志，注意磁盘空间
3. **监控告警**: 建议配置外部监控系统监控HWatch运行状态
4. **版本更新**: 关注项目更新，及时升级修复安全问题

## 🔍 故障排除指南

### 常见问题及解决方案

#### SSH连接问题
**症状**: SSH任务显示连接失败
**排查步骤**:
1. 检查设备IP地址和端口配置
2. 验证用户名和密码是否正确
3. 测试网络连通性：`ping <device_ip>`
4. 手动SSH测试：`ssh username@device_ip`
5. 检查设备SSH服务状态
6. 查看详细错误日志

**常见原因**:
- 网络不通或防火墙阻断
- 认证信息错误
- SSH服务未启动或配置问题
- 设备资源不足无法建立新连接

#### SNMP查询问题
**症状**: SNMP任务无响应或返回空值
**排查步骤**:
1. 验证SNMP团体名配置
2. 检查设备SNMP服务状态
3. 使用snmpwalk工具测试：`snmpwalk -v2c -c community device_ip oid`
4. 确认OID是否正确和设备支持
5. 检查SNMP端口是否开放

#### 数据解析问题
**症状**: 正则表达式不匹配或解析失败
**排查步骤**:
1. 设置日志级别为DEBUG查看原始输出
2. 使用在线正则表达式测试工具验证
3. 确认捕获组数量与labels数量一致
4. 检查多行匹配是否需要`(?s)`标志
5. 验证数学运算表达式语法

#### Web界面问题
**症状**: 无法访问Web界面或登录失败
**排查步骤**:
1. 检查应用是否正常启动
2. 确认端口8080是否被占用
3. 验证登录凭据是否正确
4. 检查浏览器控制台错误信息
5. 查看应用日志中的Web服务器错误

### 调试技巧

#### 启用详细日志
```bash
export LOG_LEVEL=DEBUG
python app.py
```

#### 单任务测试
临时禁用其他任务，只启用需要调试的任务：
```yaml
- alias: "debug_task"
  enabled: true    # 只启用这个任务
  # ... 其他配置
```

#### 手动命令测试
在设备上手动执行命令，对比输出格式：
```bash
ssh admin@device_ip "show version"
```

#### 正则表达式调试
使用Python交互式环境测试正则表达式：
```python
import re
pattern = r"(?s)BIOS version:\s*(\d+).*?Branch point:\s*(\d+)"
text = "your_device_output_here"
matches = re.search(pattern, text)
print(matches.groups() if matches else "No match")
```

## 📈 性能优化建议

### 系统级优化
1. **资源配置**: 确保足够的CPU和内存资源
2. **网络优化**: 使用高速稳定的网络连接
3. **存储优化**: 使用SSD存储提高数据库性能
4. **系统调优**: 调整操作系统网络参数

### 应用级优化
1. **合理间隔**: 避免过于频繁的数据采集
2. **批量操作**: 在单个SSH会话中执行多个命令
3. **连接复用**: 系统自动管理SSH连接池
4. **异步处理**: 任务并行执行提高效率

### 配置优化
1. **超时设置**: 根据网络条件调整超时时间
2. **重试策略**: 合理设置重试次数避免资源浪费
3. **存储选择**: 根据使用场景选择合适的存储方式
4. **任务分组**: 将相关任务分组执行减少连接开销

## 🤝 贡献指南

### 开发环境搭建
```bash
# 克隆项目
git clone <repository-url>
cd hwatch

# 安装开发依赖
uv sync --dev

# 运行测试
python -m pytest test/

# 代码格式化
ruff format .

# 代码检查
ruff check .
```

### 提交规范
- 遵循Conventional Commits规范
- 提供详细的commit message
- 包含必要的测试用例
- 更新相关文档

### Issue报告
报告问题时请提供：
1. 详细的问题描述
2. 复现步骤
3. 系统环境信息
4. 相关日志输出
5. 配置文件（脱敏后）

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。

---

**HWatch** - 让网络设备监控变得简单高效！

如有问题或建议，欢迎提交Issue或Pull Request。
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