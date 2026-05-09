import os
from flask import Flask, redirect, url_for, session
from config import config


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Root redirect
    @app.route('/')
    def index():
        if session.get('user'):
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # Register blueprints
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from app.dashboard import dashboard as dashboard_blueprint
    app.register_blueprint(dashboard_blueprint, url_prefix='/dashboard')

    from app.trainees import trainees as trainees_blueprint
    app.register_blueprint(trainees_blueprint, url_prefix='/trainees')

    from app.media import media as media_blueprint
    app.register_blueprint(media_blueprint, url_prefix='/media')

    from app.portfolio import portfolio as portfolio_blueprint
    app.register_blueprint(portfolio_blueprint, url_prefix='/portfolio')

    from app.employer import employer as employer_blueprint
    app.register_blueprint(employer_blueprint, url_prefix='/employer')

    return app


# Module-level app instance — allows both `gunicorn app:app` and `gunicorn run:app`
app = create_app()
