from functools import wraps
from flask import jsonify, request, Blueprint
from database import db, Prompt, GeneratedPrompt
from services import model
from logger import logger

api_bp = Blueprint('api', __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Authorization')
        if token == 'admin':
            return f(*args, **kwargs)
        return jsonify({'message': 'Authentication is required!'}), 401
    return decorated

@api_bp.route('/')
@token_required
def hello_world():
    return jsonify(message='Hello, World!')

@api_bp.route('/prompts', methods=['POST'])
@token_required
def create_prompt():
    logger.info("Creating a new prompt.")
    data = request.get_json()
    new_prompt = Prompt(
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
@token_required
def get_prompt(prompt_id):
    logger.info(f"Fetching prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/<int:prompt_id>', methods=['PUT'])
@token_required
def update_prompt(prompt_id):
    logger.info(f"Updating prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    data = request.get_json()
    prompt.text = data.get('text', prompt.text)
    prompt.intended_use = data.get('intended_use', prompt.intended_use)
    prompt.target_audience = data.get('target_audience', prompt.target_audience)
    prompt.expected_outcome = data.get('expected_outcome', prompt.expected_outcome)
    prompt.tags = data.get('tags', prompt.tags)
    db.session.commit()
    logger.info(f"Prompt {prompt_id} updated successfully.")
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/<int:prompt_id>', methods=['DELETE'])
@token_required
def delete_prompt(prompt_id):
    logger.info(f"Deleting prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    db.session.delete(prompt)
    db.session.commit()
    logger.info(f"Prompt {prompt_id} deleted successfully.")
    return jsonify({'message': 'Prompt deleted successfully'})

@api_bp.route('/prompts/private', methods=['GET'])
@token_required
def get_private_prompts():
    prompts = Prompt.query.filter_by(is_shared=False).all()
    return jsonify([prompt.to_dict() for prompt in prompts])

@api_bp.route('/prompts/public', methods=['GET'])
@token_required
def get_public_prompts():
    logger.info("Fetching public prompts.")
    prompts = Prompt.query.filter_by(is_shared=True).all()
    return jsonify([prompt.to_dict() for prompt in prompts])

@api_bp.route('/prompts/<int:prompt_id>/publish', methods=['PUT'])
@token_required
def publish_prompt(prompt_id):
    logger.info(f"Publishing prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    prompt.is_shared = True
    db.session.commit()
    logger.info(f"Prompt {prompt_id} published successfully.")
    return jsonify(prompt.to_dict())

@api_bp.route('/prompts/public/search', methods=['GET'])
@token_required
def search_public_prompts():
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
@token_required
def generate_prompt(prompt_id):
    logger.info(f"Generating content for prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)

    if not model:
        return jsonify({"error": "Generative model not available. Check GOOGLE_API_KEY."}), 503

    # Build the prompt text from the prompt's attributes
    prompt_text = f"""
    Prompt: {prompt.text}
    Intended Use: {prompt.intended_use}
    Target Audience: {prompt.target_audience}
    Expected Outcome: {prompt.expected_outcome}
    """

    try:
        response = model.generate_content(prompt_text.strip())
        
        # Save the generated prompt to the database
        new_generated_prompt = GeneratedPrompt(
            prompt_id=prompt.id,
            generated_text=response.text,
            prompt_token_count=response.usage_metadata.prompt_token_count,
            candidates_token_count=response.usage_metadata.candidates_token_count
        )
        db.session.add(new_generated_prompt)
        db.session.commit()
        logger.info(f"Content generated and saved for prompt {prompt_id}.")

        return jsonify(new_generated_prompt.to_dict())
    except Exception as e:
        logger.error(f"Error generating content for prompt {prompt_id}: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/prompts/<int:prompt_id>/history', methods=['GET'])
@token_required
def get_generation_history(prompt_id):
    logger.info(f"Fetching generation history for prompt {prompt_id}.")
    prompt = Prompt.query.get_or_404(prompt_id)
    history = [gen_prompt.to_dict() for gen_prompt in prompt.generated_prompts]
    logger.info(f"Fetched {len(history)} generated prompts for prompt {prompt_id}.")
    return jsonify(history)
