
import bottle
import json

# In-memory data store
tasks = [
    ["device1", "alias1", "192.168.1.1", "type1", "10s", "2024-01-01", True],
    ["device2", "alias2", "192.168.1.2", "type2", "20s", "2024-01-02", False],
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
    data = {
        "datasets": [
            {
                "label": "device1",
                "data": [
                    {"x": "2024-08-14T10:00:00", "y": 10},
                    {"x": "2024-08-14T10:01:00", "y": 15},
                    {"x": "2024-08-14T10:02:00", "y": 12},
                ],
                "borderColor": "#ff6384",
                "fill": False,
            },
            {
                "label": "device2",
                "data": [
                    {"x": "2024-08-14T10:00:00", "y": 5},
                    {"x": "2024-08-14T10:01:00", "y": 8},
                    {"x": "2024-08-14T10:02:00", "y": 11},
                ],
                "borderColor": "#36a2eb",
                "fill": False,
            },
        ],
        "tasks": ["task1", "task2"],
        "available_devices": ["device1", "device2", "device3"],
    }
    return json.dumps(data)

@bottle.route('/static/<filepath:path>')
def serve_static(filepath):
    return bottle.static_file(filepath, root='./views/static')

if __name__ == '__main__':
    bottle.run(host='localhost', port=8080, debug=True, reloader=True)
