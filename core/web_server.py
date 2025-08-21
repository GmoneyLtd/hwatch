import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Any

import yaml
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

# 导入项目模块
from core.config_loader import AppConfig, load_config
from core.database import get_available_devices, get_available_tasks, get_chart_data


def _generate_chart_color(index: int) -> str:
    """基于索引生成图表颜色, 支持无限数量的key"""
    base_colors = [
        "#FF6384",
        "#36A2EB",
        "#FFCE56",
        "#4BC0C0",
        "#9966FF",
        "#FF9F40",
        "#C9CBCF",
        "#FF9F40",
        "#4BC0C0",
        "#FF6384",
        "#36A2EB",
        "#FFCE56",
    ]

    if index < len(base_colors):
        return base_colors[index]

    # 使用HSL生成新颜色
    hue = (index * 137.5) % 360
    saturation = 70 + (index % 3) * 10
    lightness = 50 + (index % 4) * 10
    return f"hsl({hue}, {saturation}%, {lightness}%)"


def _simplify_oid_key(key: str) -> str:
    """简化OID格式的key显示"""
    if "." in key and len(key.split(".")) > 6:
        key_parts = key.split(".")
        return ".".join(key_parts[-2:])
    return key


def _get_background_color(border_color: str) -> str:
    """获取对应的背景颜色"""
    if border_color.startswith("hsl"):
        return border_color.replace("hsl", "hsla").replace(")", ", 0.2)")
    return border_color + "20"


# --- 全局变量与应用实例 ---

app = FastAPI(title="Hwatch")


# 添加访问日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f'{request.client.host} - "{request.method} {request.url.path}" {response.status_code} {process_time:.2f}s'
    )

    return response


# 挂载静态文件目录
static_path = os.path.join(os.path.dirname(__file__), "../views/static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 设置模板目录
templates_path = os.path.join(os.path.dirname(__file__), "../views/templates")
templates = Jinja2Templates(directory=templates_path)

# 应用状态机 (后续由主程序 app.py 填充)
app_state: dict[str, Any] = {
    "config": None,
    "config_path": None,
    "scheduler": None,  # 调度器实例
    "reload_callback": None,  # 重新加载配置的回调
}

# --- 认证 ---

# 简单的用户数据库 - 从环境变量获取, 如果不存在则使用默认值
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "123456")
FAKE_USERS_DB = {WEB_USERNAME: {"password": WEB_PASSWORD}}

# 会话存储 - 存储活跃的会话token和过期时间
ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}

# 会话有效期（8小时）
SESSION_EXPIRE_HOURS = 8


def cleanup_expired_sessions():
    """清理过期的会话"""
    current_time = datetime.now()
    expired_tokens = []

    for token, session_data in ACTIVE_SESSIONS.items():
        if current_time > session_data["expires_at"]:
            expired_tokens.append(token)

    for token in expired_tokens:
        del ACTIVE_SESSIONS[token]
        logger.debug(f"清理过期会话: {token[:8]}...")


def get_current_user(request: Request):
    """获取当前用户，验证会话有效性"""
    cleanup_expired_sessions()  # 清理过期会话

    token = request.cookies.get("session_token")
    if not token:
        return None

    session_data = ACTIVE_SESSIONS.get(token)
    if not session_data:
        return None

    # 检查会话是否过期
    if datetime.now() > session_data["expires_at"]:
        del ACTIVE_SESSIONS[token]
        logger.info(f"会话已过期: {session_data['username']}")
        return None

    # 更新最后访问时间
    session_data["last_access"] = datetime.now()

    return {"username": session_data["username"]}


# 创建依赖注入单例变量
current_user_dependency = Depends(get_current_user)


# --- Web 页面路由 ---


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.tpl", {"request": request})


@app.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    logger.info(f"用户尝试登录: {username} (IP: {request.client.host})")

    user = FAKE_USERS_DB.get(username)
    if not user or user["password"] != password:
        logger.warning(f"用户登录失败: {username} (IP: {request.client.host}) - 用户名或密码错误")
        return templates.TemplateResponse(
            "login.tpl",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # 生成安全的会话token
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)

    # 存储会话信息
    ACTIVE_SESSIONS[session_token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "last_access": datetime.now(),
        "ip": request.client.host,
    }

    logger.info(f"用户登录成功: {username} (IP: {request.client.host}), 会话有效期至: {expires_at}")

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    # 设置安全的会话cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,  # 防止XSS攻击
        secure=False,  # 在生产环境中应设为True（需要HTTPS）
        samesite="lax",  # 防止CSRF攻击
        max_age=SESSION_EXPIRE_HOURS * 3600,  # 8小时后cookie过期
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    user = get_current_user(request)
    username = "Unknown" if not user else user.get("username", "Unknown")

    # 清理服务器端会话
    token = request.cookies.get("session_token")
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
        logger.info(f"用户登出: {username} (IP: {request.client.host}), 会话已清理")
    else:
        logger.info(f"用户登出: {username} (IP: {request.client.host})")

    response = RedirectResponse(url="/login")
    response.delete_cookie("session_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user: dict = current_user_dependency):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("app.tpl", {"request": request})


# --- API 路由 ---


@app.get("/api/tasks", response_model=list[dict[str, Any]])
async def get_tasks(user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    config: AppConfig = app_state.get("config")
    if not config:
        return []
    # 返回前端需要的数据格式
    task_list = []
    # 创建设备映射以便快速查找
    device_map = {device.name: device for device in config.devices}
    for task in config.tasks:
        # 获取任务目标设备的IP地址
        target_ips = []
        target_devices = []
        for target_name in task.targets:
            device = device_map.get(target_name)
            if device:
                target_devices.append(device.name)
                target_ips.append(device.ip)

        task_list.append({
            "alias": task.alias,
            "targets": target_devices,
            "target_ips": target_ips,
            "protocol": task.protocol,
            "type": task.type or "N/A",
            "schedule_mode": task.schedule.mode or "run_once",
            "schedule_seconds": task.schedule.seconds or 0,
            "enabled": task.enabled,
        })
    return task_list


@app.get("/api/config")
async def get_config(user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    config_path = app_state.get("config_path")
    try:
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
        return Response(content=content, media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        raise HTTPException(status_code=500, detail="无法读取配置文件") from None  # 不保留原始异常链, 避免混淆


@app.post("/api/config")
async def save_config(request: Request, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")
    logger.info(f"用户 {username} 开始更新配置文件")

    content = await request.body()
    content = content.decode("utf-8")
    config_path = app_state.get("config_path")

    # 验证YAML格式
    try:
        yaml.safe_load(content)
        logger.debug("配置文件 YAML 格式验证通过")
    except yaml.YAMLError as e:
        logger.error(f"用户 {username} 提供的配置文件 YAML 格式错误: {e}")
        raise HTTPException(status_code=400, detail=f"YAML格式错误: {e}") from None

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"配置文件 {config_path} 已被用户 {username} 在线更新。")
        # 文件保存后,watchdog会自动触发重载逻辑
        return {"message": "配置保存成功! "}
    except Exception as e:
        logger.error(f"用户 {username} 更新配置文件失败: {e}")
        raise HTTPException(status_code=500, detail="无法写入配置文件") from None


@app.get("/api/chart")
async def get_chart_data_api(
    task_alias: str | None = None,
    start: str | None = None,
    end: str | None = None,
    devices: str | None = None,
    user: dict = current_user_dependency,
):
    if not user:
        raise HTTPException(status_code=401)

    # 解析时间参数, 如果没有提供则使用默认时间范围(最近2小时)
    if start and end:
        try:
            start_date = datetime.fromisoformat(start)
            end_date = datetime.fromisoformat(end)
        except ValueError:
            # 如果时间格式无效, 使用默认时间范围(最近2小时)
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=2)
    else:
        # 默认时间范围: 最近2小时
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=2)

    # 获取任务列表 - 基于指定时间区间内实际存在数据的任务
    tasks = await get_available_tasks(start_date, end_date)

    # 获取设备列表的逻辑:
    # 1. 如果没有选择任务, 设备列表为空
    # 2. 如果选择了任务, 获取该任务在指定时间区间内的设备列表
    if task_alias:
        available_devices = await get_available_devices(start_date, end_date, task_alias)
    else:
        available_devices = []

    # 解析选中的设备
    selected_devices = devices.split(",") if devices else []

    # 构建基础响应数据
    response_data = {
        "tasks": tasks,
        "available_devices": available_devices,
        "selected_devices": selected_devices,
        "datasets": [],
    }

    # 只有当选择了任务、设备和时间时, 才查询图表数据
    if task_alias and selected_devices and start and end:
        # 获取原始数据
        raw_data = await get_chart_data(task_alias, start_date, end_date)

        # 转换为 Chart.js 格式
        datasets = []
        if raw_data:
            # 按设备和key组合分组数据
            series_data = {}
            for row in raw_data:
                device = row["device_name"]
                key = row["key"]

                if device not in selected_devices:
                    continue

                # 创建唯一的系列标识符: device_key
                series_key = f"{device}_{key}"

                if series_key not in series_data:
                    series_data[series_key] = {"device": device, "key": key, "data": []}

                # 解析数值, 处理各种可能的数据格式
                value = row["value"]
                numeric_value = 0.0

                if value is not None:
                    try:
                        # 尝试直接转换为浮点数
                        numeric_value = float(value)
                    except (ValueError, TypeError):
                        # 如果转换失败, 尝试清理字符串后再转换
                        try:
                            cleaned_value = str(value).strip().replace(",", "")
                            if cleaned_value and cleaned_value.replace(".", "").replace("-", "").isdigit():
                                numeric_value = float(cleaned_value)
                        except (ValueError, TypeError):
                            numeric_value = 0.0

                series_data[series_key]["data"].append({"x": row["timestamp"], "y": numeric_value})

            # 为每个设备-key组合创建数据集
            sorted_series = sorted(series_data.items(), key=lambda x: (x[1]["device"], x[1]["key"]))

            for color_index, (_, series_info) in enumerate(sorted_series):
                # device_keys = [k for k, v in series_data.items() if v["device"] == series_info["device"]]

                # 生成标签
                # if len(device_keys) == 1:
                #     label = f"{series_info['key']}"
                # else:
                label = f"{series_info['device']} - {series_info['key']}"

                # 生成颜色
                border_color = _generate_chart_color(color_index)
                background_color = _get_background_color(border_color)

                datasets.append({
                    "label": label,
                    "data": series_info["data"],
                    "borderColor": border_color,
                    "backgroundColor": background_color,
                    "fill": False,
                    "tension": 0.1,
                })

        response_data["datasets"] = datasets

    return response_data


@app.get("/api/outfiles")
async def list_outfiles(user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    outfile_dir = "outfile"
    if not os.path.exists(outfile_dir):
        return []
    files = os.listdir(outfile_dir)
    file_list = []
    for f in files:
        file_path = os.path.join(outfile_dir, f)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            file_list.append({"name": f, "size": stat.st_size, "created_at": stat.st_ctime})
    return sorted(file_list, key=lambda x: x["created_at"], reverse=True)


@app.get("/outfile/{filename}")
async def download_outfile(filename: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")

    # 防止路径遍历攻击
    if ".." in filename or filename.startswith("/"):
        logger.warning(f"用户 {username} 尝试下载非法文件路径: {filename}")
        raise HTTPException(status_code=400, detail="无效的文件名")

    file_path = os.path.join("outfile", filename)

    if not os.path.exists(file_path):
        logger.warning(f"用户 {username} 尝试下载不存在的文件: {filename}")
        raise HTTPException(status_code=404, detail="文件未找到")

    if not os.path.isfile(file_path):
        logger.warning(f"用户 {username} 尝试下载的路径不是文件: {filename}")
        raise HTTPException(status_code=400, detail="路径不是文件")

    logger.info(f"用户 {username} 下载文件: {filename}")
    return FileResponse(file_path, filename=filename)


@app.post("/api/tasks/{task_alias}/toggle")
async def toggle_task_enabled(task_alias: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    logger.warning(f"收到切换任务 {task_alias} 状态的请求,但调度器逻辑尚未实现。")
    # TODO: 实现与调度器交互的逻辑
    # 1. 修改内存中的配置状态
    # 2. 通知调度器移除或添加相应的job
    # 3. 可能需要重写配置文件以持久化状态
    return {"status": "pending", "message": "调度器逻辑未实现"}


@app.post("/api/tasks/{action}/{device}/{task_alias}")
async def handle_task_action(action: str, device: str, task_alias: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")
    logger.info(f"用户 {username} 尝试对任务 '{task_alias}' 在设备 '{device}' 上执行操作 '{action}'")

    if action not in ["enable", "disable"]:
        logger.warning(f"用户 {username} 对任务 '{task_alias}' 执行了无效操作: {action}")
        raise HTTPException(status_code=400, detail="无效的操作,仅支持 'enable' 或 'disable'")

    config: AppConfig = app_state.get("config")
    if not config:
        logger.error(f"用户 {username} 操作任务 '{task_alias}' 失败: 系统配置未加载")
        raise HTTPException(status_code=500, detail="配置未加载")

    # 查找对应的任务
    task = None
    for t in config.tasks:
        if t.alias == task_alias:
            task = t
            break

    if not task:
        logger.warning(f"用户 {username} 尝试操作不存在的任务: {task_alias}")
        raise HTTPException(status_code=404, detail=f"任务 {task_alias} 未找到")

    # 检查任务是否针对指定设备
    if device not in task.targets:
        logger.warning(f"用户 {username} 尝试在设备 '{device}' 上操作任务 '{task_alias}',但任务不针对该设备")
        raise HTTPException(status_code=400, detail=f"任务 {task_alias} 不针对设备 {device}")

    # 获取配置文件路径
    config_path = app_state.get("config_path")
    if not config_path:
        logger.error(f"用户 {username} 操作任务 '{task_alias}' 失败: 配置文件路径未设置")
        raise HTTPException(status_code=500, detail="配置文件路径未设置")

    # 读取原始配置文件内容
    try:
        with open(config_path, encoding="utf-8") as f:
            config_content = f.read()

        # 解析YAML配置
        config_data = yaml.safe_load(config_content)
        logger.debug(f"用户 {username} 成功读取配置文件内容")
    except Exception as e:
        logger.error(f"用户 {username} 操作任务 '{task_alias}' 失败: 读取配置文件失败 - {e}")
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {e}") from None

    # 查找并更新对应任务的启用状态
    task_found = False
    for t in config_data.get("tasks", []):
        if t.get("alias") == task_alias:
            old_status = t.get("enabled", False)
            new_status = action == "enable"
            t["enabled"] = new_status
            task_found = True
            logger.info(f"用户 {username} 将任务 '{task_alias}' 状态从 {old_status} 更新为 {new_status}")
            break

    if not task_found:
        logger.warning(f"用户 {username} 尝试操作的任务 '{task_alias}' 在配置文件中未找到")
        raise HTTPException(status_code=404, detail=f"任务 {task_alias} 在配置文件中未找到")

    # 将更新后的配置写回文件
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        logger.info(f"用户 {username} 成功更新配置文件 {config_path}")
    except Exception as e:
        logger.error(f"用户 {username} 更新配置文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"写入配置文件失败: {e}") from None

    # 由于配置文件已更新,watch模块会自动检测到变更并重新加载配置和任务
    logger.info(f"用户 {username} 对任务 '{task_alias}' 在设备 '{device}' 上的操作 '{action}' 完成,等待配置重载...")
    return {"status": "success", "message": f"任务 {task_alias} 已{action},配置将在后台自动更新"}


# 注意: 以下是需要调度器实现的API的存根 (stub)
