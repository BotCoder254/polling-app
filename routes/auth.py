from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from utils.email import send_verification_email, send_reset_password_email
import requests
import json
from oauthlib.oauth2 import WebApplicationClient
import uuid

auth_bp = Blueprint('auth', __name__)

# Move OAuth client initialization to a function
def get_google_client():
    return WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])

def get_google_provider_cfg():
    return requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()

@auth_bp.route('/login/google')
def google_login():
    # Initialize client within route
    client = get_google_client()
    
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)

@auth_bp.route('/login/google/callback')
def google_callback():
    # Initialize client within route
    client = get_google_client()
    
    # Get authorization code Google sent back
    code = request.args.get("code")
    
    # Find out what URL to hit to get tokens
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(current_app.config['GOOGLE_CLIENT_ID'], current_app.config['GOOGLE_CLIENT_SECRET']),
    )

    # Parse the tokens
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Get user info from Google
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        users_name = userinfo_response.json()["given_name"]
        picture = userinfo_response.json().get("picture", None)

        # Check if user exists
        user = User.objects(email=users_email).first()
        if not user:
            # Create new user
            user = User(
                username=users_name,
                email=users_email,
                profile_image=picture,
                is_verified=True,
                oauth_id=unique_id
            )
            user.set_password(str(uuid.uuid4()))  # Random password for OAuth users
            user.save()

        login_user(user)
        return redirect(url_for('index'))
    else:
        flash("Google authentication failed", "error")
        return redirect(url_for('auth.login'))

@auth_bp.route('/verify/<token>')
def verify_email(token):
    user = User.verify_email_token(token)
    if user:
        user.is_verified = True
        user.save()
        flash('Your email has been verified!', 'success')
        return redirect(url_for('auth.login'))
    flash('Invalid or expired verification link', 'error')
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.objects(email=email).first()
        if user:
            send_reset_password_email(user)
            flash('Check your email for password reset instructions', 'success')
            return redirect(url_for('auth.login'))
        flash('Email address not found', 'error')
    return render_template('auth/reset_password_request.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset link', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        user.set_password(password)
        user.save()
        flash('Your password has been reset', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.objects(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        user.save()
        
        login_user(user)
        return redirect(url_for('polls.list'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.objects(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('polls.list'))
        
        flash('Invalid username or password')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))