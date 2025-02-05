import os
import requests
import praw
import re
from collections import Counter
from datetime import datetime, timezone

# Retrieve sensitive data from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.environ.get('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.environ.get('REDDIT_USER_AGENT')

ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')

# Function to send a message via Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        print("Telegram message sent successfully!")
    else:
        print(f"Failed to send message. Response: {response.text}")

# Authenticate with Reddit
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

# Define regex for stock tickers (assumes uppercase 1-5 letter words)
TICKER_REGEX = r'\b[A-Z]{1,5}\b'

# Function to get today's posts from a subreddit
def get_today_posts(subreddit_name, limit=500):
    subreddit = reddit.subreddit(subreddit_name)
    today = datetime.now(timezone.utc).date()

    posts = []
    for submission in subreddit.new(limit=limit):  # Fetch recent posts
        post_date = datetime.fromtimestamp(submission.created_utc, timezone.utc).date()
        if post_date == today:
            posts.append(submission.title + " " + submission.selftext)

    print(f"Retrieved {len(posts)} posts from r/{subreddit_name} today.")
    return posts

# Load valid stock tickers (from a public API)
def get_valid_tickers():
    url = f"https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        lines = response.text.split("\n")
        valid_tickers = {line.split(",")[0] for line in lines if line}
        return valid_tickers
    return set()

valid_tickers = get_valid_tickers()

# Filter out common abbreviations and invalid tickers
common_abbreviations = {"DD", "A", "S", "U", "FDA", "ESG", "AI", "I", "PR", "USA", "P", "Q", "T", "B", "M", "YOLO"}  # Add more if necessary

# Function to filter valid tickers (exclude short non-stock abbreviations)
def filter_valid_tickers(tickers, valid_tickers, common_abbreviations):
    filtered_tickers = [t for t in tickers if t in valid_tickers and t not in common_abbreviations]
    return filtered_tickers

# Function to count and print the top mentioned tickers for a given subreddit
def get_top_tickers_text(subreddit_name):
    posts = get_today_posts(subreddit_name)
    
    # Count stock ticker mentions
    all_words = " ".join(posts)
    tickers = re.findall(TICKER_REGEX, all_words)
    
    filtered_tickers = filter_valid_tickers(tickers, valid_tickers, common_abbreviations)
    ticker_counts = Counter(filtered_tickers)
    
    result = f"\nTop mentioned tickers in r/{subreddit_name} today:"
    if ticker_counts:
        for ticker, count in ticker_counts.most_common(10):
            result += f"\n{ticker}: {count}"
    else:
        result += "\nNo valid tickers found."
    
    return result

# Get results for both subreddits and send via Telegram
pennystocks_message = get_top_tickers_text("pennystocks")
wallstreetbets_message = get_top_tickers_text("wallstreetbets")

# Combine the messages
full_message = f"Reddit Stocks Update!\n{pennystocks_message}\n\n{wallstreetbets_message}"

# Send the message
send_telegram_message(full_message)
