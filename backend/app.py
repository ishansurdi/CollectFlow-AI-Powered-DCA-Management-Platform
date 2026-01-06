from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from config import Config
from db.mongo import init_db
from utils.logger import setup_logger
import os

# Import routes
from routes.auth_routes import auth_bp
from routes.case_routes import case_bp
from routes.dca_routes import dca_bp
from routes.ai_routes import ai_bp
from routes.dashboard_routes import dashboard_bp
from routes.integration_routes import integration_bp

# Import agent orchestrator
from agents.orchestrator import AgentOrchestrator

# Global orchestrator instance
agent_orchestrator = None

def create_app():
    """Application factory pattern"""
    global agent_orchestrator
    
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(Config)
    
    # Enable CORS for production deployment
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Setup logging
    logger = setup_logger()
    app.logger.handlers = logger.handlers
    app.logger.setLevel(logger.level)
    
    # Initialize database
    try:
        init_db()
        app.logger.info("Database connection established")
    except Exception as e:
        app.logger.error(f"Failed to connect to database: {str(e)}")
        raise
    
    # Initialize autonomous agent system (only once)
    if agent_orchestrator is None:
        os.makedirs('./backend/ai_models/saved_models', exist_ok=True)
        os.makedirs('./logs', exist_ok=True)
        agent_orchestrator = AgentOrchestrator()
        agent_orchestrator.start()
        app.logger.info("Autonomous Agent System ACTIVATED")
    
    # Register API blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(case_bp, url_prefix='/api/cases')
    app.register_blueprint(dca_bp, url_prefix='/api/dca')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(integration_bp, url_prefix='/api/integration')
    
    # Disable strict slashes globally
    app.url_map.strict_slashes = False
    
    # Serve frontend files
    @app.route('/')
    def index():
        return send_from_directory('../frontend', 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        # Prevent serving API routes as static files
        if path.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404
        return send_from_directory('../frontend', path)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'FedEx DCA Management System'
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {str(error)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    # Agent status endpoint
    @app.route('/api/agents/status', methods=['GET'])
    def get_agent_status():
        """Get status of all autonomous agents"""
        global agent_orchestrator
        if agent_orchestrator:
            return jsonify(agent_orchestrator.get_status()), 200
        return jsonify({'error': 'Agents not initialized'}), 503
    
    @app.route('/api/agents/trigger/<agent_name>', methods=['POST'])
    def trigger_agent(agent_name):
        """Manually trigger an agent to run"""
        global agent_orchestrator
        if agent_orchestrator:
            try:
                result = agent_orchestrator.run_agent_now(agent_name)
                return jsonify(result), 200
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
        return jsonify({'error': 'Agents not initialized'}), 503
    
    @app.route('/api/agents/activity', methods=['GET'])
    def get_agent_activity():
        """Get recent autonomous agent activity"""
        try:
            from db.mongo import get_db
            db = get_db()
            
            limit = int(request.args.get('limit', 50))
            
            # Get autonomous events
            events = list(db.events.find({'metadata.autonomous': True}).sort('timestamp', -1).limit(limit))
            
            # Format events
            for event in events:
                event['_id'] = str(event['_id'])
                if 'timestamp' in event:
                    event['timestamp'] = event['timestamp'].isoformat()
            
            return jsonify(events), 200
            
        except Exception as e:
            app.logger.error(f"Error fetching agent activity: {str(e)}")
            return jsonify({'error': 'Failed to fetch agent activity'}), 500
    
    app.logger.info("FedEx DCA Management System initialized successfully")
    
    return app

# Create app instance for production (gunicorn)
app = create_app()

if __name__ == '__main__':
    app = create_app()
    
    try:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG
        )
    finally:
        # Graceful shutdown
        if agent_orchestrator:
            agent_orchestrator.stop()
            app.logger.info("Agent system stopped")
