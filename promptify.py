from flask import Blueprint, render_template

promptify_bp = Blueprint('promptify', __name__, template_folder='templates/promptify', static_folder='static')

@promptify_bp.route('/')
def index():
    return render_template('index.html')

@promptify_bp.route('/login')
def login():
    return render_template('login.html')

@promptify_bp.route('/prompt/<int:prompt_id>')
def prompt_details():
    return render_template('prompt.html')

@promptify_bp.route('/public')
def public_prompts():
    return render_template('public.html')
