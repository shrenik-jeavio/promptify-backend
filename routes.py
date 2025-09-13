import json
import traceback
from functools import wraps
from flask import jsonify, request, Blueprint, current_app
from database import db, Prompt, GeneratedPrompt, User, TokenBlacklist, PromptVote
from services import model
from logger import logger
import jwt
from datetime import datetime, timedelta
import uuid

api_bp = Blueprint('api', __name__)

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            token_jti = data.get('jti')
            if not token_jti or TokenBlacklist.query.filter_by(jti=token_jti).first():
                return jsonify({'message': 'Token has been revoked'}), 401
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)
    return decorated

@api_bp.route('/login', methods=['POST'])
def login():
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return jsonify({'message': 'Could not verify'}), 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}

    user = User.query.filter_by(username=auth.username).first()

    if not user or not user.check_password(auth.password):
        return jsonify({'message': 'Could not verify'}), 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24),
        'jti': str(uuid.uuid4())
    }, current_app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        'token': token,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'gender': user.gender
    })

@api_bp.route('/logout', methods=['POST'])
@auth_required
def logout(current_user):
    token = request.headers['x-access-token']
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"], options={"verify_exp": False})
        token_jti = data.get('jti')
        if token_jti:
            blacklisted_token = TokenBlacklist(jti=token_jti)
            db.session.add(blacklisted_token)
            db.session.commit()
            return jsonify({'message': 'Successfully logged out'}), 200
        else:
            return jsonify({'message': 'Invalid token'}), 400
    except Exception as e:
        return jsonify({'message': 'Failed to decode token', 'error': str(e)}), 500


@api_bp.route('/')
@auth_required
def hello_world(current_user):
    return jsonify(message=f'Hello, {current_user.username}!')

@api_bp.route('/prompts', methods=['POST'])
@auth_required
def create_prompt(current_user):
    logger.info("Creating a new prompt.")
    data = request.get_json()
    new_prompt = Prompt(
        user_id=current_user.id,
        title=data.get('title', ''),
        text=data['text'],
        intended_use=data.get('intended_use'),
        target_audience=data.get('target_audience'),
        expected_outcome=data.get('expected_outcome'),
        tags=data.get('tags')
    )
    db.session.add(new_prompt)
    db.session.commit()
    logger.info(f"Prompt {new_prompt.id} created successfully.")
    return jsonify(new_prompt.to_dict()), 201

@api_bp.route('/prompts/<int:prompt_id>', methods=['GET'])
@auth_required
def get_prompt(current_user, prompt_id):
    logger.info(f"Fetching prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if not prompt.is_shared and prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
@auth_required
def update_prompt(current_user, prompt_id):
    logger.info(f"Updating prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403
    data = request.get_json()
    prompt.title = data.get('title', prompt.title)
    prompt.text = data.get('text', prompt.text)
    prompt.intended_use = data.get('intended_use', prompt.intended_use)
    prompt.target_audience = data.get('target_audience', prompt.target_audience)
    prompt.expected_outcome = data.get('expected_outcome', prompt.expected_outcome)
    prompt.tags = data.get('tags', prompt.tags)
    db.session.commit()
    logger.info(f"Prompt {prompt_id} updated successfully.")
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
@auth_required
def delete_prompt(current_user, prompt_id):
    logger.info(f"Deleting prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403
    db.session.delete(prompt)
    db.session.commit()
    logger.info(f"Prompt {prompt_id} deleted successfully.")
    return jsonify({'message': 'Prompt deleted successfully'})

@api_bp.route('/prompts', methods=['GET'])
@auth_required
def get_prompts(current_user):
    sort_order = request.args.get('sort', 'newest')
    query = Prompt.query.filter_by(user_id=current_user.id)

    if sort_order == 'newest':
        query = query.order_by(Prompt.created_at.desc())
    elif sort_order == 'oldest':
        query = query.order_by(Prompt.created_at.asc())

    prompts = query.all()
    return jsonify([prompt.to_dict() for prompt in prompts])

@api_bp.route('/prompts/public', methods=['GET'])
@auth_required
def get_public_prompts(current_user):
    logger.info("Fetching public prompts.")
    prompts = Prompt.query.filter_by(is_shared=True).all()
    return jsonify([prompt.to_dict() for prompt in prompts])

@api_bp.route('/prompts/<int:prompt_id>/publish', methods=['PUT'])
@auth_required
def publish_prompt(current_user, prompt_id):
    logger.info(f"Publishing prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403
    prompt.is_shared = True
    db.session.commit()
    logger.info(f"Prompt {prompt_id} published successfully.")
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/public/search', methods=['GET'])
@auth_required
def search_public_prompts(current_user):
    query_params = request.args
    query = Prompt.query.filter_by(is_shared=True)

    if 'tags' in query_params:
        query = query.filter(Prompt.tags.ilike(f"%{query_params['tags']}%"))
    if 'intended_use' in query_params:
        query = query.filter(Prompt.intended_use.ilike(f"%{query_params['intended_use']}%"))
    if 'target_audience' in query_params:
        query = query.filter(Prompt.target_audience.ilike(f"%{query_params['target_audience']}%"))

    prompts = query.all()
    logger.info(f"Found {len(prompts)} prompts matching search criteria.")
    return jsonify([prompt.to_dict() for prompt in prompts])

@api_bp.route('/prompts/<int:prompt_id>/generate', methods=['POST'])
@auth_required
def generate_prompt(current_user, prompt_id):
    logger.info(f"Generating content for prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if not prompt.is_shared and prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403

    if not model:
        return jsonify({"error": "Generative model not available. Check GOOGLE_API_KEY."}), 503

    # Build the prompt text from the prompt's attributes
    user_prompt_text = f"""
    Prompt: {prompt.text}
    Intended Use: {prompt.intended_use}
    Target Audience: {prompt.target_audience}
    Expected Outcome: {prompt.expected_outcome}
    """

    system_prompt = f"""
    You are a prompt engineering expert. Your task is to analyze a user's prompt and then generate a response based on a refined version of that prompt.
    Please analyze the following user prompt and provide a response in a single JSON object with the following structure:
    {{
      "title": "<A concise title for the prompt, maximum 25 characters>",
      "analysis": {{
        "overall_score": <an integer score out of 10 for the prompt>,
        "clarity": <an integer score out of 10>,
        "specificity": <an integer score out of 10>,
        "effectiveness": <an integer score out of 10>,
        "improvements_made": ["<a list of strings describing improvements made>"],
        "additional_suggestions": ["<a list of strings for further suggestions>"]
      }},
      "refined_prompt": "<your refined version of the user's prompt>",
      "generated_content": "<the content generated by executing the refined prompt>"
    }}

    Here is the user's prompt to analyze:
    ---
    {user_prompt_text.strip()}
    ---
    """

    try:
        response = model.generate_content(system_prompt.strip())
        logger.info(f"Raw response from Gemini for prompt {prompt_id}: {response.text}")
        
        # The response from the model is a JSON string, so we need to parse it
        try:
            # It's possible the model wraps the JSON in markdown, so we'll try to extract it
            clean_response = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(clean_response)
        except json.JSONDecodeError:
            logger.error(f"JSONDecodeError for prompt {prompt_id}. Unable to parse model response.")
            return jsonify({"error": "The AI model returned a response that was not valid JSON.", "raw_response": response.text}), 500

        analysis = data.get('analysis', {})
        
        # If the prompt doesn't have a title, update it with the generated one
        generated_title = data.get('title')
        if generated_title and not prompt.title:
            prompt.title = generated_title[:25] # Enforce max length

        # Save the generated prompt to the database
        new_generated_prompt = GeneratedPrompt(
            prompt_id=prompt.id,
            generated_text=data.get('generated_content'),
            prompt_token_count=response.usage_metadata.prompt_token_count,
            candidates_token_count=response.usage_metadata.candidates_token_count,
            overall_score=analysis.get('overall_score'),
            clarity=analysis.get('clarity'),
            specificity=analysis.get('specificity'),
            effectiveness=analysis.get('effectiveness'),
            refined_prompt=data.get('refined_prompt'),
            improvements_made=analysis.get('improvements_made'),
            additional_suggestions=analysis.get('additional_suggestions')
        )
        db.session.add(new_generated_prompt)
        db.session.commit()
        logger.info(f"Content generated and saved for prompt {prompt_id}.")

        return jsonify(new_generated_prompt.to_dict())
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error generating content for prompt {prompt_id}: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/prompts/<int:prompt_id>/history', methods=['GET'])
@auth_required
def get_generation_history(current_user, prompt_id):
    logger.info(f"Fetching generation history for prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    if not prompt.is_shared and prompt.user_id != current_user.id:
        return jsonify({'message': 'Access forbidden!'}), 403
    history = [gen_prompt.to_dict() for gen_prompt in prompt.generated_prompts]
    logger.info(f"Fetched {len(history)} generated prompts for prompt {prompt_id}.")
    return jsonify(history)

@api_bp.route('/prompts/<int:prompt_id>/vote', methods=['POST'])
@auth_required
def vote_on_prompt(current_user, prompt_id):
    prompt = Prompt.query.get_or_404(prompt_id)

    if not prompt.is_shared:
        return jsonify({'message': 'This prompt is not shared publicly.'}), 403

    if prompt.user_id == current_user.id:
        return jsonify({'message': 'You cannot vote on your own prompt.'}), 403

    data = request.get_json()
    vote_value = data.get('vote')

    if vote_value not in [1, -1, 0]:
        return jsonify({'message': 'Invalid vote value. Use 1 for upvote, -1 for downvote, or 0 to remove vote.'}), 400

    existing_vote = PromptVote.query.filter_by(user_id=current_user.id, prompt_id=prompt.id).first()

    if existing_vote:
        if vote_value == 0:
            db.session.delete(existing_vote)
            db.session.commit()
            return jsonify({'message': 'Vote removed.'})
        else:
            existing_vote.vote = vote_value
            db.session.commit()
            return jsonify({'message': 'Vote updated.'})
    else:
        if vote_value != 0:
            new_vote = PromptVote(user_id=current_user.id, prompt_id=prompt.id, vote=vote_value)
            db.session.add(new_vote)
            db.session.commit()
            return jsonify({'message': 'Vote recorded.'}), 201
        else:
            return jsonify({'message': 'No vote to remove.'})
