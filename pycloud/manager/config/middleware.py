"""Pylons middleware initialization"""
import importlib

from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware
from paste.registry import RegistryManager
from pylons import config
from paste.cascade import Cascade
from paste.urlparser import StaticURLParser

from pycloud.manager.config.environment import load_environment


class CloudletApp(PylonsApp):

    def __init__(self, *args, **kwargs):
        super(CloudletApp, self).__init__(*args, **kwargs)
        self._controllers = None

    def setup_app_env(self, environ, start_response):
        PylonsApp.setup_app_env(self, environ, start_response)
        self.load_controllers()

    def load_controllers(self):
        if self._controllers:
            return

        controllers = importlib.import_module("pycloud.manager.controllers")
        controllers.load_controllers()
        self._controllers = controllers

    def find_controller(self, controller_name):
        if controller_name in self.controller_classes:
            return self.controller_classes[controller_name]

        controller_cls = self._controllers.get_controller(controller_name)

        # Cache loaded controllers
        self.controller_classes[controller_name] = controller_cls
        return controller_cls




# Create the cloudlet app
def make_app(global_conf, full_stack=True, static_files=True, **app_conf):

    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # Create the base app, and add the routes middleware
    app = CloudletApp()
    app = RoutesMiddleware(app, config["routes.map"])

    app = RegistryManager(app)

    # Create the app to serve static files
    static_app = StaticURLParser(config['pylons.paths']['static_files'])

    # Set up the order apps are resolved
    app = Cascade([static_app, app])

    return app