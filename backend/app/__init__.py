from flask import Flask
from pymongo import MongoClient

from config import Config
from extensions import cors, jwt
from .models.user_model import create_user_indexes
from .routes.auth_routes import auth_bp
from .models.task_model import create_task_indexes
from .routes.task_routes import task_bp
from .models.vm_model import create_vm_indexes
from .routes.vm_routes import vm_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    secret = app.config.get("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "Set JWT_SECRET_KEY to a random secret of at least 32 characters."
        )

    jwt.init_app(app)

    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": [app.config["FRONTEND_ORIGIN"]]
            }
        },
    )

    mongo_client = MongoClient(
        app.config["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )

    try:
        mongo_client.admin.command("ping")
    except Exception:
        mongo_client.close()
        raise

    app.extensions["mongo_client"] = mongo_client
    app.extensions["mongo_db"] = mongo_client[
        app.config["MONGO_DB_NAME"]
    ]

    app.logger.setLevel("INFO")
    app.logger.info("MongoDB connection verified.")

    with app.app_context():
        create_user_indexes()
        create_task_indexes()
        create_vm_indexes()
        app.logger.info("Task index verified.")

    app.logger.info("User email index verified.")
    app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(vm_bp)

    return app