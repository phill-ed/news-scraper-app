import requests
from bs4 import BeautifulSoup
import logging
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse

from models import db, Website, Article, ScrapeLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperEngine:
    """Main scraping engine for news articles"""
    
    def __init__(self, website: Website):
        self.website = website
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Configure proxy if enabled
        if website.proxy_enabled and (website.proxy_http or website.proxy_https):
            proxies = {}
            if website.proxy_http:
                proxies['http'] = website.proxy_http
            if website.proxy_https:
                proxies['https'] = website.proxy_https
            self.session.proxies.update(proxies)
    
    def scrape(self) -> Dict:
        """Main method to scrape articles from website"""
        result = {
            'success': False,
            'articles_scraped': 0,
            'errors': []
        }
        
        log = ScrapeLog(website_id=self.website.id, action='start', message='Starting scrape')
        db.session.add(log)
        db.session.commit()
        
        try:
            if self.website.use_playwright:
                articles = self._scrape_with_playwright()
            else:
                articles = self._scrape_with_beautifulsoup()
            
            # Save articles to database
            for article_data in articles:
                existing = Article.query.filter_by(url=article_data['url']).first()
                if not existing:
                    article = Article(website_id=self.website.id, **article_data)
                    db.session.add(article)
                    result['articles_scraped'] += 1
            
            db.session.commit()
            result['success'] = True
            
            log.action = 'success'
            log.message = f'Successfully scraped {result["articles_scraped"]} articles'
            log.articles_scraped = result['articles_scraped']
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error scraping {self.website.name}: {error_msg}")
            result['errors'].append(error_msg)
            
            log.action = 'error'
            log.message = error_msg
            log.errors = error_msg
        
        db.session.commit()
        return result
    
    def _scrape_with_beautifulsoup(self) -> List[Dict]:
        """Scrape using requests + BeautifulSoup"""
        articles = []
        
        response = self.session.get(self.website.url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find article links (common patterns)
        article_links = self._find_article_links(soup)
        
        for link in article_links[:10]:  # Limit to 10 articles per scrape
            try:
                article_url = urljoin(self.website.url, link.get('href', ''))
                if not article_url or article_url == self.website.url:
                    continue
                
                # Scrape individual article
                article = self._scrape_article(article_url)
                if article:
                    articles.append(article)
                
                # Delay between requests
                time.sleep(random.uniform(0.5, 1.5))
                
            except Exception as e:
                logger.warning(f"Error scraping article {link}: {e}")
                continue
        
        return articles
    
    def _scrape_with_playwright(self) -> List[Dict]:
        """Scrape JavaScript-rendered content using Playwright"""
        articles = []
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                try:
                    page.goto(self.website.url, timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=10000)
                    
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    article_links = self._find_article_links(soup)
                    
                    for link in article_links[:10]:
                        try:
                            article_url = urljoin(self.website.url, link.get('href', ''))
                            if not article_url:
                                continue
                            
                            article = self._scrape_article(article_url, use_playwright=True)
                            if article:
                                articles.append(article)
                            
                            time.sleep(random.uniform(0.5, 1.5))
                            
                        except Exception as e:
                            logger.warning(f"Error scraping article: {e}")
                            continue
                            
                finally:
                    browser.close()
                    
        except ImportError:
            logger.error("Playwright not installed. Falling back to BeautifulSoup.")
            return self._scrape_with_beautifulsoup()
        except Exception as e:
            logger.error(f"Playwright error: {e}")
            raise
        
        return articles
    
    def _find_article_links(self, soup: BeautifulSoup) -> List:
        """Find article links on the page"""
        # Common article link patterns
        selectors = [
            'article a',
            '.article-link',
            '.post-link',
            '.news-link',
            'a[href*="/article"]',
            'a[href*="/news"]',
            'a[href*="/post"]',
            'h2 a',
            'h3 a',
        ]
        
        links = []
        for selector in selectors:
            links = soup.select(selector)
            if links:
                break
        
        # Filter valid links
        valid_links = []
        for link in links:
            href = link.get('href', '')
            if href and not href.startswith('#') and not href.startswith('javascript'):
                valid_links.append(link)
        
        return valid_links[:20]  # Limit to 20 links
    
    def _scrape_article(self, url: str, use_playwright: bool = False) -> Optional[Dict]:
        """Scrape individual article"""
        try:
            if use_playwright:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    
                    try:
                        page.goto(url, timeout=30000)
                        page.wait_for_load_state('networkidle', timeout=10000)
                        html = page.content()
                    finally:
                        browser.close()
            else:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                html = response.text
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract article data using configured selectors
            title = self._extract_with_selectors(soup, self.website.title_selector.split(','))
            content = self._extract_with_selectors(soup, self.website.content_selector.split(','))
            date_str = self._extract_with_selectors(soup, self.website.date_selector.split(','))
            category = self._extract_with_selectors(soup, self.website.category_selector.split(','))
            
            # Parse date
            published_date = self._parse_date(date_str)
            
            # Generate summary (first 200 chars of content)
            summary = content[:200] + '...' if len(content) > 200 else content
            
            # Basic sentiment analysis
            sentiment, sentiment_score = self._analyze_sentiment(content)
            
            return {
                'title': title,
                'url': url,
                'content': content,
                'summary': summary,
                'published_date': published_date,
                'category': category,
                'sentiment': sentiment,
                'sentiment_score': sentiment_score
            }
            
        except Exception as e:
            logger.warning(f"Error scraping article {url}: {e}")
            return None
    
    def _extract_with_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Try multiple selectors and return first non-empty result"""
        for selector in selectors:
            selector = selector.strip()
            if not selector:
                continue
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return text
            except:
                continue
        return ''
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        
        # Common date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        # Try to extract date using regex
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\w+ \d{1,2}, \d{4}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                date_str = match.group()
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except:
                        continue
        
        return None
    
    def _analyze_sentiment(self, text: str) -> tuple:
        """Basic sentiment analysis using keyword matching"""
        if not text:
            return 'neutral', 0.0
        
        # Simple keyword-based sentiment
        positive_words = [
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'positive', 'success', 'win', 'best', 'love', 'happy', 'joy',
            'breakthrough', 'achievement', 'improve', 'growth', 'increase'
        ]
        
        negative_words = [
            'bad', 'terrible', 'awful', 'horrible', 'poor', 'worst', 'hate',
            'negative', 'fail', 'failure', 'loss', 'decrease', 'decline',
            'crisis', 'problem', 'issue', 'concern', 'risk', 'danger'
        ]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 'neutral', 0.0
        
        score = (positive_count - negative_count) / total
        
        if score > 0.2:
            return 'positive', score
        elif score < -0.2:
            return 'negative', score
        else:
            return 'neutral', score


def scrape_website(website_id: int) -> Dict:
    """Scrape a specific website by ID"""
    website = Website.query.get(website_id)
    if not website:
        return {'success': False, 'error': 'Website not found'}
    
    scraper = ScraperEngine(website)
    return scraper.scrape()


def scrape_all_websites() -> Dict:
    """Scrape all active websites"""
    websites = Website.query.filter_by(is_active=True).all()
    
    total_scraped = 0
    errors = []
    
    for website in websites:
        try:
            result = scrape_website(website.id)
            if result['success']:
                total_scraped += result['articles_scraped']
            if result.get('errors'):
                errors.extend(result['errors'])
        except Exception as e:
            errors.append(f"{website.name}: {str(e)}")
    
    return {
        'success': True,
        'websites_scraped': len(websites),
        'total_articles': total_scraped,
        'errors': errors
    }
