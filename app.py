from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

from config import Config
from models import db, Website, Article, ScrapeLog, Schedule
from scraper import scrape_website, scrape_all_websites
from exporters import export_articles_csv, export_articles_json, export_articles_pdf
from scheduler import init_scheduler, create_schedule, delete_schedule, update_schedule, run_all_schedules

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)

# Initialize scheduler
scheduler_manager = None


@app.before_first_request
def initialize_database():
    """Create database tables"""
    db.create_all()
    
    global scheduler_manager
    scheduler_manager = init_scheduler(app)
    scheduler_manager.start()
    
    # Load existing schedules
    with app.app_context():
        schedules = Schedule.query.filter_by(is_active=True).all()
        for schedule in schedules:
            scheduler_manager.add_job(schedule.id)


# ==================== Routes ====================

@app.route('/')
def index():
    """Dashboard with statistics"""
    # Stats
    total_websites = Website.query.count()
    active_websites = Website.query.filter_by(is_active=True).count()
    total_articles = Article.query.count()
    
    # Recent articles
    recent_articles = Article.query.order_by(Article.scraped_at.desc()).limit(10).all()
    
    # Recent logs
    recent_logs = ScrapeLog.query.order_by(ScrapeLog.created_at.desc()).limit(10).all()
    
    # Sentiment distribution
    sentiment_stats = {
        'positive': Article.query.filter_by(sentiment='positive').count(),
        'neutral': Article.query.filter_by(sentiment='neutral').count(),
        'negative': Article.query.filter_by(sentiment='negative').count(),
    }
    
    # Articles per category
    categories = db.session.query(
        Article.category, 
        db.func.count(Article.id)
    ).group_by(Article.category).all()
    
    return render_template('index.html',
                         total_websites=total_websites,
                         active_websites=active_websites,
                         total_articles=total_articles,
                         recent_articles=recent_articles,
                         recent_logs=recent_logs,
                         sentiment_stats=sentiment_stats,
                         categories=categories)


# ==================== Website Routes ====================

@app.route('/websites')
def websites():
    """List all websites"""
    websites_list = Website.query.all()
    return render_template('websites.html', websites=websites_list)


@app.route('/websites/new', methods=['GET', 'POST'])
def website_new():
    """Add new website"""
    if request.method == 'POST':
        website = Website(
            name=request.form['name'],
            url=request.form['url'],
            category=request.form.get('category', 'General'),
            title_selector=request.form.get('title_selector', 'h1, .title, .article-title'),
            date_selector=request.form.get('date_selector', 'time, .date, .published'),
            content_selector=request.form.get('content_selector', 'article, .content'),
            category_selector=request.form.get('category_selector', '.category, .tag'),
            use_playwright='use_playwright' in request.form,
            is_active='is_active' in request.form,
            proxy_enabled='proxy_enabled' in request.form,
            proxy_http=request.form.get('proxy_http'),
            proxy_https=request.form.get('proxy_https'),
            auto_scrape_enabled='auto_scrape_enabled' in request.form,
            scrape_interval=int(request.form.get('scrape_interval', 3600))
        )
        db.session.add(website)
        db.session.commit()
        
        # Create schedule if auto-scrape enabled
        if website.auto_scrape_enabled and scheduler_manager:
            create_schedule(website.id, website.scrape_interval)
        
        flash('Website added successfully!', 'success')
        return redirect(url_for('websites'))
    
    return render_template('website_form.html', website=None)


@app.route('/websites/<int:id>/edit', methods=['GET', 'POST'])
def website_edit(id):
    """Edit website"""
    website = Website.query.get_or_404(id)
    
    if request.method == 'POST':
        website.name = request.form['name']
        website.url = request.form['url']
        website.category = request.form.get('category', 'General')
        website.title_selector = request.form.get('title_selector', 'h1, .title, .article-title')
        website.date_selector = request.form.get('date_selector', 'time, .date, .published')
        website.content_selector = request.form.get('content_selector', 'article, .content')
        website.category_selector = request.form.get('category_selector', '.category, .tag')
        website.use_playwright = 'use_playwright' in request.form
        website.is_active = 'is_active' in request.form
        website.proxy_enabled = 'proxy_enabled' in request.form
        website.proxy_http = request.form.get('proxy_http')
        website.proxy_https = request.form.get('proxy_https')
        
        old_auto_scrape = website.auto_scrape_enabled
        website.auto_scrape_enabled = 'auto_scrape_enabled' in request.form
        website.scrape_interval = int(request.form.get('scrape_interval', 3600))
        
        db.session.commit()
        
        # Handle schedule changes
        if website.auto_scrape_enabled and not old_auto_scrape:
            if scheduler_manager:
                create_schedule(website.id, website.scrape_interval)
        elif website.auto_scrape_enabled and old_auto_scrape:
            if scheduler_manager:
                update_schedule(
                    Schedule.query.filter_by(website_id=website.id).first().id,
                    interval_seconds=website.scrape_interval
                )
        elif not website.auto_scrape_enabled and old_auto_scrape:
            schedule = Schedule.query.filter_by(website_id=website.id).first()
            if schedule:
                delete_schedule(schedule.id)
        
        flash('Website updated successfully!', 'success')
        return redirect(url_for('websites'))
    
    return render_template('website_form.html', website=website)


@app.route('/websites/<int:id>/delete', methods=['POST'])
def website_delete(id):
    """Delete website"""
    website = Website.query.get_or_404(id)
    
    # Delete associated schedule
    schedule = Schedule.query.filter_by(website_id=id).first()
    if schedule:
        delete_schedule(schedule.id)
    
    db.session.delete(website)
    db.session.commit()
    
    flash('Website deleted successfully!', 'success')
    return redirect(url_for('websites'))


# ==================== Scraping Routes ====================

@app.route('/scrape/<int:website_id>')
def scrape_single(website_id):
    """Scrape a single website"""
    result = scrape_website(website_id)
    
    if result['success']:
        flash(f'Successfully scraped {result["articles_scraped"]} articles!', 'success')
    else:
        flash(f'Error: {result.get("error", "Unknown error")}', 'danger')
    
    return redirect(url_for('websites'))


@app.route('/scrape/all')
def scrape_all():
    """Scrape all active websites"""
    result = scrape_all_websites()
    
    if result['success']:
        flash(f'Scraped {result["total_articles"]} articles from {result["websites_scraped"]} websites!', 'success')
    else:
        flash(f'Errors occurred during scraping', 'warning')
    
    return redirect(url_for('index'))


# ==================== Article Routes ====================

@app.route('/news')
def news():
    """List all articles with filtering and pagination"""
    # Get filter parameters
    website_id = request.args.get('website_id', type=int)
    category = request.args.get('category')
    sentiment = request.args.get('sentiment')
    search = request.args.get('search')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Article.query
    
    if website_id:
        query = query.filter(Article.website_id == website_id)
    
    if category:
        query = query.filter(Article.category == category)
    
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Article.title.ilike(search_term),
                Article.content.ilike(search_term),
                Article.summary.ilike(search_term)
            )
        )
    
    # Order by date
    query = query.order_by(Article.scraped_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=20, error_out=False)
    articles = pagination.items
    
    # Get filter options
    websites = Website.query.filter_by(is_active=True).all()
    categories = db.session.query(Article.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('news.html',
                         articles=articles,
                         pagination=pagination,
                         websites=websites,
                         categories=categories,
                         current_website=website_id,
                         current_category=category,
                         current_sentiment=sentiment,
                         search=search)


@app.route('/article/<int:id>')
def article_detail(id):
    """Show article detail"""
    article = Article.query.get_or_404(id)
    article.is_read = True
    db.session.commit()
    
    return render_template('article.html', article=article)


@app.route('/article/<int:id>/bookmark', methods=['POST'])
def article_bookmark(id):
    """Toggle bookmark"""
    article = Article.query.get_or_404(id)
    article.is_bookmarked = not article.is_bookmarked
    db.session.commit()
    
    return jsonify({'bookmarked': article.is_bookmarked})


# ==================== Export Routes ====================

@app.route('/export/csv')
def export_csv():
    """Export articles to CSV"""
    articles = _get_filtered_articles()
    return export_articles_csv(articles)


@app.route('/export/json')
def export_json():
    """Export articles to JSON"""
    articles = _get_filtered_articles()
    return export_articles_json(articles)


@app.route('/export/pdf')
def export_pdf():
    """Export articles to PDF"""
    articles = _get_filtered_articles()
    return export_articles_pdf(articles)


def _get_filtered_articles():
    """Get filtered articles for export"""
    website_id = request.args.get('website_id', type=int)
    category = request.args.get('category')
    sentiment = request.args.get('sentiment')
    search = request.args.get('search')
    
    query = Article.query
    
    if website_id:
        query = query.filter(Article.website_id == website_id)
    if category:
        query = query.filter(Article.category == category)
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Article.title.ilike(search_term),
                Article.content.ilike(search_term)
            )
        )
    
    return query.order_by(Article.scraped_at.desc()).limit(1000).all()


# ==================== Schedule Routes ====================

@app.route('/schedules')
def schedules():
    """List all schedules"""
    schedules_list = Schedule.query.all()
    return render_template('schedules.html', schedules=schedules_list)


@app.route('/schedules/<int:id>/toggle', methods=['POST'])
def schedule_toggle(id):
    """Toggle schedule active status"""
    schedule = Schedule.query.get_or_404(id)
    schedule.is_active = not schedule.is_active
    db.session.commit()
    
    if scheduler_manager:
        update_schedule(id, is_active=schedule.is_active)
    
    return jsonify({'is_active': schedule.is_active})


@app.route('/schedules/run-all')
def schedules_run_all():
    """Manually run all schedules"""
    results = run_all_schedules()
    
    total = sum(r.get('result', {}).get('articles_scraped', 0) for r in results if 'result' in r)
    flash(f'Ran {len(results)} schedules, scraped {total} articles', 'success')
    
    return redirect(url_for('schedules'))


# ==================== API Routes ====================

@app.route('/api/websites', methods=['GET'])
def api_websites():
    """API: List all websites"""
    websites = Website.query.all()
    return jsonify([w.to_dict() for w in websites])


@app.route('/api/websites', methods=['POST'])
def api_website_create():
    """API: Create website"""
    data = request.json
    website = Website(**data)
    db.session.add(website)
    db.session.commit()
    return jsonify(website.to_dict()), 201


@app.route('/api/websites/<int:id>', methods=['PUT'])
def api_website_update(id):
    """API: Update website"""
    website = Website.query.get_or_404(id)
    data = request.json
    
    for key, value in data.items():
        if hasattr(website, key):
            setattr(website, key, value)
    
    db.session.commit()
    return jsonify(website.to_dict())


@app.route('/api/websites/<int:id>', methods=['DELETE'])
def api_website_delete(id):
    """API: Delete website"""
    website = Website.query.get_or_404(id)
    db.session.delete(website)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/news', methods=['GET'])
def api_news():
    """API: List articles with filters"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Article.query
    
    website_id = request.args.get('website_id', type=int)
    category = request.args.get('category')
    sentiment = request.args.get('sentiment')
    search = request.args.get('search')
    
    if website_id:
        query = query.filter(Article.website_id == website_id)
    if category:
        query = query.filter(Article.category == category)
    if sentiment:
        query = query.filter(Article.sentiment == sentiment)
    if search:
        query = query.filter(Article.title.ilike(f'%{search}%'))
    
    pagination = query.order_by(Article.scraped_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'articles': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@app.route('/api/stats')
def api_stats():
    """API: Get statistics"""
    return jsonify({
        'total_websites': Website.query.count(),
        'active_websites': Website.query.filter_by(is_active=True).count(),
        'total_articles': Article.query.count(),
        'sentiment_distribution': {
            'positive': Article.query.filter_by(sentiment='positive').count(),
            'neutral': Article.query.filter_by(sentiment='neutral').count(),
            'negative': Article.query.filter_by(sentiment='negative').count(),
        }
    })


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
