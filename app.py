import streamlit as st
import datetime
import requests
import base64
import pytz
import re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
APP_1_REPO = "Leanderschepers-star/Daily-Rap-App" 
APP_1_FILE = "streamlit_app.py" 
REPO_NAME = "Leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday

# --- 2. GITHUB & STATS HELPERS ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def update_github_file(path, content, msg="Update"):
    file_data = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

def get_synced_data():
    file_json = get_github_file(APP_1_REPO, APP_1_FILE)
    if file_json:
        content = base64.b64decode(file_json['content']).decode('utf-8')
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        try:
            loc = {}
            if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
            if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
            return loc.get('w_list', []), loc.get('s_list', [])
        except: return [], []
    return None, None # Returns None if the connection itself failed

def calculate_stats(content):
    if not content: return 0, 0, []
    found_dates = set(re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', content))
    date_objs = {datetime.strptime(d, '%d/%m/%Y').date() for d in found_dates}
    today = be_now.date()
    streak = 0
    curr = today if today in date_objs else (today - timedelta(days=1))
    while curr in date_objs:
        streak += 1
        curr -= timedelta(days=1)
    earned = (content.count("DATE:") * 10) + (streak * 5)
    purchases = re.findall(r'PURCHASE: (.*)', content)
    prices = {"Studio Cat": 300, "Neon Layout": 150}
    spent = sum(prices.get(item, 0) for item in purchases)
    return earned - spent, streak, purchases
