from flask_mongoengine import MongoEngine
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
from flask import current_app
import pytz
import uuid

db = MongoEngine()

class Question(db.EmbeddedDocument):
    question_text = db.StringField(required=True)
    question_type = db.StringField(required=True, choices=[
        'single_choice',
        'multiple_choice',
        'ranking',
        'weighted',
        'text',
        'scale'
    ])
    options = db.ListField(db.StringField())
    required = db.BooleanField(default=True)
    points_available = db.IntField(default=100)  # For weighted questions
    min_selections = db.IntField(default=1)  # For multiple choice
    max_selections = db.IntField()  # For multiple choice
    scale_min = db.IntField(default=1)  # For scale questions
    scale_max = db.IntField(default=5)  # For scale questions
    condition = db.DictField()  # For conditional logic

class Answer(db.EmbeddedDocument):
    user = db.ReferenceField('User')
    question_index = db.IntField(required=True)
    answer_value = db.DynamicField()  # Can store different types of answers
    timestamp = db.DateTimeField(default=datetime.utcnow)
    points_allocated = db.IntField()  # For weighted questions

class Poll(db.Document):
    title = db.StringField(required=True)
    description = db.StringField()
    poll_type = db.StringField(required=True, choices=[
        'simple_poll',
        'survey',
        'quiz',
        'ranking'
    ])
    created_by = db.ReferenceField('User')
    created_at = db.DateTimeField(default=datetime.utcnow)
    expires_at = db.DateTimeField()
    status = db.StringField(choices=('draft', 'active', 'closed'), default='draft')
    
    # For simple polls
    options = db.ListField(db.StringField())
    votes = db.DictField(default={})
    
    # For advanced polls/surveys
    questions = db.ListField(db.EmbeddedDocumentField(Question))
    answers = db.ListField(db.EmbeddedDocumentField(Answer))
    
    # Settings
    is_private = db.BooleanField(default=False)
    allow_anonymous = db.BooleanField(default=True)
    show_results = db.StringField(choices=[
        'always',
        'after_vote',
        'after_close',
        'never'
    ], default='always')
    require_verification = db.BooleanField(default=False)
    one_vote_per_ip = db.BooleanField(default=False)
    
    # Access Control
    allowed_users = db.ListField(db.ReferenceField('User'))
    allowed_domains = db.ListField(db.StringField())
    access_code = db.StringField()
    
    # Metadata
    tags = db.ListField(db.StringField())
    category = db.StringField()
    share_token = db.StringField(default=lambda: str(uuid.uuid4()))
    views = db.IntField(default=0)
    vote_timestamps = db.ListField(db.DateTimeField(), default=[])
    
    # Analytics
    completion_time = db.ListField(db.IntField())  # Time taken to complete in seconds
    drop_off_points = db.DictField()  # Track where users abandon the poll
    device_stats = db.DictField()  # Track device types used
    
    meta = {
        'indexes': [
            'created_at',
            'status',
            'tags',
            'category',
            'share_token'
        ]
    }

    def add_vote(self, user=None, option_index=None, is_anonymous=False):
        if is_anonymous and self.allow_anonymous:
            self.anonymous_votes.append({
                'option': option_index,
                'timestamp': datetime.utcnow()
            })
        elif user:
            if str(option_index) not in self.votes:
                self.votes[str(option_index)] = []
            self.votes[str(option_index)].append(str(user.id))
        
        self.vote_timestamps.append(datetime.utcnow())
        self.save()

    def get_results(self):
        if self.poll_type == 'simple_poll':
            return self._get_simple_poll_results()
        elif self.poll_type == 'ranking':
            return self._get_ranking_results()
        elif self.poll_type in ['survey', 'quiz']:
            return self._get_survey_results()

    def _get_simple_poll_results(self):
        total_votes = sum(len(votes) for votes in self.votes.values())
        results = {
            'total_votes': total_votes,
            'options': {}
        }
        for option_index, votes in self.votes.items():
            results['options'][option_index] = {
                'votes': len(votes),
                'percentage': (len(votes) / total_votes * 100) if total_votes > 0 else 0
            }
        return results

    def _get_ranking_results(self):
        results = {}
        for answer in self.answers:
            rankings = answer.answer_value
            for rank, option_index in enumerate(rankings):
                if option_index not in results:
                    results[option_index] = {'points': 0, 'rankings': [0] * len(self.options)}
                # More points for higher rankings
                points = len(self.options) - rank
                results[option_index]['points'] += points
                results[option_index]['rankings'][rank] += 1
        return results

    def _get_survey_results(self):
        results = {i: {'responses': {}} for i in range(len(self.questions))}
        for answer in self.answers:
            q_idx = answer.question_index
            response = answer.answer_value
            if isinstance(response, list):
                for r in response:
                    results[q_idx]['responses'][r] = results[q_idx]['responses'].get(r, 0) + 1
            else:
                results[q_idx]['responses'][response] = results[q_idx]['responses'].get(response, 0) + 1
        return results

    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'description': self.description,
            'poll_type': self.poll_type,
            'created_by': self.created_by.username,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'total_votes': sum(len(votes) for votes in self.votes.values()),
            'views': self.views,
            'engagement_rate': self.get_engagement_rate()
        }

    def get_engagement_rate(self):
        total_votes = sum(len(votes) for votes in self.votes.values())
        return (total_votes / self.views * 100) if self.views > 0 else 0

class User(db.Document):
    username = db.StringField(required=True, unique=True)
    email = db.EmailField(required=True, unique=True)
    password_hash = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)
    profile_image = db.StringField(default="default.jpg")
    bio = db.StringField(max_length=500)
    location = db.StringField()
    is_admin = db.BooleanField(default=False)
    is_verified = db.BooleanField(default=False)
    oauth_id = db.StringField()  # For OAuth login
    
    # Social links
    social_links = db.DictField(default={})
    
    # User preferences
    preferences = db.DictField(default={
        'theme': 'light',
        'chart_type': 'bar',
        'language': 'en',
        'timezone': 'UTC',
        'email_notifications': True,
        'privacy': {
            'show_email': False,
            'show_votes': True,
            'show_activity': True
        }
    })
    
    # Stats and metrics
    total_polls_created = db.IntField(default=0)
    total_votes_cast = db.IntField(default=0)
    badges = db.ListField(db.StringField())
    reputation_points = db.IntField(default=0)
    voting_streak = db.IntField(default=0)
    last_vote_date = db.DateTimeField()
    
    # Relationships
    following = db.ListField(db.ReferenceField('User'))
    followers = db.ListField(db.ReferenceField('User'))
    favorite_polls = db.ListField(db.ReferenceField('Poll'))
    
    # Activity tracking
    last_login = db.DateTimeField()
    login_count = db.IntField(default=0)
    last_active = db.DateTimeField()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        return jwt.encode(
            {'user_id': str(self.id), 'exp': datetime.utcnow() + timedelta(hours=24)},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_token(token):
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return User.objects(id=data['user_id']).first()
        except:
            return None

    def update_activity(self):
        self.last_active = datetime.utcnow()
        self.save()

    def record_login(self):
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.save()

    def add_reputation(self, points):
        self.reputation_points += points
        self.check_badges()
        self.save()

    def check_badges(self):
        if self.total_polls_created >= 10 and 'Poll Creator' not in self.badges:
            self.badges.append('Poll Creator')
        if self.total_votes_cast >= 100 and 'Active Voter' not in self.badges:
            self.badges.append('Active Voter')
        if self.reputation_points >= 1000 and 'Trusted User' not in self.badges:
            self.badges.append('Trusted User')

    def update_voting_streak(self):
        today = datetime.utcnow().date()
        if self.last_vote_date:
            last_vote_date = self.last_vote_date.date()
            if (today - last_vote_date).days == 1:
                self.voting_streak += 1
            elif (today - last_vote_date).days > 1:
                self.voting_streak = 1
        else:
            self.voting_streak = 1
        self.last_vote_date = datetime.utcnow()
        self.save()

    def to_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email if self.preferences['privacy']['show_email'] else None,
            'profile_image': self.profile_image,
            'bio': self.bio,
            'location': self.location,
            'badges': self.badges,
            'reputation': self.reputation_points,
            'total_polls': self.total_polls_created,
            'total_votes': self.total_votes_cast,
            'joined_date': self.created_at.strftime('%Y-%m-%d'),
            'voting_streak': self.voting_streak
        }

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)