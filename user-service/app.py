from flask import Flask
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

from config import Config
from models.user import db, bcrypt
from routes.user_routes import user_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)
    migrate = Migrate(app, db)

    app.register_blueprint(user_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
