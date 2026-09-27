"""
Change Blast Radius Analyzer — Flask Application Entry Point
"""

from flask import Flask
from flask_cors import CORS

from routes.tree import tree_bp
from routes.analyze import analyze_bp
from routes.graph import graph_bp
from routes.symbols import symbols_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register route blueprints
    app.register_blueprint(tree_bp, url_prefix="/api")
    app.register_blueprint(analyze_bp, url_prefix="/api")
    app.register_blueprint(graph_bp, url_prefix="/api")
    app.register_blueprint(symbols_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "blast-radius-analyzer"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
