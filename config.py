import os
from datetime import timedelta

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///news_scraper.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Scraping settings
    SCRAPER_TIMEOUT = int(os.environ.get('SCRAPER_TIMEOUT', 30))
    SCRAPER_MAX_RETRIES = int(os.environ.get('SCRAPER_MAX_RETRIES', 3))
    SCRAPER_DELAY = float(os.environ.get('SCRAPER_DELAY', 1.0))  # seconds between requests
    
    # Playwright settings
    USE_PLAYWRIGHT = os.environ.get('USE_PLAYWRIGHT', 'false').lower() == 'true'
    PLAYWRIGHT_TIMEOUT = int(os.environ.get('PLAYWRIGHT_TIMEOUT', 30000))
    
    # Proxy settings
    PROXY_ENABLED = os.environ.get('PROXY_ENABLED', 'false').lower() == 'true'
    PROXY_HTTP = os.environ.get('PROXY_HTTP', '')
    PROXY_HTTPS = os.environ.get('PROXY_HTTPS', '')
    
    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))
    
    # Scheduler
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true'
    SCHEDULER_INTERVAL = int(os.environ.get('SCHEDULER_INTERVAL', 3600))  # 1 hour default
    
    # Export settings
    EXPORT_FOLDER = os.environ.get('EXPORT_FOLDER', 'exports')
    MAX_EXPORT_RECORDS = int(os.environ.get('MAX_EXPORT_RECORDS', 10000))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'scraper.log')
    
    # Sentiment analysis
    SENTIMENT_ENABLED = os.environ.get('SENTIMENT_ENABLED', 'true').lower() == 'true'
