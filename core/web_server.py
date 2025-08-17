
import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from typing import Dict, Any, List
from datetime import datetime, timedelta
import yaml

# 导入项目模块
from core.config_loader import AppConfig, load_config
from core.database import get_chart_data

# --- 全局变量与应用实例 ---

app = FastAPI(title="Hwatch")

# 挂载静态文件目录
static_path = os.path.join(os.path.dirname(__file__), '../views/static')
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 设置模板目录
templates_path = os.path.join(os.path.dirname(__file__), '../views/templates')
templates = Jinja2Templates(directory=templates_path)

# 应用状态机 (后续由主程序 app.py 填充)
app_state: Dict[str, Any] = {
    "config": None,
    "config_path": None,
    "scheduler": None, # 调度器实例
    "reload_callback": None, # 重新加载配置的回调
}

# --- 认证 ---

# 简单的用户数据库
FAKE_USERS_DB = {"admin": {"password": "admin"}}

async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if token and token in FAKE_USERS_DB: # 在实际应用中，这里应该是验证token的有效性
        return FAKE_USERS_DB[token]
    return None

# --- Web 页面路由 ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.tpl", {"request": request})

@app.post("/login")
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = FAKE_USERS_DB.get(username)
    if not user or user["password"] != password:
        return templates.TemplateResponse(
            "login.tpl",
            {"request": request, "error": "无效的用户名或密码"},
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    # 在实际应用中，应使用安全的会话管理
    response.set_cookie(key="session_token", value=username, httponly=True)
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login")
    response.delete_cookie("session_token")
    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("app.tpl", {"request": request})

# --- API 路由 ---

@app.get("/api/tasks", response_model=List[Dict[str, Any]])
async def get_tasks(user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    config: AppConfig = app_state.get("config")
    if not config:
        return []
    # 返回前端需要的数据格式
    task_list = []
    for task in config.tasks:
        task_list.append({
            "alias": task.alias,
            "targets": task.targets,
            "protocol": task.protocol,
            "type": task.type or 'N/A',
            "schedule_mode": task.schedule.mode or 'run_once',
            "schedule_seconds": task.schedule.seconds or 0,
            "enabled": task.enabled
        })
    return task_list

@app.get("/api/config")
async def get_config(user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    config_path = app_state.get("config_path")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        raise HTTPException(status_code=500, detail="无法读取配置文件")

@app.post("/api/config")
async def save_config(request: Request, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    data = await request.json()
    content = data.get('content')
    config_path = app_state.get("config_path")
    
    # 验证YAML格式
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML格式错误: {e}")

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"配置文件 {config_path} 已被用户 {user} 在线更新。")
        # 文件保存后，watchdog会自动触发重载逻辑
        return {"message": "配置保存成功！"}
    except Exception as e:
        logger.error(f"写入配置文件失败: {e}")
        raise HTTPException(status_code=500, detail="无法写入配置文件")

@app.get("/api/chart_data")
async def get_chart_data_api(task_alias: str, start: str, end: str, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    try:
        start_date = datetime.fromisoformat(start)
        end_date = datetime.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，请使用ISO格式。")
    
    data = await get_chart_data(task_alias, start_date, end_date)
    return data

@app.get("/api/outfiles")
async def list_outfiles(user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    outfile_dir = "outfile"
    if not os.path.exists(outfile_dir):
        return []
    files = os.listdir(outfile_dir)
    file_list = []
    for f in files:
        file_path = os.path.join(outfile_dir, f)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            file_list.append({
                "name": f,
                "size": stat.st_size,
                "created_at": stat.st_ctime
            })
    return sorted(file_list, key=lambda x: x["created_at"], reverse=True)

@app.get("/outfile/{filename}")
async def download_outfile(filename: str, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    
    # 防止路径遍历攻击
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    file_path = os.path.join("outfile", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件未找到")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    return FileResponse(file_path, filename=filename)

# 注意：以下是需要调度器实现的API的存根 (stub)

@app.post("/api/tasks/{task_alias}/toggle")
async def toggle_task_enabled(task_alias: str, user: dict = Depends(get_current_user)):
    if not user: raise HTTPException(status_code=401)
    logger.warning(f"收到切换任务 {task_alias} 状态的请求，但调度器逻辑尚未实现。")
    # TODO: 实现与调度器交互的逻辑
    # 1. 修改内存中的配置状态
    # 2. 通知调度器移除或添加相应的job
    # 3. 可能需要重写配置文件以持久化状态
    return {"status": "pending", "message": "调度器逻辑未实现"}

