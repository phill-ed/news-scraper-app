from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Website(db.Model):
    """Model for news websites to scrape"""
    __tablename__ = 'websites'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), default='General')
    
    # CSS selectors for scraping
    title_selector = db.Column(db.String(200), default='h1, .title, .article-title')
    date_selector = db.Column(db.String(200), default='time, .date, .published')
    content_selector = db.Column(db.String(200), default='article, .content, .article-content')
    category_selector = db.Column(db.String(200), default='.category, .tag')
    
    # Configuration
    use_playwright = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    proxy_enabled = db.Column(db.Boolean, default=False)
    proxy_http = db.Column(db.String(200), nullable=True)
    proxy_https = db.Column(db.String(200), nullable=True)
    
    # Sentiment analysis method
    sentiment_method = db.Column(db.String(20), default='keyword')  # keyword, textblob, vader, openai
    
    # Schedule settings
    auto_scrape_enabled = db.Column(db.Boolean, default=False)
    scrape_interval = db.Column(db.Integer, default=3600)  # seconds
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = db.relationship('Article', backref='website', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'category': self.category,
            'title_selector': self.title_selector,
            'date_selector': self.date_selector,
            'content_selector': self.content_selector,
            'category_selector': self.category_selector,
            'use_playwright': self.use_playwright,
            'is_active': self.is_active,
            'proxy_enabled': self.proxy_enabled,
            'proxy_http': self.proxy_http,
            'proxy_https': self.proxy_https,
            'sentiment_method': self.sentiment_method,
            'auto_scrape_enabled': self.auto_scrape_enabled,
            'scrape_interval': self.scrape_interval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'article_count': self.articles.count()
        }


class Article(db.Model):
    """Model for scraped articles"""
    __tablename__ = 'articles'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    
    # Article data
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    author = db.Column(db.String(200))
    published_date = db.Column(db.DateTime)
    category = db.Column(db.String(100))
    
    # Additional metadata
    image_url = db.Column(db.String(500))
    sentiment = db.Column(db.String(20))  # positive, negative, neutral
    sentiment_score = db.Column(db.Float)  # -1 to 1
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    is_bookmarked = db.Column(db.Boolean, default=False)
    
    # Timestamps
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'website_name': self.website.name if self.website else None,
            'title': self.title,
            'url': self.url,
            'content': self.content,
            'summary': self.summary,
            'author': self.author,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'category': self.category,
            'image_url': self.image_url,
            'sentiment': self.sentiment,
            'sentiment_score': self.sentiment_score,
            'is_read': self.is_read,
            'is_bookmarked': self.is_bookmarked,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ScrapeLog(db.Model):
    """Model for logging scrape operations"""
    __tablename__ = 'scrape_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=True)
    
    # Log data
    action = db.Column(db.String(50), nullable=False)  # start, success, error
    message = db.Column(db.Text)
    articles_scraped = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    website = db.relationship('Website', backref='scrape_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'website_name': self.website.name if self.website else None,
            'action': self.action,
            'message': self.message,
            'articles_scraped': self.articles_scraped,
            'errors': self.errors,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Schedule(db.Model):
    """Model for scheduled scraping tasks"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    
    # Schedule configuration
    interval_seconds = db.Column(db.Integer, default=3600)
    is_active = db.Column(db.Boolean, default=True)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    
    # Status
    total_runs = db.Column(db.Integer, default=0)
    successful_runs = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    website = db.relationship('Website', backref='schedules')
    
    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'website_name': self.website.name if self.website else None,
            'interval_seconds': self.interval_seconds,
            'is_active': self.is_active,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
