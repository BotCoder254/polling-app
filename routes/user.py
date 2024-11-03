from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for

from flask_login import login_required, current_user

from models import Poll, User

from werkzeug.utils import secure_filename

import os

import pytz

from datetime import datetime, timedelta

from collections import defaultdict



user_bp = Blueprint('user', __name__)



@user_bp.route('/dashboard')

@login_required

def dashboard():

    # Get user's stats

    total_polls = Poll.objects(created_by=current_user.id).count()

    active_polls = Poll.objects(created_by=current_user.id, status='active').count()

    

    # Calculate total votes and engagement

    user_polls = Poll.objects(created_by=current_user.id)

    total_votes = sum(len(poll.votes.values()) + len(poll.anonymous_votes) for poll in user_polls)

    total_views = sum(poll.views for poll in user_polls)

    engagement_rate = (total_votes / total_views * 100) if total_views > 0 else 0

    

    # Calculate average response time

    response_times = []

    for poll in user_polls:

        if poll.vote_timestamps:

            first_vote = min(poll.vote_timestamps)

            response_time = (first_vote - poll.created_at).total_seconds() / 3600  # in hours

            response_times.append(response_time)

    avg_response_time = f"{sum(response_times) / len(response_times):.1f}h" if response_times else "N/A"

    

    # Get participation stats

    total_participants = len(set(

        user_id for poll in user_polls 

        for votes in poll.votes.values() 

        for user_id in votes

    ))

    active_users = len(set(

        user_id for poll in Poll.objects(status='active', created_by=current_user.id)

        for votes in poll.votes.values()

        for user_id in votes

    ))

    

    # Prepare votes over time data

    votes_data = defaultdict(int)

    for poll in user_polls:

        for timestamp in poll.vote_timestamps:

            date = timestamp.date()

            votes_data[date] += 1

    votes_data = dict(sorted(votes_data.items()))

    

    # Prepare engagement analytics data

    engagement_data = {

        'categories': ['Views', 'Votes', 'Shares', 'Comments'],

        'values': [

            total_views,

            total_votes,

            sum(1 for poll in user_polls if poll.share_token),

            0  # Placeholder for comments if implemented

        ]

    }

    

    # Prepare demographics data (example)

    demographics_data = {

        'labels': ['Mobile', 'Desktop', 'Tablet'],

        'values': [45, 40, 15]  # Example values

    }

    

    # Get recent activity

    recent_polls = Poll.objects(created_by=current_user.id).order_by('-created_at')[:5]

    recent_votes = []

    for poll in Poll.objects(votes__values__contains=str(current_user.id)).order_by('-created_at')[:5]:

        vote_timestamp = max(timestamp for timestamp in poll.vote_timestamps)

        recent_votes.append({

            'poll': poll,

            'timestamp': vote_timestamp

        })

    

    return render_template('user/dashboard.html',

                         total_polls=total_polls,

                         active_polls=active_polls,

                         total_votes=total_votes,

                         engagement_rate=f"{engagement_rate:.1f}",

                         avg_response_time=avg_response_time,

                         total_participants=total_participants,

                         active_users=active_users,

                         user_engagement=f"{(active_users/total_participants*100):.1f}" if total_participants > 0 else "0",

                         recent_polls=recent_polls,

                         recent_votes=recent_votes,

                         votes_data={

                             'dates': [d.strftime('%Y-%m-%d') for d in votes_data.keys()],

                             'counts': list(votes_data.values())

                         },

                         engagement_data=engagement_data,

                         demographics_data=demographics_data)



@user_bp.route('/analytics/<poll_id>')

@login_required

def poll_analytics(poll_id):

    poll = Poll.objects(id=poll_id, created_by=current_user.id).first_or_404()

    

    # Calculate detailed analytics

    total_votes = sum(len(v) for v in poll.votes.values()) + len(poll.anonymous_votes)

    vote_distribution = {

        option: len(votes) + sum(1 for v in poll.anonymous_votes if v['option'] == i)

        for i, (option, votes) in enumerate(poll.votes.items())

    }

    

    # Time-based analysis

    hourly_distribution = defaultdict(int)

    for timestamp in poll.vote_timestamps:

        hour = timestamp.hour

        hourly_distribution[hour] += 1

    

    # Engagement metrics

    engagement_rate = (total_votes / poll.views * 100) if poll.views > 0 else 0

    

    return render_template('user/poll_analytics.html',

                         poll=poll,

                         total_votes=total_votes,

                         vote_distribution=vote_distribution,

                         hourly_distribution=dict(sorted(hourly_distribution.items())),

                         engagement_rate=engagement_rate)



@user_bp.route('/export/<poll_id>')

@login_required

def export_poll_data(poll_id):

    poll = Poll.objects(id=poll_id, created_by=current_user.id).first_or_404()

    

    # Prepare data for export

    data = {

        'poll_info': poll.to_dict(),

        'vote_details': {

            'registered_votes': poll.votes,

            'anonymous_votes': poll.anonymous_votes

        },

        'timestamps': [t.isoformat() for t in poll.vote_timestamps],

        'analytics': {

            'total_votes': sum(len(v) for v in poll.votes.values()) + len(poll.anonymous_votes),

            'views': poll.views,

            'engagement_rate': (poll.total_votes / poll.views * 100) if poll.views > 0 else 0

        }

    }

    

    return jsonify(data)



@user_bp.route('/profile/update', methods=['POST'])

@login_required

def update_profile():

    data = request.form

    

    current_user.bio = data.get('bio', '')

    current_user.location = data.get('location', '')

    current_user.social_links = {

        'twitter': data.get('twitter', ''),

        'linkedin': data.get('linkedin', ''),

        'github': data.get('github', '')

    }

    current_user.save()

    

    flash('Profile updated successfully!', 'success')

    return redirect(url_for('user.profile', username=current_user.username))



@user_bp.route('/profile/image', methods=['POST'])

@login_required

def update_profile_image():

    if 'image' not in request.files:

        return jsonify({'error': 'No image provided'}), 400

    

    file = request.files['image']

    if file.filename == '':

        return jsonify({'error': 'No image selected'}), 400

    

    if file and allowed_file(file.filename):

        filename = secure_filename(f"{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg")

        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

        

        # Update user's profile image

        current_user.profile_image = filename

        current_user.save()

        

        return jsonify({'status': 'success', 'filename': filename})

    

    return jsonify({'error': 'Invalid file type'}), 400



def allowed_file(filename):

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@user_bp.route('/settings', methods=['GET', 'POST'])

@login_required

def settings():

    if request.method == 'POST':

        data = request.get_json()

        

        # Update user preferences

        current_user.preferences.update({

            'theme': data.get('theme', 'light'),

            'chart_type': data.get('chart_type', 'bar'),

            'language': data.get('language', 'en'),

            'timezone': data.get('timezone', 'UTC'),

            'email_notifications': data.get('email_notifications', True),

            'privacy': {

                'show_email': data.get('show_email', False),

                'show_votes': data.get('show_votes', True),

                'show_activity': data.get('show_activity', True)

            }

        })

        current_user.save()

        return jsonify({'status': 'success'})

    

    return render_template('user/settings.html', 

                         user=current_user,

                         timezones=pytz.all_timezones)



@user_bp.route('/polls/close/<poll_id>', methods=['POST'])

@login_required

def close_poll(poll_id):

    poll = Poll.objects(id=poll_id, created_by=current_user.id).first_or_404()

    poll.status = 'closed'

    poll.save()

    return jsonify({'status': 'success'})



@user_bp.route('/my-polls')

@login_required

def my_polls():

    active_polls = Poll.objects(created_by=current_user.id, status='active')

    closed_polls = Poll.objects(created_by=current_user.id, status='closed')

    return render_template('user/my_polls.html',

                         active_polls=active_polls,

                         closed_polls=closed_polls)



@user_bp.route('/my-votes')

@login_required

def my_votes():

    voted_polls = Poll.objects(votes__values__contains=str(current_user.id))

    return render_template('user/my_votes.html',

                         voted_polls=voted_polls)



@user_bp.route('/profile/<username>')

@login_required

def profile(username):

    user = User.objects(username=username).first_or_404()

    

    # Get user's polls

    polls = Poll.objects(created_by=user.id).order_by('-created_at')

    

    # Get user's activities

    activities = []

    

    # Add poll creation activities

    for poll in polls:

        activities.append({

            'type': 'create',

            'icon': 'fa-poll',

            'description': f'Created poll: {poll.title}',

            'timestamp': poll.created_at

        })

    

    # Add voting activities

    voted_polls = Poll.objects(votes__values__contains=str(user.id))

    for poll in voted_polls:

        activities.append({

            'type': 'vote',

            'icon': 'fa-vote-yea',

            'description': f'Voted on: {poll.title}',

            'timestamp': poll.created_at

        })

    

    # Sort activities by timestamp

    activities.sort(key=lambda x: x['timestamp'], reverse=True)

    

    return render_template('user/profile.html',

                         user=user,

                         polls=polls,

                         activities=activities)



@user_bp.route('/analytics')

@login_required

def analytics():

    # Get user's polls

    polls = Poll.objects(created_by=current_user.id)

    

    # Calculate statistics

    total_polls = len(polls)

    total_votes = sum(sum(len(votes) for votes in poll.votes.values()) for poll in polls)

    active_polls = len([p for p in polls if p.status == 'active'])

    

    # Get vote distribution over time

    vote_timeline = {}

    for poll in polls:

        for timestamp in poll.vote_timestamps:

            date = timestamp.date()

            vote_timeline[date] = vote_timeline.get(date, 0) + 1

    

    # Sort timeline data

    timeline_data = sorted(vote_timeline.items())

    

    # Calculate engagement rate

    total_views = sum(poll.views for poll in polls)

    engagement_rate = (total_votes / total_views * 100) if total_views > 0 else 0

    

    return render_template('user/analytics.html',

                         total_polls=total_polls,

                         total_votes=total_votes,

                         active_polls=active_polls,

                         timeline_data=timeline_data,

                         engagement_rate=engagement_rate)
