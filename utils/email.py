from flask import current_app, render_template, url_for
from flask_mail import Message, Mail
from threading import Thread
import jwt
from datetime import datetime, timedelta

mail = Mail()

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipient, template, **kwargs):
    msg = Message(
        subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[recipient]
    )
    msg.html = render_template(template, **kwargs)
    
    # Send email asynchronously
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()

def generate_verification_token(user):
    token = jwt.encode(
        {
            'user_id': str(user.id),
            'exp': datetime.utcnow() + timedelta(hours=24)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    return token

def verify_token(token):
    try:
        data = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return data['user_id']
    except:
        return None

def send_verification_email(user):
    token = generate_verification_token(user)
    verification_url = url_for(
        'auth.verify_email',
        token=token,
        _external=True
    )
    verification_code = token[:6].upper()
    
    send_email(
        'Verify Your Email - PollMaster',
        user.email,
        'email/verify.html',
        user=user,
        verification_url=verification_url,
        verification_code=verification_code
    )

def send_reset_password_email(user):
    token = generate_verification_token(user)
    reset_url = url_for(
        'auth.reset_password',
        token=token,
        _external=True
    )
    
    send_email(
        'Reset Your Password - PollMaster',
        user.email,
        'email/reset_password.html',
        user=user,
        reset_url=reset_url
    )

def send_welcome_email(user):
    send_email(
        'Welcome to PollMaster!',
        user.email,
        'email/welcome.html',
        user=user
    )

def send_poll_notification(user, poll):
    send_email(
        f'New Poll: {poll.title}',
        user.email,
        'email/poll_notification.html',
        user=user,
        poll=poll
    ) 