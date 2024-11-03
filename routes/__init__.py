from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__)
polls_bp = Blueprint('polls', __name__)
user_bp = Blueprint('user', __name__)

# Import routes after creating blueprints to avoid circular imports
from . import auth
from . import polls
from . import user
