# News Scraper App

A comprehensive Python Flask application for scraping, storing, and managing news articles from multiple websites.

## Features

- **Website Management**: Add, edit, and delete news websites with custom CSS selectors
- **Scraping Engine**: Uses requests + BeautifulSoup4 for static content
- **JavaScript Support**: Optional Playwright integration for dynamic content
- **SQLite Database**: Local storage for websites and scraped articles
- **Export Options**: Export articles to CSV, JSON, or PDF
- **Search & Filtering**: Search by keyword, filter by category/website/sentiment
- **Auto-Schedule**: Set up automatic scraping schedules
- **Sentiment Analysis**: Basic keyword-based sentiment analysis
- **Proxy Support**: Configure proxy for scraping
- **Responsive UI**: Modern Bootstrap 5 interface

## Installation

1. Clone the repository:
```bash
git clone https://github.com/phill-ed/news-scraper-app.git
cd news-scraper-app
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright (optional, for JavaScript rendering):
```bash
playwright install chromium
```

5. Run the application:
```bash
python app.py
```

6. Open your browser at `http://localhost:5000`

## Project Structure

```
news-scraper-app/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # Database models
├── scraper.py          # Scraping engine
├── exporters.py        # Export functionality
├── scheduler.py        # Task scheduling
├── templates/          # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── websites.html
│   ├── website_form.html
│   ├── news.html
│   ├── article.html
│   └── schedules.html
├── static/            # Static files
│   ├── css/
│   └── js/
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Usage

### Adding a Website

1. Go to the "Websites" page
2. Click "Add Website"
3. Enter the website name and URL
4. Configure CSS selectors (or use defaults)
5. Optionally enable Playwright, proxy, or auto-scrape
6. Save the website

### Scraping

- **Single Website**: Click "Scrape" on the website card
- **All Websites**: Click "Scrape All" in the sidebar
- **Scheduled**: Enable auto-scrape in website settings

### Viewing Articles

1. Go to "News" to see all articles
2. Use filters to narrow down results
3. Click an article title to view details
4. Bookmark articles for later

### Exporting

Click the export buttons (CSV/JSON/PDF) on the News page to download filtered articles.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/websites` | GET | List all websites |
| `/api/websites` | POST | Create website |
| `/api/websites/<id>` | PUT | Update website |
| `/api/websites/<id>` | DELETE | Delete website |
| `/api/news` | GET | List articles |
| `/api/stats` | GET | Get statistics |

## Configuration

Environment variables can be set in `config.py` or as system environment variables:

- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: Database connection string
- `SCRAPER_TIMEOUT`: Request timeout (seconds)
- `USE_PLAYWRIGHT`: Enable Playwright by default
- `SCHEDULER_ENABLED`: Enable scheduler

## Sentiment Analysis

The app includes basic keyword-based sentiment analysis. Here are alternatives you can implement:

### Option 1: TextBlob (Simple)
```python
from textblob import TextBlob
blob = TextBlob(text)
sentiment = blob.sentiment.polarity  # -1 to 1
```

Install: `pip install textblob`

### Option 2: VADER (Social Media Focused)
```python
from nltk.sentiment.vader import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()
scores = sia.polarity_scores(text)
```

Install: `pip install nltk`

### Option 3: Hugging Face Transformers (Most Accurate)
```python
from transformers import pipeline
classifier = pipeline("sentiment-analysis")
result = classifier(text)[0]
```

Install: `pip install transformers torch`

### Option 4: OpenAI API
```python
import openai
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": f"Analyze sentiment: {text}"}]
)
```

To use any of these, update the `_analyze_sentiment` function in `scraper.py`.

## License

MIT License
