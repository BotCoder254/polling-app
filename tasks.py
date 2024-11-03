from models import Poll
from datetime import datetime
import time
import threading

def check_expired_polls():
    while True:
        polls = Poll.objects(status='active', expires_at__lte=datetime.utcnow())
        for poll in polls:
            poll.status = 'closed'
            poll.save()
        time.sleep(60)  # Check every minute

def start_background_tasks():
    thread = threading.Thread(target=check_expired_polls, daemon=True)
    thread.start() 