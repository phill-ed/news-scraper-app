import csv
import json
import os
from datetime import datetime
from io import StringIO
from flask import send_file, make_response
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from models import Article, Website


class ExportManager:
    """Handles exporting articles to various formats"""
    
    def __init__(self, articles):
        self.articles = articles
    
    def to_csv(self):
        """Export articles to CSV format"""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Title', 'URL', 'Website', 'Category', 'Author',
            'Published Date', 'Scraped At', 'Sentiment', 'Sentiment Score',
            'Content', 'Summary'
        ])
        
        # Data
        for article in self.articles:
            writer.writerow([
                article.id,
                article.title,
                article.url,
                article.website.name if article.website else '',
                article.category or '',
                article.author or '',
                article.published_date.strftime('%Y-%m-%d %H:%M:%S') if article.published_date else '',
                article.scraped_at.strftime('%Y-%m-%d %H:%M:%S') if article.scraped_at else '',
                article.sentiment or '',
                article.sentiment_score or '',
                article.content or '',
                article.summary or ''
            ])
        
        output.seek(0)
        return output.getvalue()
    
    def to_json(self):
        """Export articles to JSON format"""
        data = []
        for article in self.articles:
            data.append({
                'id': article.id,
                'title': article.title,
                'url': article.url,
                'website': article.website.name if article.website else None,
                'category': article.category,
                'author': article.author,
                'published_date': article.published_date.isoformat() if article.published_date else None,
                'scraped_at': article.scraped_at.isoformat() if article.scraped_at else None,
                'sentiment': article.sentiment,
                'sentiment_score': article.sentiment_score,
                'content': article.content,
                'summary': article.summary
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def to_pdf(self):
        """Export articles to PDF format"""
        buffer = StringIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            alignment=TA_JUSTIFY
        )
        
        story = []
        
        # Title
        story.append(Paragraph("News Articles Report", title_style))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"Total Articles: {len(self.articles)}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Articles
        for i, article in enumerate(self.articles):
            # Title
            story.append(Paragraph(f"{i+1}. {article.title}", heading_style))
            
            # Metadata
            meta = []
            if article.website:
                meta.append(f"Source: {article.website.name}")
            if article.category:
                meta.append(f"Category: {article.category}")
            if article.published_date:
                meta.append(f"Date: {article.published_date.strftime('%Y-%m-%d')}")
            if article.sentiment:
                meta.append(f"Sentiment: {article.sentiment.capitalize()} ({article.sentiment_score:.2f})")
            
            if meta:
                story.append(Paragraph(" | ".join(meta), styles['Normal']))
                story.append(Spacer(1, 10))
            
            # Content
            if article.summary:
                story.append(Paragraph(article.summary, normal_style))
            
            # URL
            story.append(Paragraph(f"<link href='{article.url}'>{article.url}</link>", styles['Normal']))
            
            story.append(Spacer(1, 20))
            
            # Page break every 5 articles
            if (i + 1) % 5 == 0 and i < len(self.articles) - 1:
                story.append(PageBreak())
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()


def export_articles_csv(articles):
    """Create CSV export response"""
    exporter = ExportManager(articles)
    csv_data = exporter.to_csv()
    
    response = make_response(csv_data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=articles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response


def export_articles_json(articles):
    """Create JSON export response"""
    exporter = ExportManager(articles)
    json_data = exporter.to_json()
    
    response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=articles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    return response


def export_articles_pdf(articles):
    """Create PDF export response"""
    exporter = ExportManager(articles)
    pdf_data = exporter.to_pdf()
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=articles_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    return response
