# HWatch - Network Device Monitoring System

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116+-green.svg)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-3+-lightblue.svg)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

HWatch is a lightweight, high-performance network device monitoring system built with Python. It supports data collection via SSH and SNMP protocols, providing real-time monitoring, data storage, and web-based visualization.

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "HWatch System"
        A[app.py] --> B[TaskScheduler]
        A --> C[WebServer]
        A --> D[FileWatcher]
        A --> E[Database]
        
        B --> F[Collector]
        F --> G[SSH Pool]
        F --> H[SNMP Pool]
        
        C --> I[Web UI]
        C --> J[REST API]
        C --> K[Authentication]
        
        D --> L[config.yaml]
        L --> M[Config Reload]
        M --> B
        
        F --> N[Data Parser]
        N --> O[SQLite Storage]
        N --> P[File Storage]
    end
    
    subgraph "Network Devices"
        Q[Router A]
        R[Firewall]
        S[Access Point]
    end
    
    subgraph "Protocols"
        T[SSH Commands]
        U[SNMP Get/Walk]
    end
    
    G --> T
    H --> U
    T --> Q
    T --> R
    U --> Q
    U --> R
    U --> S
    
    I --> V[Web Browser]
    J --> W[API Clients]
```

## 🛠️ Technology Stack

### Core Framework
- **Python 3.13+**: Main programming language
- **FastAPI 0.116+**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for FastAPI applications
- **AsyncIO**: Asynchronous programming support

### Database & Storage
- **SQLite 3**: Lightweight relational database for structured data
- **Aiosqlite**: Async SQLite driver
- **File System**: Plain text log storage option

### Network Protocols
- **AsyncSSH 2.21+**: SSH client for command execution
- **PySNMP 7.1+**: SNMP client for device monitoring
- **Connection Pooling**: Optimized connection management

### Task Scheduling
- **APScheduler 3.11+**: Advanced Python Scheduler
- **Interval/Delay Modes**: Flexible scheduling strategies
- **Hot Reload**: Dynamic configuration updates

### Web Interface
- **Jinja2 3.1+**: Template engine for dynamic HTML
- **ECharts 5.4+**: Interactive data visualization library
- **ACE Editor**: Code editor for YAML configuration
- **Custom CSS**: Responsive design with custom styling
- **Session-based Authentication**: Secure user management

### Configuration & Logging
- **PyYAML 6.0+**: YAML configuration parser
- **Loguru 0.7+**: Advanced logging system
- **Watchdog 6.0+**: File system monitoring

### Development & Deployment
- **UV**: Fast Python package manager
- **Docker**: Containerization support
- **Docker Compose**: Multi-container orchestration
- **Alpine Linux**: Lightweight container base

## 📊 Module Architecture

### 1. Application Entry (`app.py`)
```mermaid
graph LR
    A[Signal Handler] --> B[Graceful Shutdown]
    C[Main Loop] --> D[Database Init]
    C --> E[Config Load]
    C --> F[Scheduler Start]
    C --> G[File Watcher]
    C --> H[Web Server]
    
    B --> I[Stop Web Server]
    B --> J[Stop File Monitor]
    B --> K[Stop Scheduler]
    B --> L[Cleanup Connections]
    B --> M[Close Database]
```

**Key Features:**
- **Graceful Shutdown**: Proper signal handling with ordered component shutdown
- **Configuration Management**: Hot-reload configuration without restart
- **Component Orchestration**: Manages all system components lifecycle
- **Error Handling**: Comprehensive error recovery and logging

### 2. Task Scheduler (`core/scheduler.py`)
```mermaid
graph TB
    A[TaskScheduler] --> B[Schedule All Tasks]
    A --> C[Incremental Update]
    A --> D[Task Execution]
    
    B --> E[Interval Jobs]
    B --> F[Delay Jobs]
    
    C --> G[Compare Configs]
    C --> H[Add New Tasks]
    C --> I[Remove Old Tasks]
    C --> J[Update Modified Tasks]
    
    D --> K[Execute Job]
    K --> L[Run Collector]
    K --> M[Process Results]
    K --> N[Schedule Next Run]
```

**Key Features:**
- **Dynamic Scheduling**: Add/remove/modify tasks without restart
- **Multiple Modes**: Support for interval and delay scheduling
- **Configuration Tracking**: Compare task configurations for incremental updates
- **Execution Limits**: Control task execution frequency and lifetime

### 3. Data Collector (`core/collector.py`)
```mermaid
graph TB
    A[run_task] --> B{Protocol Type}
    
    B -->|SSH| C[SSH Collector]
    B -->|SNMP| D[SNMP Collector]
    
    C --> E[Connection Pool]
    C --> F[Command Execution]
    C --> G[Output Parsing]
    
    D --> H[Engine Pool]
    D --> I[SNMP Get/Walk]
    D --> J[Data Processing]
    
    E --> K[Reuse/Create Connection]
    F --> L[Execute Commands]
    G --> M[Regex Parsing]
    G --> N[Math Calculations]
    
    H --> O[Reuse/Create Engine]
    I --> P[OID Queries]
    J --> Q[Value Extraction]
```

**Key Features:**
- **Connection Pooling**: Efficient SSH/SNMP connection management
- **Protocol Support**: SSH command execution and SNMP data collection
- **Data Parsing**: Advanced regex parsing with mathematical operations
- **Error Recovery**: Retry mechanisms and connection health monitoring

### 4. Web Server (`core/web_server.py`)
```mermaid
graph TB
    A[FastAPI App] --> B[Authentication]
    A --> C[Static Files]
    A --> D[API Routes]
    A --> E[Web Pages]
    
    B --> F[Session Management]
    B --> G[Login/Logout]
    
    D --> H[Device List API]
    D --> I[Task List API]
    D --> J[Chart Data API]
    D --> K[Health Check API]
    
    E --> L[Dashboard]
    E --> M[Task Management]
    E --> N[Device Status]
    E --> O[Data Visualization]
```

**Key Features:**
- **RESTful APIs**: Comprehensive API endpoints for data access
- **Interactive Dashboard**: Real-time monitoring and visualization
- **Authentication**: Session-based security with configurable timeouts
- **Responsive Design**: Mobile-friendly web interface

### 5. Configuration System (`core/config_loader.py`)
```mermaid
graph LR
    A[config.yaml] --> B[YAML Parser]
    B --> C[Validation]
    C --> D[Device Config]
    C --> E[Task Config]
    
    D --> F[Connection Settings]
    D --> G[SSH Parameters]
    D --> H[SNMP Parameters]
    
    E --> I[Schedule Config]
    E --> J[Protocol Config]
    E --> K[Storage Config]
    E --> L[Parse Config]
```

**Key Features:**
- **YAML Configuration**: Human-readable configuration format
- **Hot Reload**: Monitor and reload configuration changes
- **Validation**: Comprehensive configuration validation
- **Type Safety**: Strongly typed configuration objects

### 6. Database Layer (`core/database.py`)
```mermaid
graph TB
    A[Database Manager] --> B[SQLite Connection]
    A --> C[Schema Management]
    A --> D[Data Operations]
    
    B --> E[Async Connection Pool]
    B --> F[Connection Lifecycle]
    
    C --> G[Table Creation]
    C --> H[Schema Migration]
    
    D --> I[Save Results]
    D --> J[Query Data]
    D --> K[Chart Data]
    D --> L[Device/Task Lists]
```

**Key Features:**
- **Async Operations**: Non-blocking database operations
- **Auto Schema**: Automatic table creation and management
- **Data Aggregation**: Efficient data retrieval for charts and reports
- **Connection Management**: Proper connection lifecycle handling

## 🚀 Quick Start

### Prerequisites
- Python 3.13 or higher
- Network devices with SSH/SNMP access
- Basic understanding of network protocols

### Installation Methods

#### Method 1: Using UV (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd hwatch

# Install dependencies with UV
uv sync

# Copy and configure settings
cp config_init.yaml config.yaml
# Edit config.yaml according to your environment

# Start the application
uv run python app.py
```

#### Method 2: Using Docker
```bash
# Clone the repository
git clone <repository-url>
cd hwatch

# Build and run with Docker Compose
docker-compose up -d

# Or build manually for single platform
docker build -t hwatch .
docker run -p 8080:8080 -v $(pwd)/config.yaml:/app/config.yaml hwatch

# Or build for multiple platforms using buildx
docker buildx build --no-cache --platform linux/amd64,linux/arm64 \
  -t registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:0.1.0 \
  -t registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:latest --load .
```

#### Method 3: Traditional Python
```bash
# Clone the repository
git clone <repository-url>
cd hwatch

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure and start
cp config_init.yaml config.yaml
python app.py
```

### Access the Application
- **Web Interface**: http://localhost:8080
- **Default Credentials**: admin / 123456
- **API Documentation**: http://localhost:8080/docs
- **Help & Documentation**: Click the help icon (?) in the dashboard header or visit http://localhost:8080/help

## ⚙️ Configuration Guide (config.yaml)

### YAML List Syntax Clarification

**Important:** YAML supports two equivalent syntaxes for lists. Both forms are valid and interchangeable:

#### Flow Syntax (Inline)
```yaml
targets: ["Router_A", "Fortinet_60"]
labels: ["BIOS_Version", "Branch_Point"]
```

#### Block Syntax (Multi-line)
```yaml
targets:
- "Router_A"
- "Fortinet_60"
labels:
- "BIOS_Version"
- "Branch_Point"
```

#### Mixed Usage in Examples
Throughout this documentation, you'll see both syntaxes used:
- **Flow syntax** (`[item1, item2]`) - Often used for short lists in examples
- **Block syntax** (using `-`) - Often used for longer lists or when readability is important

**Choose the style you prefer** - both work identically. The block syntax is often more readable for longer lists or when items are lengthy.

---

### Device Configuration (devices)

Each device contains basic information and connection configuration:

```yaml
devices:
- name: "Router_A"              # Device identifier, must be unique
  ip: "192.168.1.100"           # Device IP address
  connection:                   # Connection configuration
    ssh:                        # SSH connection settings
      username: "admin"          # SSH username
      password: "admin123"       # SSH password
      port: 22                  # SSH port, default 22
      timeout: 10               # Connection timeout (seconds)
      retry: 3                  # Number of retry attempts
    snmp:                       # SNMP connection settings
      community: "public"        # SNMP community string
      port: 161                 # SNMP port, default 161
      timeout: 10               # Timeout (seconds)
      retry: 3                  # Number of retry attempts
```

### Task Configuration (tasks)

#### Basic Configuration Fields
```yaml
tasks:
- alias: "task_alias"           # Unique task identifier
  enabled: true                 # Whether to enable the task
  protocol: "ssh"               # Protocol type: ssh or snmp
  targets:                      # Target device list (using block syntax)
  - "Router_A"
  - "Fortinet_60"
  storage: "sqlite"             # Storage method: sqlite, file, or null
```

**Note:** The `targets` field above uses block syntax. You could also write it as `targets: ["Router_A", "Fortinet_60"]` using flow syntax.

#### Scheduling Configuration (schedule)
```yaml
schedule:
  frequency: 0                  # Execution count limit, 0 means unlimited
  mode: "interval"              # Scheduling mode: interval or delay
  seconds: 60                   # Execution interval (seconds)
```

**Scheduling Mode Explanation:**
- `interval`: Fixed interval execution, next execution scheduled immediately after current execution starts
- `delay`: Delayed execution, next execution scheduled after waiting specified time following completion

#### SSH Task Configuration

**Single Command Execution:**
```yaml
- alias: "get_router_version"
  enabled: true
  protocol: "ssh"
  command: 
  - "show version"
  targets: ["Router_A"]
  schedule:
    frequency: 1                # Execute only once
  storage: "sqlite"
```

**Multiple Command Execution:**
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

**SSH Task with Data Parsing:**
```yaml
- alias: "parse_system_info"
  enabled: true
  protocol: "ssh"
  command: 
  - "get system status"
  parse:
    regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
    calculate:
    - "/1000000"                # First value divided by 1000000
    - "*10"                     # Second value multiplied by 10
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

#### SNMP Task Configuration (New Mixed Operations Format)

**SNMP Get (Single Value Retrieval):**
```yaml
- alias: "memory_usage"
  enabled: true
  protocol: "snmp"
  snmp:
    oid:
    - "1.3.6.1.4.1.12356.101.4.1.4.0"
    type:
    - "snmpget"
  labels:
  - "fgSysMemUsage"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"
```

**SNMP Walk (Multiple Value Retrieval with Auto-Generated Labels):**
```yaml
- alias: "processor_usage"
  enabled: true
  protocol: "snmp"
  snmp:
    oid:
    - "1.3.6.1.4.1.12356.101.4.4.2.1.2"
    type:
    - "snmpwalk"
  labels:
  - "fgProcessorUsage"          # Auto-generates: .1, .2, .3, .4
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"
```

**Mixed SNMP Operations (Advanced):**
```yaml
- alias: "mixed_snmp_monitoring"
  enabled: true
  protocol: "snmp"
  snmp:
    oid:
    - "1.3.6.1.4.1.12356.101.4.1.8.0"    # Session count (single)
    - "1.3.6.1.4.1.12356.101.4.4.2.1.2"  # CPU usage (multiple)
    - "1.3.6.1.4.1.12356.101.4.1.4.0"    # Memory usage (single)
    type:
    - "snmpget"   # Single value
    - "snmpwalk"  # Multiple values -> generates .1, .2, .3, .4 suffixes
    - "snmpget"   # Single value
  labels:
  - "SessionCount"
  - "CPUUsage"     # Becomes CPUUsage.1, CPUUsage.2, CPUUsage.3, CPUUsage.4
  - "MemoryUsage"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 10
  storage: "sqlite"
```

### Data Parsing Configuration (parse)

#### Regular Expression Parsing
```yaml
parse:
  regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
  calculate:
  - "/1000000"                  # First value divided by 1000000
  - "*10"                      # Second value multiplied by 10
```

**Regular Expression Tips:**
- Use `(?s)` to enable multiline mode, allowing `.` to match newline characters
- Use `\\s*` to match possible whitespace characters
- Use `.*?` for non-greedy matching
- The number of capture groups `()` must match the number of `labels`

#### Mathematical Operations (calculate)
Supported operators:
- `"+number"`: Addition operation, e.g., `"+100"`
- `"-number"`: Subtraction operation, e.g., `"-50"`
- `"*number"`: Multiplication operation, e.g., `"*1024"`
- `"/number"`: Division operation, e.g., `"/1000"`

**Use Cases:**
- Unit conversion: Bytes to KB (`"/1024"`)
- Percentage to decimal: (`"/100"`)
- Value normalization: Large value scaling (`"/1000000"`)

### Dynamic Label Generation

The system now supports intelligent dynamic label generation for SNMP operations:

#### Automatic Label Suffixing
- **snmpget operations**: Use the configured base label directly
- **snmpwalk operations**: Automatically append numeric suffixes (.1, .2, .3, etc.)
- **Mixed operations**: Handle both types seamlessly in a single task

#### Smart Label Mapping
```yaml
labels:
- "SessionCount"    # snmpget -> "SessionCount"
- "CPUUsage"        # snmpwalk -> "CPUUsage.1", "CPUUsage.2", "CPUUsage.3", "CPUUsage.4"
- "MemoryUsage"     # snmpget -> "MemoryUsage"
```

#### Benefits
- **No Manual Management**: Labels are generated based on actual SNMP results
- **Accurate Mapping**: Each returned value gets a unique, meaningful label
- **Consistent Naming**: Predictable label patterns for easy data access
- **Simplified Configuration**: No need to pre-define all possible walk result labels

### Complete Example Based on Latest Configuration Format

The following is a complete example using the new protocol-separated configuration:

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
# SSH Task - System information collection with parsing
- alias: "run_show_command"
  enabled: true
  protocol: "ssh"
  ssh:
    command:
    - "get system status"
    - "get system arp"
    parse:
      regex: "(?s)BIOS version:\\s*(\\d+).*?Branch point:\\s*(\\d+)"
      calculate:
      - "/1000000"  # BIOS version value normalization
      - "*10"       # Branch point amplified by 10
  labels:
  - "BIOS_Version"
  - "Branch_Point"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 20
    mode: "delay"
    seconds: 120
  storage: "file"

# SNMP Task - CPU usage monitoring with auto-generated labels
- alias: "fgProcessorUsage_per"
  enabled: true
  protocol: "snmp"
  snmp:
    oid:
    - "1.3.6.1.4.1.12356.101.4.4.2.1.2"
    type:
    - "snmpwalk"
  labels:
  - "fgProcessorUsage"  # Auto-generates: .1, .2, .3, .4
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 5
  storage: "sqlite"

# SNMP Task - Mixed operations (get + walk + get)
- alias: "mixed_snmp_monitoring"
  enabled: true
  protocol: "snmp"
  snmp:
    oid:
    - "1.3.6.1.4.1.12356.101.4.1.8.0"    # Session count
    - "1.3.6.1.4.1.12356.101.4.4.2.1.2"  # CPU usage cores
    - "1.3.6.1.4.1.12356.101.4.1.4.0"    # Memory usage
    type:
    - "snmpget"   # Single value
    - "snmpwalk"  # Multiple values
    - "snmpget"   # Single value
  labels:
  - "SessionCount"
  - "CPUUsage"     # Becomes CPUUsage.1, .2, .3, .4
  - "MemoryUsage"
  targets: ["Fortinet_60"]
  schedule:
    frequency: 0
    mode: "interval"
    seconds: 10
  storage: "sqlite"

# SSH Task - Simple command execution
- alias: "get_router_a_version"
  enabled: false
  protocol: "ssh"
  ssh:
    command:
    - "show version"
  targets: ["Router_A"]
  schedule:
    frequency: 1
  storage: "sqlite"
```

### Key Changes in New Configuration Format

#### Protocol-Specific Configuration Structure
- **SSH Tasks**: Use `ssh:` block with `command:` list
- **SNMP Tasks**: Use `snmp:` block with `oid:` and `type:` lists
- **Parse Configuration**: Can be placed in either `ssh:` or `snmp:` blocks

#### Enhanced SNMP Operations
- **Mixed Operations**: Each OID can have its own operation type (snmpget/snmpwalk)
- **Auto-Generated Labels**: snmpwalk operations automatically append suffixes (.1, .2, .3, etc.)
- **One-to-One Mapping**: Number of OIDs must match number of types

#### Backward Compatibility
- The old configuration format is **not supported**
- All configurations must be updated to the new protocol-separated format
- Enhanced validation prevents configuration errors
  targets: ["Router_A"]
  schedule:
    frequency: 1  # Execute only once
  storage: "sqlite"

# SSH Task - Operational command (no result storage)
- alias: "clear_router_a_counters"
  enabled: false
  protocol: "ssh"
  command: 
  - "clear counters"
  targets: ["Router_A"]
  schedule:
    frequency: 1
  storage: null  # No result storage
```

## 📊 Web Interface Features

### Dashboard
- Real-time device status monitoring
- Interactive charts and graphs
- Task execution statistics
- System health indicators

### Task Management
- View all configured tasks
- Monitor task execution status
- Access execution logs and results
- Real-time configuration updates

### Data Visualization
- Time-series charts for numerical data
- Customizable chart colors and styles
- Data export capabilities
- Historical data analysis

### Device Management
- Device connectivity status
- Connection pool statistics
- Protocol-specific information
- Performance metrics

## 🔧 API Documentation

### Health Check
```http
GET /api/healthz
```
Returns system health status.

### Device Information
```http
GET /api/devices
```
Returns list of configured devices.

### Task Information
```http
GET /api/tasks
```
Returns list of configured tasks.

### Chart Data
```http
GET /api/chart_data/{task_alias}
```
Returns chart data for specific task.

## 🐳 Docker Deployment

### Using Docker Compose
```yaml
version: '3.8'
services:
  hwatch:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./log:/app/log
      - ./outfile:/app/outfile
    environment:
      - WEB_USERNAME=admin
      - WEB_PASSWORD=yourpassword
      - LOG_LEVEL=INFO
```

### Advanced Docker Build and Push

For production deployment and multi-platform support, use the optimized build script:

```bash
# Use the enhanced Docker build script
./docker-build.sh
```

#### Build Script Features
- **Multi-platform Support**: Builds for linux/amd64 and linux/arm64
- **Tag Conflict Management**: Handles existing tag conflicts intelligently
- **Automatic Push**: Pushes to remote registry after successful build
- **Build Validation**: Verifies successful deployment
- **Cache Management**: Optional cleanup of build cache

#### Tag Conflict Resolution
When version tags already exist in the remote repository, the script provides three options:

1. **Overwrite Existing Tags**: Force push to replace existing version
2. **Cancel Build**: Abort the build process safely
3. **Use New Version**: Interactively specify a new version number

#### Build Configuration
The build script supports easy configuration modification:

```bash
# Configuration parameters (modify in docker-build.sh)
REGISTRY="registry.cn-hangzhou.aliyuncs.com"
NAMESPACE="apuer"
IMAGE_NAME="hwatch"
VERSION="0.1.1"
PLATFORMS="linux/amd64,linux/arm64"
```

#### Usage Instructions
```bash
# Pull latest version
docker pull registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:latest

# Pull specific version
docker pull registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:0.1.1

# Run container
docker run -d -p 8000:8000 registry.cn-hangzhou.aliyuncs.com/apuer/hwatch:latest
```

### Environment Variables
- `WEB_USERNAME`: Web interface username (default: admin)
- `WEB_PASSWORD`: Web interface password (default: 123456)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## 🔐 Web Account Management

### Default Login Information
- **Username**: `admin`
- **Password**: `123456`

### Custom Account Configuration
Customize login accounts via environment variables:

```bash
# Set custom username and password
export WEB_USERNAME=myuser
export WEB_PASSWORD=mypassword

# Start the application
python app.py
```

### Session Management
- **Session Duration**: 8-hour absolute expiration time
- **Security Tokens**: Uses encrypted secure random tokens
- **Automatic Cleanup**: System automatically cleans expired sessions
- **Browser Closure**: Sessions are automatically cleared when browser is closed
- **Concurrent Login**: Supports multiple users logging in simultaneously

### Security Features
- Password hash storage (using bcrypt)
- Session token encryption
- Automatic logout mechanism
- Session hijacking prevention

## 📋 Log System Configuration

### Log Level Settings

**Priority Order (High to Low):**
1. **Environment Variable `LOG_LEVEL`** (Highest Priority)
2. **Command Line Argument `--level`** (Medium Priority)
3. **Default Value `WARNING`** (Lowest Priority)

### Usage Methods

**Method 1: Environment Variable Setting (Recommended)**
```bash
# Set log level
export LOG_LEVEL=INFO
python app.py

# Supported levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Method 2: Command Line Arguments**
```bash
# Temporarily set log level
python app.py --level DEBUG

# View help information
python app.py --help
```

**Method 3: Combined Usage**
```bash
# Environment variable has higher priority, will ignore command line arguments
export LOG_LEVEL=ERROR
python app.py --level DEBUG  # Actually uses ERROR level
```

### Log Level Description

| Level | Purpose | Output Content |
|-------|---------|----------------|
| `DEBUG` | Development debugging | Detailed debug info, variable values, execution flow |
| `INFO` | General information | App startup, task execution, config loading, etc. |
| `WARNING` | Warning information | Config issues, connection exceptions, retry operations, etc. |
| `ERROR` | Error information | Task failures, connection errors, parsing failures, etc. |
| `CRITICAL` | Critical errors | System crashes, fatal errors, etc. |

### Log File Locations

```
log/
├── app.log          # Main application log (rotated by date)
├── scheduler.log    # Task scheduling log
└── error.log        # Error log (ERROR level and above)
```

### Log Configuration Features

- **Auto Rotation**: Log files automatically rotate by date
- **Size Limit**: Maximum 10MB per log file
- **Retention Policy**: Keep logs for the last 7 days
- **Unified Format**: Timestamp | Level | Module | Message
- **Color Output**: Console output supports color differentiation by level

### Log Usage Recommendations

**Development Environment:**
```bash
export LOG_LEVEL=DEBUG
```

**Production Environment:**
```bash
export LOG_LEVEL=WARNING
```

**Troubleshooting:**
```bash
export LOG_LEVEL=INFO
```

## 📊 Web Interface Usage

### Login Access
1. Access http://localhost:8080 after starting the application
2. Login with default account or custom account
3. Session is valid for 8 hours, re-login required after expiration

### Dashboard Features
- **Real-time Monitoring**: Display execution status of all enabled tasks
- **Data Charts**: Historical data trend visualization
- **Detailed Information**: Hover to view specific values and timestamps
- **Device Status**: Show device connection status and last update time
- **Help Documentation**: Click the help icon (?) in the header to access comprehensive documentation and configuration guides

### Task Management
- **Task List**: View all configured tasks and their status
- **Enable Control**: Dynamically enable/disable tasks
- **Configuration Editing**: Real-time config file editing (restart required for effect)
- **Execution History**: View task execution history and results

### Data Viewing
- **SQLite Data**: View charts and historical trends in web interface
- **File Data**: Raw output saved in `outfile/` directory
- **Real-time Updates**: Data automatically refreshes, no manual refresh needed
- **Export Function**: Support data export to CSV format

## 🔧 Advanced Features

### SSH Connection Pool
System automatically manages SSH connection pool for improved performance:
- **Connection Reuse**: Connections for same tasks and devices are reused
- **Auto Cleanup**: Connections unused for more than 10 minutes are automatically cleaned
- **Health Check**: Connection status is checked before use
- **Concurrency Control**: Maximum 5 concurrent connections per device

### Error Handling Mechanism
- **Auto Retry**: Retry according to configuration when connection fails
- **Exponential Backoff**: Retry intervals use exponential backoff strategy (2^attempt seconds)
- **Timeout Control**: Independent timeout settings for connection and command execution
- **Detailed Logs**: Record all error information for troubleshooting

### Data Storage Strategy
- **SQLite**: Structured data storage, supports chart display and historical queries
- **File**: Raw output storage, convenient for debugging and data auditing
- **Null**: No result storage, suitable for operational commands

### Task Scheduling Mechanism
- **Interval Mode**: Fixed interval execution, next execution calculated based on task start time
- **Delay Mode**: Delayed execution, wait specified time after task completion before next execution
- **Frequency Control**: Support limiting task execution count
- **Smart Incremental Update**: Only refresh changed tasks when config changes, keep other tasks running

### 🔄 Incremental Update Mechanism

#### Working Principle
System intelligently identifies configuration changes through task signatures (MD5 hash) for precise incremental updates:

1. **Task Signature Generation**: Generate MD5 signature for each task's key configuration
2. **Configuration Comparison**: Compare new and old configurations to precisely identify change types
3. **Categorized Processing**: Execute different update strategies based on change types
4. **State Preservation**: Unchanged tasks maintain running state unaffected

#### Change Type Processing

| Change Type | Processing Strategy | Impact Scope |
|-------------|--------------------|--------------|
| **New Tasks** | Directly add to scheduler | New tasks only |
| **Deleted Tasks** | Remove all related jobs and counts | Deleted tasks only |
| **Modified Tasks** | Remove first then re-add | Modified tasks only |
| **Unchanged Tasks** | Keep as is | No impact |

#### Task Signature Includes
- Task basic info: alias, enabled, protocol, targets, storage
- Schedule config: frequency, mode, seconds
- Protocol-specific config: SSH commands, SNMP OID and type
- Parse config: regex, mathematical operations, labels

#### Incremental Update Log Example
```
Configuration changes detected, starting reload...
Starting incremental task scheduling update...
Configuration changes detected: added 1, removed 0, modified 2, unchanged 5
Deleted task: old_task
Updated task: fgSysMemUsage
Updated task: fgProcessorUsage_per
Added task: new_monitoring_task
Incremental update completed! Processed 4 changes
Configuration reload and task incremental update successful!
```

#### Performance Advantages
- **Reduced Interruption**: Running tasks won't be restarted unnecessarily
- **Improved Stability**: Avoid connection rebuilding and data loss from full refresh
- **Resource Saving**: Only process truly changed tasks, reduce system overhead
- **Faster Response**: Incremental updates respond faster than full updates
- **Connection Preservation**: SSH connections in pool are preserved, avoiding reconnection

#### Duplicate Prevention Mechanism
System has comprehensive duplicate processing prevention:
- **File System Events**: Editor saves may trigger multiple file system events
- **Configuration Comparison**: Second detection with no actual changes will skip processing
- **Log Recording**: Clear records of each detection result for debugging

#### Usage Recommendations
1. **Batch Modifications**: Recommend completing multiple config changes at once to reduce frequent updates
2. **Test Verification**: Observe logs after modifications to confirm update results
3. **Backup Configuration**: Backup config files before important changes
4. **Monitor Impact**: Pay attention to task execution status and performance after modifications

## 📝 System Log Files

### Log File Structure
```
log/
├── app.log              # Main application log
├── scheduler.log        # Task scheduling dedicated log
├── error.log           # Error level log
└── debug.log           # Debug level log (DEBUG mode only)

outfile/
├── task_alias_device_name.log    # Task output for file storage mode
└── ...
```

### Log Content Description
- **Application Startup**: System initialization, config loading, service startup info
- **Task Execution**: Execution status, duration, result statistics for each task
- **Connection Management**: SSH/SNMP connection establishment, reuse, cleanup process
- **Error Information**: Connection failures, command execution failures, parsing errors, etc.
- **Performance Metrics**: Task execution time, connection pool status, memory usage, etc.

## 🚨 Important Notes

### Security Considerations
1. **Configuration File Security**: `config.yaml` contains device passwords, please set appropriate file permissions
2. **Network Security**: Ensure monitoring network security to avoid password leakage
3. **Web Access**: Production environment recommends configuring HTTPS and strong passwords
4. **Log Security**: Log files may contain sensitive information, pay attention to access control

### Network Requirements
1. **Connectivity**: Monitoring host must be able to access target device SSH/SNMP ports
2. **Firewall**: Ensure relevant ports (SSH:22, SNMP:161) are open
3. **Bandwidth**: Frequent collection may generate network traffic, pay attention to bandwidth planning
4. **Latency**: Network latency affects task execution time, set reasonable timeout values

### Performance Recommendations
1. **Collection Interval**: Set reasonably based on data change frequency and network conditions
2. **Concurrency Control**: Avoid executing too many tasks simultaneously causing resource competition
3. **Storage Selection**: Use SQLite for frequent queries, file storage for debugging and auditing
4. **Data Cleanup**: Regularly clean historical data to avoid oversized database

### Maintenance Recommendations
1. **Regular Backup**: Backup configuration files and important data
2. **Log Rotation**: System automatically rotates logs, pay attention to disk space
3. **Monitoring Alerts**: Recommend configuring external monitoring system to monitor HWatch running status
4. **Version Updates**: Follow project updates, upgrade promptly to fix security issues

## 🔍 Troubleshooting Guide

### Common Issues and Solutions

#### SSH Connection Issues
**Symptoms**: SSH tasks show connection failure
**Troubleshooting Steps**:
1. Check device IP address and port configuration
2. Verify username and password are correct
3. Test network connectivity: `ping <device_ip>`
4. Manual SSH test: `ssh username@device_ip`
5. Check device SSH service status
6. View detailed error logs

**Common Causes**:
- Network unreachable or firewall blocking
- Authentication information error
- SSH service not started or configuration issues
- Device resource insufficient to establish new connections

#### SNMP Query Issues
**Symptoms**: SNMP tasks no response or return empty values
**Troubleshooting Steps**:
1. Verify SNMP community string configuration
2. Check device SNMP service status
3. Test with snmpwalk tool: `snmpwalk -v2c -c community device_ip oid`
4. Confirm OID is correct and device supported
5. Check if SNMP port is open

#### Data Parsing Issues
**Symptoms**: Regular expression doesn't match or parsing fails
**Troubleshooting Steps**:
1. Set log level to DEBUG to view raw output
2. Use online regex testing tools for verification
3. Ensure capture group count matches labels count
4. Check if multiline matching needs `(?s)` flag
5. Verify mathematical operation expression syntax

#### Web Interface Issues
**Symptoms**: Cannot access web interface or login failure
**Troubleshooting Steps**:
1. Check if application started normally
2. Confirm port 8080 is not occupied
3. Verify login credentials are correct
4. Check browser console error messages
5. View web server errors in application logs

### Debugging Tips

#### Enable Detailed Logging
```bash
export LOG_LEVEL=DEBUG
python app.py
```

#### Single Task Testing
Temporarily disable other tasks, only enable the task needing debugging:
```yaml
- alias: "debug_task"
  enabled: true    # Only enable this task
  # ... other configuration
```

#### Manual Command Testing
Manually execute commands on device to compare output format:
```bash
ssh admin@device_ip "show version"
```

#### Regular Expression Debugging
Use Python interactive environment to test regular expressions:
```python
import re
pattern = r"(?s)BIOS version:\s*(\d+).*?Branch point:\s*(\d+)"
text = "your_device_output_here"
matches = re.search(pattern, text)
print(matches.groups() if matches else "No match")
```

## 📈 Performance Optimization Recommendations

### System Level Optimization
1. **Resource Configuration**: Ensure sufficient CPU and memory resources
2. **Network Optimization**: Use high-speed stable network connections
3. **Storage Optimization**: Use SSD storage to improve database performance
4. **System Tuning**: Adjust operating system network parameters

### Application Level Optimization
1. **Reasonable Intervals**: Avoid overly frequent data collection
2. **Batch Operations**: Execute multiple commands in single SSH session
3. **Connection Reuse**: System automatically manages SSH connection pool
4. **Async Processing**: Tasks execute in parallel for improved efficiency

### Configuration Optimization
1. **Timeout Settings**: Adjust timeout according to network conditions
2. **Retry Strategy**: Set reasonable retry count to avoid resource waste
3. **Storage Selection**: Choose appropriate storage method based on use case
4. **Task Grouping**: Group related tasks for execution to reduce connection overhead

## 💾 Git Workflow and Repository Management

### Dual Repository Push Configuration

This project supports an advanced dual repository push workflow for enhanced backup and deployment flexibility. Use the provided sync script for automated setup:

```bash
# Run the repository synchronization script
./sync2repo.sh
```

#### Push Method Selection
The sync script provides two dual repository push methodologies:

##### Method 1: Separate Remotes (origin + backup)
- **Benefits**: Independent control and flexible management
- **Use Case**: When you need granular control over individual repositories
- **Commands**: 
  ```bash
  git push origin --all && git push origin --tags
  git push backup --all && git push backup --tags
  ```

##### Method 2: Unified 'all' Remote
- **Benefits**: Simplified operations and streamlined workflow
- **Use Case**: When you prefer one-command synchronization
- **Commands**:
  ```bash
  git push all --all && git push all --tags
  ```

#### Branch Configuration
- **Default Branch**: `feature/english`
- **Multi-branch Support**: Pushes all branches and tags simultaneously
- **Branch Protection**: Maintains existing branch structures

#### Repository Synchronization Features
- **Interactive Setup**: Choose between separate or unified push methods
- **Conflict Detection**: Handles existing remote configurations
- **Detailed Feedback**: Individual success/failure status for each repository
- **Error Diagnosis**: Comprehensive troubleshooting information
- **Configuration Validation**: Verifies remote repository accessibility

#### Usage Examples
```bash
# Quick setup with interactive selection
./sync2repo.sh

# View current remote configuration
git remote -v

# Push to all configured repositories (unified method)
git push all --all && git push all --tags

# Push to specific repository (separate method)
git push origin --all
git push backup --all
```

#### Repository Configuration
The script configures the following repository structure:
- **Primary Repository**: GitHub or main code hosting platform
- **Backup Repository**: Secondary repository for redundancy
- **All Remote**: Special remote that pushes to multiple repositories simultaneously

### Branch Management
- **Feature Branch**: `feature/english` serves as the default development branch
- **Hot Reload**: Configuration changes without affecting running tasks
- **Version Control**: Comprehensive commit message standards

## 🤝 Contributing Guidelines

### Development Environment Setup
```bash
# Clone project
git clone <repository-url>
cd hwatch

# Install development dependencies
uv sync --dev

# Run tests
python -m pytest test/

# Code formatting
ruff format .

# Code checking
ruff check .
```

### Submission Standards
- Follow Conventional Commits specification
- Provide detailed commit messages
- Include necessary test cases
- Update relevant documentation

### Issue Reporting
When reporting issues, please provide:
1. Detailed problem description
2. Reproduction steps
3. System environment information
4. Relevant log output
5. Configuration file (after desensitization)

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**HWatch** - Making network device monitoring simple and efficient!

For questions or suggestions, feel free to submit Issues or Pull Requests.

## 🔒 Security Considerations

### Authentication
- Session-based authentication with secure tokens
- Configurable session timeout (default: 2 hours)
- Protection against XSS and CSRF attacks

### Network Security
- SSH connection pooling with automatic cleanup
- SNMP community string protection
- Connection timeout and retry mechanisms

### Data Protection
- SQLite database with proper permissions
- Log file rotation and cleanup
- Sensitive information masking in logs

## 🚀 Performance Optimization

### Connection Pooling
- **SSH Connection Pooling**: SSH connections are pooled and reused based on (task_alias, device_name) keys
- **SNMP Engine Pooling**: SNMP engines are cached and reused based on (device_ip, community) keys
- **Automatic Cleanup**: Inactive SSH connections (10+ minutes) and SNMP engines (5+ minutes) are automatically cleaned
- **Memory Efficiency**: Achieves up to 42.9% memory savings in typical scenarios
- **Connection Reuse**: Same device/community combinations share SNMP engines for optimal performance
- **Health Monitoring**: Connection validity is checked before reuse, with automatic cleanup of invalid connections

### Asynchronous Operations
- Non-blocking task execution
- Concurrent device monitoring
- Efficient resource utilization

### Memory Management
- SQLite for efficient data storage
- Connection pool size limits
- Automatic garbage collection

## 🔧 Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Check device connectivity
ping 192.168.1.100

# Test SSH access
ssh admin@192.168.1.100

# Test SNMP access
snmpget -v2c -c public 192.168.1.100 1.3.6.1.2.1.1.1.0
```

#### Configuration Errors
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Check application logs
tail -f log/app.log
```

#### Performance Issues
```bash
# Monitor resource usage
top -p $(pgrep -f "python app.py")

# Check database size
ls -lh hwatch.db

# Monitor connection pools
curl http://localhost:8080/api/healthz
```

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General operational messages
- **WARNING**: Warning messages for attention
- **ERROR**: Error conditions
- **CRITICAL**: Critical error conditions

## 📈 Monitoring and Maintenance

### Regular Maintenance
1. Monitor log file sizes and rotate as needed
2. Check database growth and optimize if necessary
3. Update device credentials and configurations
4. Review and update task schedules
5. Monitor system resource usage

### Health Monitoring
- Use the built-in health check endpoint
- Monitor application logs for errors
- Set up alerts for critical failures
- Regular backup of configuration and data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Setup
```bash
# Clone and setup development environment
git clone <repository-url>
cd hwatch
uv sync --dev

# Run tests
uv run pytest

# Code formatting
uv run ruff format
uv run ruff check
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation
- Consult the configuration examples

---

*HWatch - Lightweight Network Device Monitoring Made Simple*