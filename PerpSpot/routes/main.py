from flask import Blueprint, render_template, request, jsonify
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@main_bp.route('/dashboard')
def dashboard():
    """Trading dashboard (alias for index)"""
    return render_template('index.html')

@main_bp.route('/bridge')
def bridge():
    """Bridge arbitrage page"""
    return render_template('index.html')

@main_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@main_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500
