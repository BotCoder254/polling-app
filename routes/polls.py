from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app
from flask_login import login_required, current_user
from models import Poll, User, Question, Answer
from datetime import datetime
from utils.pagination import PaginatedResponse
import pytz

polls_bp = Blueprint('polls', __name__, url_prefix='/polls')

@polls_bp.route('/')
def list():
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', current_app.config['POLLS_PER_PAGE']))
    
    # Get filters
    tag = request.args.get('tag')
    search = request.args.get('search')
    category = request.args.get('category')
    sort_by = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')
    view_mode = request.args.get('view', 'grid')
    
    # Base query
    query = Poll.objects(status='active')
    
    # Apply filters
    if tag:
        query = query.filter(tags=tag)
    if search:
        query = query.filter(title__icontains=search)
    if category:
        query = query.filter(category=category)
    
    # Apply sorting
    sort_prefix = '-' if order == 'desc' else ''
    query = query.order_by(f'{sort_prefix}{sort_by}')
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    polls = query.skip((page - 1) * per_page).limit(per_page)
    
    # Get aggregated data
    all_tags = Poll.objects.distinct('tags')
    categories = Poll.objects.distinct('category')
    
    # Create paginated response
    paginated_polls = PaginatedResponse(polls, page, per_page, total)
    
    return render_template('polls/list.html',
                         polls=paginated_polls,
                         all_tags=all_tags,
                         categories=categories,
                         view_mode=view_mode,
                         current_filters={
                             'tag': tag,
                             'search': search,
                             'category': category,
                             'sort': sort_by,
                             'order': order
                         })

@polls_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    try:
        if request.method == 'POST':
            # Get form data
            form_data = request.form if request.form else request.get_json()
            if not form_data:
                raise ValueError("No data provided")

            # Create poll
            poll = Poll(
                title=form_data.get('title'),
                description=form_data.get('description'),
                poll_type=form_data.get('poll_type', 'simple_poll'),
                created_by=current_user.id,
                status='active'
            )

            # Handle options
            if form_data.get('poll_type') == 'simple_poll':
                options = request.form.getlist('options[]') if request.form else form_data.get('options', [])
                if not options:
                    raise ValueError("No options provided")
                poll.options = options
            else:
                questions = form_data.get('questions', [])
                if not questions:
                    raise ValueError("No questions provided")
                for q_data in questions:
                    question = Question(
                        question_text=q_data.get('text'),
                        question_type=q_data.get('type'),
                        options=q_data.get('options', []),
                        required=q_data.get('required', True),
                        points_available=q_data.get('points', 100),
                        min_selections=q_data.get('min_selections', 1),
                        max_selections=q_data.get('max_selections')
                    )
                    poll.questions.append(question)

            # Handle settings
            if form_data.get('expires_at'):
                poll.expires_at = datetime.fromisoformat(form_data['expires_at'])
            poll.is_private = form_data.get('is_private', False)
            poll.allow_anonymous = form_data.get('allow_anonymous', True)
            poll.show_results = form_data.get('show_results', 'always')
            poll.require_verification = form_data.get('require_verification', False)
            poll.one_vote_per_ip = form_data.get('one_vote_per_ip', False)

            # Handle tags
            tags = form_data.get('tags', '')
            if isinstance(tags, str):
                poll.tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
            else:
                poll.tags = tags

            poll.category = form_data.get('category')
            poll.save()

            # Update user stats
            current_user.total_polls_created += 1
            current_user.add_reputation(10)
            current_user.save()

            flash('Poll created successfully!', 'success')
            return redirect(url_for('polls.view', poll_id=str(poll.id)))

    except ValueError as e:
        flash(str(e), 'error')
        return redirect(url_for('polls.create'))
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('polls.create'))

    return render_template('polls/create.html')

@polls_bp.route('/<poll_id>')
def view(poll_id):
    try:
        poll = Poll.objects(id=poll_id).first_or_404()
        poll.views += 1
        poll.save()
        
        can_vote, error = poll.can_user_vote(current_user, request.remote_addr)
        
        return render_template('polls/view.html',
                             poll=poll,
                             can_vote=can_vote,
                             error=error)
    except Exception as e:
        flash('Poll not found', 'error')
        return redirect(url_for('polls.list'))

@polls_bp.route('/<poll_id>/vote', methods=['POST'])
def vote(poll_id):
    poll = Poll.objects(id=poll_id).first_or_404()
    data = request.get_json()
    
    can_vote, error = poll.can_user_vote(current_user, request.remote_addr)
    if not can_vote:
        return jsonify({'error': error}), 400
    
    if poll.poll_type == 'simple_poll':
        poll.add_vote(
            user=current_user if current_user.is_authenticated else None,
            option_index=data['option'],
            is_anonymous=data.get('anonymous', False)
        )
    else:
        for answer in data['answers']:
            poll.add_answer(
                user=current_user if current_user.is_authenticated else None,
                question_index=answer['question_index'],
                answer_value=answer['value'],
                points=answer.get('points')
            )
    
    if current_user.is_authenticated:
        current_user.total_votes_cast += 1
        current_user.add_reputation(1)
        current_user.update_voting_streak()
        current_user.save()
    
    return jsonify(poll.to_dict())