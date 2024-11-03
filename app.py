from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_mongoengine import MongoEngine
from config import Config
from models import User
from routes.auth import auth_bp
from routes.polls import polls_bp
from routes.user import user_bp
from utils.email import mail
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    db = MongoEngine(app)
    mail.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.objects(id=user_id).first()

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(polls_bp, url_prefix='/polls')
    app.register_blueprint(user_bp, url_prefix='/user')

    # Create upload folders if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join('static', 'profile_images'), exist_ok=True)

    # Index route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('polls.list'))
        return render_template('index.html')

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    # Context processors
    @app.context_processor
    def utility_processor():
        def format_date(date):
            return date.strftime('%B %d, %Y')
        return dict(format_date=format_date)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)