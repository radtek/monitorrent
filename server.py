import os
import random
import string
from cherrypy import wsgiserver
from path import path
from monitorrent.engine import DBEngineRunner
from monitorrent.db import init_db_engine, create_db, upgrade
from monitorrent.plugin_managers import load_plugins, get_all_plugins, upgrades, TrackersManager, ClientsManager
from monitorrent.settings_manager import SettingsManager
from monitorrent.rest import create_api, AuthMiddleware
from monitorrent.rest.static_file import StaticFiles
from monitorrent.rest.login import Login, Logout
from monitorrent.rest.topics import TopicCollection, TopicParse, Topic
from monitorrent.rest.trackers import TrackerCollection, Tracker, TrackerCheck
from monitorrent.rest.clients import ClientCollection, Client, ClientCheck
from monitorrent.rest.settings_authentication import SettingsAuthentication
from monitorrent.rest.settings_password import SettingsPassword
from monitorrent.rest.settings_execute import SettingsExecute
from monitorrent.rest.execute import ExecuteLog, ExecuteCall, EngineRunnerLogger


init_db_engine("sqlite:///monitorrent.db", False)
load_plugins()
upgrade(get_all_plugins(), upgrades)
create_db()

tracker_manager = TrackersManager()
clients_manager = ClientsManager()
settings_manager = SettingsManager()

engine_runner_logger = EngineRunnerLogger()
engine_runner = DBEngineRunner(engine_runner_logger, tracker_manager, clients_manager)


def add_static_route(api, folder):
    p = path(folder)
    api.add_route('/', StaticFiles(folder, 'index.html'))
    api.add_route('/favicon.ico', StaticFiles(folder, 'favicon.ico', False))
    api.add_route('/styles/monitorrent.css', StaticFiles(os.path.join(folder, 'styles'), 'monitorrent.css', False))
    api.add_route('/login', StaticFiles(folder, 'login.html', False))
    for f in p.walkdirs():
        parts = filter(None, f.splitall())
        url = '/' + '/'.join(parts[1:]) + '/{filename}'
        api.add_route(url, StaticFiles(f))

debug = True
if debug:
    secret_key = 'Secret!'
    token = 'monitorrent'
else:
    secret_key = os.urandom(24)
    token = ''.join(random.choice(string.letters) for x in range(8))
3

AuthMiddleware.init(secret_key, token)
app = create_api()
add_static_route(app, 'webapp')
app.add_route('/api/login', Login(settings_manager))
app.add_route('/api/logout', Logout())
app.add_route('/api/topics', TopicCollection(tracker_manager))
app.add_route('/api/topics/{id}', Topic(tracker_manager))
app.add_route('/api/topics/parse', TopicParse(tracker_manager))
app.add_route('/api/trackers', TrackerCollection(tracker_manager))
app.add_route('/api/trackers/{tracker}', Tracker(tracker_manager))
app.add_route('/api/trackers/{tracker}/check', TrackerCheck(tracker_manager))
app.add_route('/api/clients', ClientCollection(clients_manager))
app.add_route('/api/clients/{client}', Client(clients_manager))
app.add_route('/api/clients/{client}/check', ClientCheck(clients_manager))
app.add_route('/api/settings/authentication', SettingsAuthentication(settings_manager))
app.add_route('/api/settings/password', SettingsPassword(settings_manager))
app.add_route('/api/settings/execute', SettingsExecute(engine_runner))
app.add_route('/api/execute/logs', ExecuteLog(engine_runner_logger))
app.add_route('/api/execute/call', ExecuteCall(engine_runner))

if __name__ == '__main__':
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 8080), d)

    try:
        server.start()
    except KeyboardInterrupt:
        engine_runner.stop()
        server.stop()
