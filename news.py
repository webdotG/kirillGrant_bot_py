import os
import requests
import feedparser
from datetime import datetime
from dotenv import load_dotenv
import logging
from bs4 import BeautifulSoup
import json

logging.basicConfig(level=logging.INFO)
load_dotenv()

class NewsReader:
    def __init__(self):
        self.sources = {
            'RBK': {
                'url': 'https://www.rbc.ru/v10/ajax/get-news-feed/project/rbcnews/lastDate/{last_date}/limit/10',
                'parser': 'rbc'
            },
            'New York Times': {
                'url': 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
                'parser': 'nyt'
            },
            'BBC': {
                'url': 'http://feeds.bbci.co.uk/news/business/rss.xml',
                'parser': 'bbc'
            }
        }

    def get_news(self, source='all', limit=5):
        """Получить новости с ограничением по количеству"""
        news_items = []
        
        if source == 'all':
            for name, config in self.sources.items():
                news_items.extend(self._parse_source(name, config))
        else:
            config = self.sources.get(source)
            if config:
                news_items = self._parse_source(source, config)
        
        sorted_news = sorted(news_items, key=lambda x: x['date'], reverse=True)
        return sorted_news[:limit]

    def _parse_source(self, source_name, config):
        try:
            if config['parser'] == 'rbc':
                return self._parse_rbc(source_name, config)
            elif config['parser'] in ['nyt', 'bbc']:
                return self._parse_rss(source_name, config)
            return []
        except Exception as e:
            logging.error(f"Error parsing {source_name} news: {str(e)}")
            return []

    def _parse_rbc(self, source_name, config):
        """Парсинг новостей RBC"""
        last_date = int(datetime.now().timestamp())
        url = config['url'].format(last_date=last_date)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        news_items = []
        for item in data.get('items', []):
            try:
                html = item.get('html', '')
                soup = BeautifulSoup(html, 'html.parser')
                
                title = soup.find('span', class_='news-feed__item__title')
                url = soup.find('a')['href']
                date_text = soup.find('span', class_='news-feed__item__date-text')
                
                if not all([title, url, date_text]):
                    continue
                
                news_items.append({
                    'title': title.get_text(strip=True),
                    'url': url,
                    'source': source_name,
                    'date': datetime.fromtimestamp(item['publish_date_t'])
                })
            except Exception as e:
                logging.error(f"Error parsing RBC item: {str(e)}")
                continue
                
        return news_items

    def _parse_rss(self, source_name, config):
        """Парсинг RSS-лент"""
        feed = feedparser.parse(config['url'])
        return [{
            'title': entry.title[:200],
            'url': entry.link,
            'source': source_name,
            'date': datetime(*entry.published_parsed[:6])
        } for entry in feed.entries[:10]]

    def format_news(self, news_items):
        """Форматирование новостей для Telegram"""
        messages = []
        current_message = ""
        
        for item in news_items:
            news_line = f"{item['source']}: {item['title']}\n{item['url']}\n\n"
            
            if len(current_message) + len(news_line) > 4000:
                messages.append(current_message)
                current_message = news_line
            else:
                current_message += news_line
                
        if current_message:
            messages.append(current_message)
            
        return messages

def default_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")