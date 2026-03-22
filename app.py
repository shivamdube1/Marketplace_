from datetime import datetime
import os
from flask import Flask, render_template, request
from config import config
from extensions import db, login_manager, bcrypt, migrate, csrf, limiter


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Run config-level init if defined (e.g. production warnings)
    cfg = config[config_name]
    if hasattr(cfg, 'init_app'):
        cfg.init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please sign in to continue.'
    login_manager.login_message_category = 'info'

    # ── Security Headers ──────────────────────────────────────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        # Basic CSP — tighten per-environment as needed
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://checkout.razorpay.com https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.razorpay.com; "
            "frame-src https://api.razorpay.com https://checkout.razorpay.com;"
        )
        return response

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.main      import main_bp
    from routes.auth      import auth_bp
    from routes.shop      import shop_bp
    from routes.cart      import cart_bp
    from routes.checkout  import checkout_bp
    from routes.admin     import admin_bp
    from routes.company   import company_bp
    from routes.ratings   import ratings_bp
    from routes.analytics import analytics_bp
    from routes.messaging import msg_bp
    from routes.buyer     import buyer_bp
    from routes.tracking  import tracking_bp
    from routes.delivery  import delivery_bp
    from routes.wishlist  import wishlist_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(shop_bp,      url_prefix='/shop')
    app.register_blueprint(cart_bp,      url_prefix='/cart')
    app.register_blueprint(checkout_bp,  url_prefix='/checkout')
    app.register_blueprint(admin_bp,     url_prefix='/admin')
    app.register_blueprint(company_bp,   url_prefix='/company')
    app.register_blueprint(ratings_bp,   url_prefix='/rate')
    app.register_blueprint(analytics_bp)
    app.register_blueprint(msg_bp)
    app.register_blueprint(buyer_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(delivery_bp)
    app.register_blueprint(wishlist_bp)

    # ── Error Handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f'Server Error: {e}')
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    # ── Context Processors ────────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from routes.cart import _get_cart_count
        from models.category import Category
        from models.company import Company
        from flask_login import current_user

        cart_count = _get_cart_count()
        categories = Category.query.order_by(Category.sort_order).all()
        pending_companies_count = Company.query.filter_by(
            is_verified=False, is_active=True).count()

        unread_messages = 0
        try:
            if current_user.is_authenticated:
                from models.messaging import MessageThread
                if current_user.is_customer:
                    unread_messages = db.session.query(
                        db.func.sum(MessageThread.unread_customer)
                    ).filter_by(customer_id=current_user.id).scalar() or 0
                elif current_user.is_company and current_user.company:
                    unread_messages = db.session.query(
                        db.func.sum(MessageThread.unread_seller)
                    ).filter_by(company_id=current_user.company.id).scalar() or 0
        except Exception:
            pass

        return {
            'cart_count':              cart_count,
            'categories':              categories,
            'brand_name':              app.config['BRAND_NAME'],
            'brand_tagline':           app.config['BRAND_TAGLINE'],
            'currency_symbol':         app.config['CURRENCY_SYMBOL'],
            'pending_companies_count': pending_companies_count,
            'now':                     datetime.utcnow(),
            'unread_messages':         int(unread_messages),
            'current_year':            datetime.utcnow().year,
        }

    # ── Template Filters ──────────────────────────────────────────────────────
    @app.template_filter('inr')
    def inr_filter(value):
        try:
            v = float(value)
            if v >= 10000000: return f'₹{v/10000000:.2f}Cr'
            if v >= 100000:   return f'₹{v/100000:.2f}L'
            if v >= 1000:     return f'₹{int(v):,}'
            return f'₹{v:.0f}'
        except (TypeError, ValueError):
            return f'₹{value}'

    return app


def _run_safe_migrations(app):
    """Add any missing columns to existing DB without dropping data."""
    with app.app_context():
        from sqlalchemy import text, inspect
        engine = db.engine
        inspector = inspect(engine)

        NEEDED = [
            ('orders',     'delivered_at',
             'ALTER TABLE orders ADD COLUMN delivered_at DATETIME'),
            ('orders',     'is_cod_flagged',
             'ALTER TABLE orders ADD COLUMN is_cod_flagged BOOLEAN DEFAULT 0'),
            ('categories', 'icon',
             "ALTER TABLE categories ADD COLUMN icon VARCHAR(16) DEFAULT '🧵'"),
        ]

        with engine.connect() as conn:
            for table, col, ddl in NEEDED:
                if ddl is None:
                    continue
                try:
                    cols = [c['name'] for c in inspector.get_columns(table)]
                    if col not in cols:
                        conn.execute(text(ddl))
                        conn.commit()
                        print(f'  ✓ Added column {table}.{col}')
                except Exception as e:
                    print(f'  ! Migration warning ({table}.{col}): {e}')


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
    _run_safe_migrations(app)
    app.run(debug=True, host='0.0.0.0', port=5000)
