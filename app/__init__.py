from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager

# Initialize the Flask application and load configuration
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Set up the LoginManager
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Ensure you have a route named 'login'

# Import routes and models so that they are registered with the application
from app import routes, models

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))