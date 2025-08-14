
import bottle

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

@bottle.route('/static/<filepath:path>')
def serve_static(filepath):
    return bottle.static_file(filepath, root='./views/static')

if __name__ == '__main__':
    bottle.run(host='localhost', port=8080, debug=True, reloader=True)
