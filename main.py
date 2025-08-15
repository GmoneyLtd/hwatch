from fastapi import FastAPI, Request, Query, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import json
import random
import os

app = FastAPI()

OUTFILE_DIR = "outfile"

# Create outfile directory if it doesn't exist
os.makedirs(OUTFILE_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="views/static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="views/templates")

# In-memory data store (from app.py)
tasks = [
    ["device1", "alias1", "192.168.1.1", "type1", "10s", "2024-01-01", True],
    ["device2", "alias2", "192.168.1.2", "type2", "20s", "2024-01-02", False],
    ["device3", "alias3", "192.168.1.3", "type1", "30s", "2024-01-03", True],
    ["device4", "alias4", "192.168.1.4", "type3", "15s", "2024-01-04", True],
]

# Routes (from app.py)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("app.tpl", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.tpl", {"request": request})

@app.get("/api/data")
async def api_data():
    return {"message": "Hello from FastAPI!", "timestamp": datetime.now().isoformat()}

@app.get("/api/tasks")
async def api_tasks():
    return JSONResponse(content=tasks)

@app.post("/api/tasks/{action}/{device}/{alias}")
async def api_task_action(action: str, device: str, alias: str):
    global tasks
    found = False
    for task in tasks:
        if task[0] == device and task[1] == alias:
            found = True
            if action == 'enable':
                task[6] = True
            elif action == 'disable':
                task[6] = False
            break
    if not found:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success"}

@app.get("/api/chart")
async def api_chart(
    start: str = Query(None),
    end: str = Query(None),
    task_alias: str = Query(None),
    devices_param: str = Query(None)
):
    # Handle devices_param, supporting comma-separated list
    selected_devices = []
    if devices_param:
        selected_devices = [d.strip() for d in devices_param.split(',')]

    # Define task and device mapping (from app.py)
    task_device_mapping = {
        "CPU监控": ["device1", "device2", "device3"],
        "内存监控": ["device2", "device4"],
        "网络监控": ["device1", "device3", "device4"],
        "磁盘IO": ["device1", "device2", "device3", "device4"]
    }

    # If no time range provided, default to last 2 hours
    start_time_dt = None
    end_time_dt = None
    if not start or not end:
        end_time_dt = datetime.now()
        start_time_dt = end_time_dt - timedelta(hours=2)
        start = start_time_dt.strftime('%Y-%m-%dT%H:%M:%S')
        end = end_time_dt.strftime('%Y-%m-%dT%H:%M:%S')
    else:
        try:
            start_time_dt = datetime.fromisoformat(start.replace('Z', '+00:00') if 'Z' in start else start)
            end_time_dt = datetime.fromisoformat(end.replace('Z', '+00:00') if 'Z' in end else end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ")

    # Simulate data - in a real application, this would fetch from a database
    all_tasks = ["CPU监控", "内存监控", "网络监控", "磁盘IO"]

    # Get available devices based on selected task
    available_devices = []
    if task_alias:
        available_devices = task_device_mapping.get(task_alias, [])
    else:
        available_devices = [] # If no task selected, no devices are available

    # Generate datasets based on selected devices
    datasets = []
    colors = ["#ff6384", "#36a2eb", "#cc65fe", "#ffce56", "#4bc0c0"]

    devices_to_show = selected_devices if selected_devices else []
    filtered_devices_to_show = [device for device in devices_to_show if device in available_devices]

    for i, device in enumerate(filtered_devices_to_show):
        data_points = []
        current_time = start_time_dt
        value = 20
        while current_time <= end_time_dt:
            value += (0.5 - random.random()) * 10
            value = max(0, min(100, value))
            
            data_points.append({
                "x": current_time.strftime('%Y-%m-%dT%H:%M:%S'),
                "y": round(value, 2)
            })
            current_time += timedelta(minutes=5)
        
        datasets.append({
            "label": device,
            "data": data_points,
            "borderColor": colors[i % len(colors)],
            "fill": False,
        })
    
    response_data = {
        "datasets": datasets,
        "tasks": all_tasks, # Always return all tasks for the dropdown
        "available_devices": available_devices,
        "selected_devices": filtered_devices_to_show
    }
    return JSONResponse(content=response_data)

@app.get("/api/outfile/list")
async def list_outfile_files():
    files = []
    for filename in os.listdir(OUTFILE_DIR):
        path = os.path.join(OUTFILE_DIR, filename)
        if os.path.isfile(path):
            creation_timestamp = os.path.getctime(path)
            creation_datetime = datetime.fromtimestamp(creation_timestamp)
            files.append({
                "name": filename,
                "size": f"{os.path.getsize(path) / 1024:.2f} KB", # Size in KB
                "created_at": creation_datetime.strftime('%Y-%m-%d %H:%M:%S')
            })
    # Sort files by creation time, newest first
    files.sort(key=lambda x: datetime.strptime(x['created_at'], '%Y-%m-%d %H:%M:%S'), reverse=True)
    return JSONResponse(content=files)

@app.get("/api/outfile/download/{filename}")
async def download_outfile_file(filename: str):
    file_path = os.path.join(OUTFILE_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")

# No need for serve_static as StaticFiles handles it

# To run this application, you would typically use Uvicorn:
# uvicorn main:app --reload --port 8080