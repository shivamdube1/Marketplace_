import os
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fabric-bazaar-secret-2025'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    PRODUCTS_PER_PAGE = 12
    BRAND_NAME    = 'FabricBazaar'
    BRAND_TAGLINE = 'India\'s Fabric Marketplace'
    CURRENCY      = 'INR'
    CURRENCY_SYMBOL = '₹'
    RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_SPBHWeZf5cvbyY')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'Qt6KtjlDp8i6IhZ6BhAT9D41')
    RAZORPAY_UPI_ID     = os.environ.get('RAZORPAY_UPI_ID', 'shivamsurajdube')

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
        f'sqlite:///{os.path.join(BASE_DIR, "fabricbazaar_dev.db")}')

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
        f'sqlite:///{os.path.join(BASE_DIR, "fabricbazaar_prod.db")}')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
