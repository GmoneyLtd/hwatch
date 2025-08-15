import bottle
import json
from datetime import datetime, timedelta

# In-memory data store
tasks = [
    ["device1", "alias1", "192.168.1.1", "type1", "10s", "2024-01-01", True],
    ["device2", "alias2", "192.168.1.2", "type2", "20s", "2024-01-02", False],
    ["device3", "alias3", "192.168.1.3", "type1", "30s", "2024-01-03", True],
    ["device4", "alias4", "192.168.1.4", "type3", "15s", "2024-01-04", True],
]

# Configure template and static file paths
bottle.TEMPLATE_PATH.insert(0, './views/templates')

@bottle.route('/')
def index():
    return bottle.template('app')

@bottle.route('/login')
def login():
    return bottle.template('login')

@bottle.route('/api/data')
def api_data():
    bottle.response.content_type = 'application/json'
    return {'message': 'Hello from Bottle API!', 'timestamp': bottle.request.timestamp}

@bottle.route('/api/tasks')
def api_tasks():
    bottle.response.content_type = 'application/json'
    return json.dumps(tasks)

@bottle.route('/api/tasks/<action>/<device>/<alias>', method='POST')
def api_task_action(action, device, alias):
    global tasks
    for task in tasks:
        if task[0] == device and task[1] == alias:
            if action == 'enable':
                task[6] = True
            elif action == 'disable':
                task[6] = False
    return {'status': 'success'}

@bottle.route('/api/chart')
def api_chart():
    bottle.response.content_type = 'application/json'
    
    # 获取查询参数
    start_time = bottle.request.query.start
    end_time = bottle.request.query.end
    task_alias = bottle.request.query.task_alias
    devices_param = bottle.request.query.devices
    
    # 处理设备参数，支持逗号分隔的列表
    selected_devices = []
    if devices_param:
        if ',' in devices_param:
            # 逗号分隔的设备列表
            selected_devices = [device.strip() for device in devices_param.split(',')]
        else:
            # 单个设备
            selected_devices = [devices_param]
    
    # 定义任务和设备的映射关系（可从数据库或配置文件中读取）
    task_device_mapping = {
        "CPU监控": ["device1", "device2", "device3"],
        "内存监控": ["device2", "device4"],
        "网络监控": ["device1", "device3", "device4"],
        "磁盘IO": ["device1", "device2", "device3", "device4"]
    }
    
    # 如果没有提供时间范围，默认为最近2小时
    if not start_time or not end_time:
        end_time_dt = datetime.now()
        start_time_dt = end_time_dt - timedelta(hours=2)
        start_time = start_time_dt.strftime('%Y-%m-%dT%H:%M:%S')
        end_time = end_time_dt.strftime('%Y-%m-%dT%H:%M:%S')
    
    # 模拟数据 - 实际应用中这里应该从数据库获取数据
    all_tasks = ["CPU监控", "内存监控", "网络监控", "磁盘IO"]
    
    # 根据时间范围获取有数据的任务
    available_tasks = all_tasks  # 显示所有任务
    
    # 如果选择了特定任务，获取该任务下可用的设备
    available_devices = []
    if task_alias:
        # 根据任务获取设备
        available_devices = task_device_mapping.get(task_alias, [])
    else:
        # 如果没有选择任务，不显示设备列表
        available_devices = []
    
    # 根据选定的设备生成数据集
    datasets = []
    colors = ["#ff6384", "#36a2eb", "#cc65fe", "#ffce56", "#4bc0c0"]
    
    # 如果没有选择设备，默认不显示任何数据
    devices_to_show = selected_devices if selected_devices else []
    
    # 只显示可用设备的数据（过滤掉不在当前任务设备列表中的设备）
    filtered_devices_to_show = [device for device in devices_to_show if device in available_devices]
    
    for i, device in enumerate(filtered_devices_to_show):
        # 生成模拟数据
        data_points = []
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if 'Z' in start_time else datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if 'Z' in end_time else datetime.fromisoformat(end_time)
        
        # 生成每5分钟一个数据点
        current_time = start_dt
        value = 20
        while current_time <= end_dt:
            # 添加一些随机变化
            value += (0.5 - random.random()) * 10
            value = max(0, min(100, value))  # 限制在0-100之间
            
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
    
    data = {
        "datasets": datasets,
        "tasks": available_tasks,
        "available_devices": available_devices,
        "selected_devices": filtered_devices_to_show
    }
    return json.dumps(data)

@bottle.route('/static/<filepath:path>')
def serve_static(filepath):
    return bottle.static_file(filepath, root='./views/static')

# 添加随机数模块
import random

if __name__ == '__main__':
    import sys
    port = 8080  
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    bottle.run(host='localhost', port=port, debug=True, reloader=True)
