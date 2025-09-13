from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from asgiref.wsgi import WsgiToAsgi
import uvicorn

from config import Config
from database import db
from routes import api_bp

migrate = Migrate()

def create_app(config_class=Config):
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(api_bp)

    return app

app = create_app()
asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=8000, reload=True)
