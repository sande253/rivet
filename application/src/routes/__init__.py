from flask import Flask


def register_blueprints(app: Flask) -> None:
    from .auth import auth_bp
    from .ui import ui_bp
    from .analysis import analysis_bp
    from .market import market_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(admin_bp)
