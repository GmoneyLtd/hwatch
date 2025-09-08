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

# Import project modules
from core.config_loader import AppConfig
from core.database import get_available_devices, get_available_labels, get_available_tasks, get_chart_data

# from core.monitoring_api import monitoring_router


def _generate_chart_color(index: int) -> str:
    """Generate chart color based on index, supports unlimited number of keys"""
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

    # Use HSL to generate new colors
    hue = (index * 137.5) % 360
    saturation = 70 + (index % 3) * 10
    lightness = 50 + (index % 4) * 10
    return f"hsl({hue}, {saturation}%, {lightness}%)"


def _simplify_oid_key(key: str) -> str:
    """Simplify OID format key display"""
    if "." in key and len(key.split(".")) > 6:
        key_parts = key.split(".")
        return ".".join(key_parts[-2:])
    return key


def _get_background_color(border_color: str) -> str:
    """Get corresponding background color"""
    if border_color.startswith("hsl"):
        return border_color.replace("hsl", "hsla").replace(")", ", 0.2)")
    return border_color + "20"


# --- Global variables and application instance ---

app = FastAPI(title="Hwatch Play")

# Include monitoring API routes
# app.include_router(monitoring_router)


# Add access log middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    logger.info(
        f'{request.client.host} - "{request.method} {request.url.path}" {response.status_code} {process_time:.2f}s'
    )

    return response


# Mount static files directory
static_path = os.path.join(os.path.dirname(__file__), "../views/static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Set template directory
templates_path = os.path.join(os.path.dirname(__file__), "../views/templates")
templates = Jinja2Templates(directory=templates_path)

# Application state machine (later filled by main program app.py)
app_state: dict[str, Any] = {
    "config": None,
    "config_path": None,
    "scheduler": None,  # Scheduler instance
    "reload_callback": None,  # Callback for reloading configuration
}

# --- Authentication ---

# Simple user database - get from environment variables, use defaults if not exist
WEB_USERNAME = os.getenv("WEB_USERNAME", "admin")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "123456")
FAKE_USERS_DB = {WEB_USERNAME: {"password": WEB_PASSWORD}}

# Session storage - store active session tokens and expiration times
ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}

# Session validity period (2 hours)
SESSION_EXPIRE_HOURS = 2


def cleanup_expired_sessions():
    """Clean up expired sessions"""
    current_time = datetime.now()
    expired_tokens = []

    for token, session_data in ACTIVE_SESSIONS.items():
        if current_time > session_data["expires_at"]:
            expired_tokens.append(token)

    for token in expired_tokens:
        del ACTIVE_SESSIONS[token]
        logger.debug(f"Cleaning up expired session: {token[:8]}...")


def get_current_user(request: Request):
    """Get current user, validate session validity"""
    cleanup_expired_sessions()  # Clean up expired sessions

    token = request.cookies.get("session_token")
    if not token:
        return None

    session_data = ACTIVE_SESSIONS.get(token)
    if not session_data:
        return None

    # Check if session has expired
    if datetime.now() > session_data["expires_at"]:
        del ACTIVE_SESSIONS[token]
        logger.info(f"Session has expired: {session_data['username']}")
        return None

    # Update last access time
    session_data["last_access"] = datetime.now()

    return {"username": session_data["username"]}


# Create dependency injection singleton variable
current_user_dependency = Depends(get_current_user)


# --- Web page routes ---


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.tpl", {"request": request})


@app.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    logger.info(f"User login attempt: {username} (IP: {request.client.host})")

    user = FAKE_USERS_DB.get(username)
    if not user or user["password"] != password:
        logger.warning(f"User login failed: {username} (IP: {request.client.host}) - Invalid username or password")
        return templates.TemplateResponse(
            "login.tpl",
            {"request": request, "error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # Generate secure session token
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)

    # Store session information
    ACTIVE_SESSIONS[session_token] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": expires_at,
        "last_access": datetime.now(),
        "ip": request.client.host,
    }

    logger.info(f"User login successful: {username} (IP: {request.client.host}), session valid until: {expires_at}")

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    # Set secure session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,  # Prevent XSS attacks
        secure=False,  # Should be set to True in production (requires HTTPS)
        samesite="lax",  # Prevent CSRF attacks
        max_age=SESSION_EXPIRE_HOURS * 3600,  # Cookie expires after 8 hours
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    user = get_current_user(request)
    username = "Unknown" if not user else user.get("username", "Unknown")

    # Clean up server-side session
    token = request.cookies.get("session_token")
    if token and token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]
        logger.info(f"User logout: {username} (IP: {request.client.host}), session cleaned up")
    else:
        logger.info(f"User logout: {username} (IP: {request.client.host})")

    response = RedirectResponse(url="/login")
    response.delete_cookie("session_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user: dict = current_user_dependency):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("app.tpl", {"request": request})


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """Serve help documentation page with README content.

    This endpoint serves a formatted help page containing the project's README
    documentation, focusing on configuration guide and usage instructions.
    Note: This page is accessible without authentication to help users understand
    the system before logging in.
    """
    import os

    import markdown

    try:
        # Try to read the Chinese README first, fall back to English
        readme_files = [
            os.path.join(os.path.dirname(__file__), "../README_CN.md"),
            os.path.join(os.path.dirname(__file__), "../README.md"),
        ]

        readme_content = ""
        for readme_file in readme_files:
            if os.path.exists(readme_file):
                with open(readme_file, encoding="utf-8") as f:
                    readme_content = f.read()
                    break

        if not readme_content:
            readme_content = "# HWatch Documentation\n\nDocumentation not available."

        # Convert markdown to HTML
        md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"])
        html_content = md.convert(readme_content)

        return templates.TemplateResponse("help.tpl", {"request": request, "readme_content": html_content})

    except Exception as e:
        logger.error(f"Error serving help page: {e}")
        return HTMLResponse(
            content="<h1>Help Documentation</h1><p>Sorry, documentation is temporarily unavailable.</p>",
            status_code=500,
        )


# --- API routes ---


@app.get("/api/healthz")
async def health_check():
    """Health check endpoint for container health probing.

    This endpoint verifies the health of essential application components:
    - Database connectivity
    - Configuration loading
    - Scheduler status

    Returns:
        dict: Health status with details of each component
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {"database": "unknown", "config": "unknown", "scheduler": "unknown"},
    }

    # Check database connectivity
    try:
        from core.database import _get_connection

        conn = await _get_connection()
        # Simple query to verify database is accessible
        async with conn.execute("SELECT 1") as cursor:
            await cursor.fetchone()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)[:100]}"
        health_status["status"] = "unhealthy"

    # Check configuration loading
    try:
        config = app_state.get("config")
        if config and hasattr(config, "devices") and hasattr(config, "tasks"):
            health_status["checks"]["config"] = "healthy"
        else:
            health_status["checks"]["config"] = "unhealthy: configuration not loaded"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["config"] = f"unhealthy: {str(e)[:100]}"
        health_status["status"] = "unhealthy"

    # Check scheduler status
    try:
        scheduler = app_state.get("scheduler")
        if scheduler and hasattr(scheduler, "scheduler") and scheduler.scheduler.running:
            health_status["checks"]["scheduler"] = "healthy"
        else:
            health_status["checks"]["scheduler"] = "unhealthy: scheduler not running"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["scheduler"] = f"unhealthy: {str(e)[:100]}"
        health_status["status"] = "unhealthy"

    # Return appropriate HTTP status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/api/tasks", response_model=list[dict[str, Any]])
async def get_tasks(user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    config: AppConfig = app_state.get("config")
    if not config:
        return []
    # Return data format needed by frontend
    task_list = []
    # Create device mapping for quick lookup
    device_map = {device.name: device for device in config.devices}
    for task in config.tasks:
        # Get IP addresses of task target devices
        target_ips = []
        target_devices = []
        for target_name in task.targets:
            device = device_map.get(target_name)
            if device:
                target_devices.append(device.name)
                target_ips.append(device.ip)

        # Generate protocol-specific type information
        protocol_type = "N/A"
        protocol_details = {}

        if task.protocol == "ssh" and task.ssh:
            protocol_type = "SSH Commands"
            protocol_details = {
                "command_count": len(task.ssh.command),
                "commands": task.ssh.command,
                "has_parse": task.ssh.parse is not None,
            }
        elif task.protocol == "snmp" and task.snmp:
            protocol_type = "SNMP Mixed"
            protocol_details = {
                "oid_count": len(task.snmp.oid),
                "oids": task.snmp.oid,
                "types": task.snmp.type,
                "has_parse": task.snmp.parse is not None,
            }

        task_list.append(
            {
                "alias": task.alias,
                "targets": target_devices,
                "target_ips": target_ips,
                "protocol": task.protocol,
                "type": protocol_type,
                "protocol_details": protocol_details,
                "schedule_mode": task.schedule.mode or "run_once",
                "schedule_seconds": task.schedule.seconds or 0,
                "storage": task.storage or "null",
                "enabled": task.enabled,
            }
        )
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
        logger.error(f"Failed to read configuration file: {e}")
        raise HTTPException(
            status_code=500, detail="Unable to read configuration file"
        ) from None  # Don't preserve original exception chain to avoid confusion


@app.post("/api/config")
async def save_config(request: Request, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")
    logger.info(f"User {username} started updating configuration file")

    content = await request.body()
    content = content.decode("utf-8")
    config_path = app_state.get("config_path")

    # Validate YAML format
    try:
        yaml.safe_load(content)
        logger.debug("Configuration file YAML format validation passed")
    except yaml.YAMLError as e:
        logger.error(f"User {username} provided configuration file YAML format error: {e}")
        raise HTTPException(status_code=400, detail=f"YAML format error: {e}") from None

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Configuration file {config_path} has been updated online by user {username}.")
        # After file is saved, watchdog will automatically trigger reload logic
        return {"message": "Configuration saved successfully!"}
    except Exception as e:
        logger.error(f"User {username} failed to update configuration file: {e}")
        raise HTTPException(status_code=500, detail="Unable to write configuration file") from None


@app.get("/api/chart")
async def get_chart_data_api(
    task_alias: str | None = None,
    start: str | None = None,
    end: str | None = None,
    devices: str | None = None,
    label: str | None = None,
    user: dict = current_user_dependency,
):
    if not user:
        raise HTTPException(status_code=401)

    # Parse time parameters, use default time range (last 2 hours) if not provided
    if start and end:
        try:
            start_date = datetime.fromisoformat(start)
            end_date = datetime.fromisoformat(end)
        except ValueError:
            # If time format is invalid, use default time range (last 2 hours)
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=2)
    else:
        # Default time range: last 2 hours
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=2)

    # Get task list - based on tasks that actually have data in specified time range
    tasks = await get_available_tasks(start_date, end_date)

    # Parse selected devices
    selected_devices = devices.split(",") if devices else []

    # Situation 1: Only task selected, return labels and devices
    if task_alias and not label:
        available_labels = await get_available_labels(task_alias, start_date, end_date)
        available_devices = await get_available_devices(start_date, end_date, task_alias)

        return {
            "labels": available_labels,
            "tasks": tasks,  # 返回完整的tasks列表
            "available_devices": available_devices,
            "selected_devices": selected_devices,
            "datasets": [],
        }

    # Situation 2: Task and label selected, but no devices, return device list
    if task_alias and label and not selected_devices:
        available_devices = await get_available_devices(start_date, end_date, task_alias)
        available_labels = await get_available_labels(task_alias, start_date, end_date)

        return {
            "labels": available_labels,  # 返回完整的labels列表
            "tasks": tasks,  # 返回完整的tasks列表
            "available_devices": available_devices,
            "selected_devices": [],
            "datasets": [],
        }

    # Build basic response data for backward compatibility
    if task_alias:
        available_devices = await get_available_devices(start_date, end_date, task_alias)
        available_labels = await get_available_labels(task_alias, start_date, end_date)
    else:
        available_devices = []
        available_labels = []

    response_data = {
        "tasks": tasks,
        "labels": available_labels,
        "available_devices": available_devices,
        "selected_devices": selected_devices,
        "datasets": [],
    }

    # Situation 3: Complete selection (task, label, devices), return chart data
    if task_alias and label and selected_devices and start and end:
        # Get raw data
        raw_data = await get_chart_data(task_alias, start_date, end_date)

        # Filter data: only keep data matching the selected label
        filtered_data = []
        for item in raw_data:
            key = item["key"]
            # Check if key matches the selected label
            if key == label or (key.startswith(label + ".") and key.split(".")[-1].isdigit()):
                if item["device_name"] in selected_devices:
                    filtered_data.append(item)

        # Process filtered data using existing logic
        datasets = []
        if filtered_data:
            # Group data by device and key combination
            series_data = {}
            for row in filtered_data:
                device = row["device_name"]
                key = row["key"]

                # Create unique series identifier: device_key
                series_key = f"{device}_{key}"

                if series_key not in series_data:
                    series_data[series_key] = {"device": device, "key": key, "data": []}

                # Parse numeric value, handle various possible data formats
                value = row["value"]
                numeric_value = 0.0

                if value is not None:
                    try:
                        # Try direct conversion to float
                        numeric_value = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, try cleaning string then converting
                        try:
                            cleaned_value = str(value).strip().replace(",", "")
                            if cleaned_value and cleaned_value.replace(".", "").replace("-", "").isdigit():
                                numeric_value = float(cleaned_value)
                        except (ValueError, TypeError):
                            numeric_value = 0.0

                # Convert timestamp to seconds precision by removing microseconds
                timestamp = row["timestamp"]
                if isinstance(timestamp, str):
                    # Parse datetime string and truncate to seconds
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        timestamp_seconds = dt.replace(microsecond=0).isoformat()
                    except ValueError:
                        timestamp_seconds = timestamp
                else:
                    # If it's already a datetime object, truncate microseconds
                    timestamp_seconds = timestamp.replace(microsecond=0).isoformat()

                series_data[series_key]["data"].append({"x": timestamp_seconds, "y": numeric_value})

            # Create dataset for each device-key combination
            sorted_series = sorted(series_data.items(), key=lambda x: (x[1]["device"], x[1]["key"]))

            for color_index, (_, series_info) in enumerate(sorted_series):
                # Generate label
                chart_label = f"{series_info['device']} - {series_info['key']}"

                # Generate color
                border_color = _generate_chart_color(color_index)
                background_color = _get_background_color(border_color)

                datasets.append(
                    {
                        "label": chart_label,
                        "data": series_info["data"],
                        "borderColor": border_color,
                        "backgroundColor": background_color,
                        "fill": False,
                        "tension": 0.1,
                    }
                )

        response_data["datasets"] = datasets
        # 确保返回完整的labels列表, 而不是只返回当前选中的label
        available_labels = await get_available_labels(task_alias, start_date, end_date)
        response_data["labels"] = available_labels
        return response_data

    # Original logic for backward compatibility: Only query chart data when task, devices and time are selected
    if task_alias and selected_devices and start and end and not label:
        # Get raw data
        raw_data = await get_chart_data(task_alias, start_date, end_date)

        # Convert to Chart.js format
        datasets = []
        if raw_data:
            # Group data by device and key combination
            series_data = {}
            for row in raw_data:
                device = row["device_name"]
                key = row["key"]

                if device not in selected_devices:
                    continue

                # Create unique series identifier: device_key
                series_key = f"{device}_{key}"

                if series_key not in series_data:
                    series_data[series_key] = {"device": device, "key": key, "data": []}

                # Parse numeric value, handle various possible data formats
                value = row["value"]
                numeric_value = 0.0

                if value is not None:
                    try:
                        # Try direct conversion to float
                        numeric_value = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, try cleaning string then converting
                        try:
                            cleaned_value = str(value).strip().replace(",", "")
                            if cleaned_value and cleaned_value.replace(".", "").replace("-", "").isdigit():
                                numeric_value = float(cleaned_value)
                        except (ValueError, TypeError):
                            numeric_value = 0.0

                # Convert timestamp to seconds precision by removing microseconds
                timestamp = row["timestamp"]
                if isinstance(timestamp, str):
                    # Parse datetime string and truncate to seconds
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        timestamp_seconds = dt.replace(microsecond=0).isoformat()
                    except ValueError:
                        timestamp_seconds = timestamp
                else:
                    # If it's already a datetime object, truncate microseconds
                    timestamp_seconds = timestamp.replace(microsecond=0).isoformat()

                series_data[series_key]["data"].append({"x": timestamp_seconds, "y": numeric_value})

            # Create dataset for each device-key combination
            sorted_series = sorted(series_data.items(), key=lambda x: (x[1]["device"], x[1]["key"]))

            for color_index, (_, series_info) in enumerate(sorted_series):
                # device_keys = [k for k, v in series_data.items() if v["device"] == series_info["device"]]

                # Generate label
                # if len(device_keys) == 1:
                #     label = f"{series_info['key']}"
                # else:
                label = f"{series_info['device']} - {series_info['key']}"

                # Generate color
                border_color = _generate_chart_color(color_index)
                background_color = _get_background_color(border_color)

                datasets.append(
                    {
                        "label": label,
                        "data": series_info["data"],
                        "borderColor": border_color,
                        "backgroundColor": background_color,
                        "fill": False,
                        "tension": 0.1,
                    }
                )

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
            file_list.append({"name": f, "size": stat.st_size, "created_at": stat.st_mtime})
    return sorted(file_list, key=lambda x: x["created_at"], reverse=True)


@app.get("/outfile/{filename}")
async def download_outfile(filename: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")

    # Prevent path traversal attacks
    if ".." in filename or filename.startswith("/"):
        logger.warning(f"User {username} attempted to download illegal file path: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join("outfile", filename)

    if not os.path.exists(file_path):
        logger.warning(f"User {username} attempted to download non-existent file: {filename}")
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.isfile(file_path):
        logger.warning(f"User {username} attempted to download path that is not a file: {filename}")
        raise HTTPException(status_code=400, detail="Path is not a file")

    logger.info(f"User {username} downloaded file: {filename}")
    return FileResponse(file_path, filename=filename)


@app.post("/api/tasks/{task_alias}/toggle")
async def toggle_task_enabled(task_alias: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)
    logger.warning(f"Received request to toggle task {task_alias} status, but scheduler logic not implemented yet.")
    # TODO: Implement logic to interact with scheduler
    # 1. Modify configuration status in memory
    # 2. Notify scheduler to remove or add corresponding jobs
    # 3. May need to rewrite configuration file to persist status
    return {"status": "pending", "message": "Scheduler logic not implemented"}


@app.post("/api/tasks/{action}/{device}/{task_alias}")
async def handle_task_action(action: str, device: str, task_alias: str, user: dict = current_user_dependency):
    if not user:
        raise HTTPException(status_code=401)

    username = user.get("username", "Unknown")
    logger.info(f"User {username} attempted to perform action '{action}' on task '{task_alias}' on device '{device}'")

    if action not in ["enable", "disable"]:
        logger.warning(f"User {username} performed invalid action on task '{task_alias}': {action}")
        raise HTTPException(status_code=400, detail="Invalid action, only 'enable' or 'disable' supported")

    config: AppConfig = app_state.get("config")
    if not config:
        logger.error(f"User {username} failed to operate task '{task_alias}': system configuration not loaded")
        raise HTTPException(status_code=500, detail="Configuration not loaded")

    # Find corresponding task
    task = None
    for t in config.tasks:
        if t.alias == task_alias:
            task = t
            break

    if not task:
        logger.warning(f"User {username} attempted to operate non-existent task: {task_alias}")
        raise HTTPException(status_code=404, detail=f"Task {task_alias} not found")

    # Check if task targets specified device
    if device not in task.targets:
        logger.warning(
            f"User {username} attempted to operate task '{task_alias}' on device '{device}', but task does not target that device"
        )
        raise HTTPException(status_code=400, detail=f"Task {task_alias} does not target device {device}")

    # Get configuration file path
    config_path = app_state.get("config_path")
    if not config_path:
        logger.error(f"User {username} failed to operate task '{task_alias}': configuration file path not set")
        raise HTTPException(status_code=500, detail="Configuration file path not set")

    # Read original configuration file content
    try:
        with open(config_path, encoding="utf-8") as f:
            config_content = f.read()

        # Parse YAML configuration
        config_data = yaml.safe_load(config_content)
        logger.debug(f"User {username} successfully read configuration file content")
    except Exception as e:
        logger.error(f"User {username} failed to operate task '{task_alias}': failed to read configuration file - {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read configuration file: {e}") from None

    # Find and update corresponding task's enabled status
    task_found = False
    for t in config_data.get("tasks", []):
        if t.get("alias") == task_alias:
            old_status = t.get("enabled", False)
            new_status = action == "enable"
            t["enabled"] = new_status
            task_found = True
            logger.info(f"User {username} updated task '{task_alias}' status from {old_status} to {new_status}")
            break

    if not task_found:
        logger.warning(f"User {username} attempted to operate task '{task_alias}' not found in configuration file")
        raise HTTPException(status_code=404, detail=f"Task {task_alias} not found in configuration file")

    # Write updated configuration back to file
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        logger.info(f"User {username} successfully updated configuration file {config_path}")
    except Exception as e:
        logger.error(f"User {username} failed to update configuration file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write configuration file: {e}") from None

    # Since configuration file has been updated, watch module will automatically detect changes and reload configuration and tasks
    logger.info(
        f"User {username} operation '{action}' on task '{task_alias}' on device '{device}' completed, waiting for configuration reload..."
    )
    return {
        "status": "success",
        "message": f"Task {task_alias} has been {action}ed, configuration will be automatically updated in background",
    }


# Note: The following are stubs for APIs that need scheduler implementation
