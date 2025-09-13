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

    @app.cli.command("seed")
    def seed():
        """Seeds the database with initial users."""
        from database import User
        users = [
            {'username': 'john.doe', 'password': 'password123', 'email': 'john.doe@promptify.com', 'gender': 'male'},
            {'username': 'sally.smith', 'password': 'password123', 'email': 'sally.smith@promptify.com', 'gender': 'female'},
            {'username': 'richie.rich', 'password': 'password123', 'email': 'richie.rich@promptify.com', 'gender': 'male'},
            {'username': 'bob.rose', 'password': 'password123', 'email': 'bob.rose@promptify.com', 'gender': 'male'},
            {'username': 'amanda.brown', 'password': 'password123', 'email': 'amanda.brown@promptify.com', 'gender': 'female'},
        ]

        for user_data in users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    gender=user_data['gender']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
        
        db.session.commit()
        print("Database seeded with initial users.")

    return app

app = create_app()
asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    uvicorn.run("app:asgi_app", host="0.0.0.0", port=8000, reload=True)
