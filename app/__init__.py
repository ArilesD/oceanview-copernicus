from secrets import token_hex

from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

cache = Cache(config={'CACHE_TYPE' : 'SimpleCache'})
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    web_app = Flask(__name__, instance_relative_config=True)
    
    web_app.config.from_mapping(
        SECRET_KEY=token_hex(32),
        DB_HOST='127.0.0.1',
        DB_PORT=3306,
        DB_NAME='oceanview_demo',
        DB_USER='oceanview',
        DB_PASSWORD='',
        SESSION_COOKIE_SAMESITE='Lax',
    )
    web_app.config.from_pyfile('config.py', silent=True)
    web_app.config.from_prefixed_env(prefix='OCEANVIEW', loads=str)
    web_app.config['CACHE_TYPE'] = 'SimpleCache'
    web_app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    cache.init_app(web_app)
    csrf.init_app(web_app)
    
    login_manager.init_app(web_app)
    login_manager.login_view = 'auth.login' 

    from app.controllers.main_routes import main_bp
    from app.controllers.api_routes import api_bp
    from app.controllers.auth_routes import auth_bp
    
    web_app.register_blueprint(main_bp)
    web_app.register_blueprint(api_bp)
    web_app.register_blueprint(auth_bp)
    
    import app.models.user 
    
    from app.demo import init_demo

    web_app.cli.add_command(init_demo)
    return web_app
