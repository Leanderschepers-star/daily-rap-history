import streamlit as st
import datetime
import requests
import base64
import pytz
import re
from datetime import datetime, timedelta

# --- SECTION 1: CONFIGURATION & LOGIC CORE ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
APP_1_REPO = "Leanderschepers-star/daily-rap-app" 
APP_1_FILE = "streamlit_app.py" 
REPO_NAME = "Leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday

def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(path, content, msg="Update"):
    file_data = get_github_file(path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

def get_synced_data():
    """Extracts words/sentences directly from your 1st App code."""
    url = f"https://api.github.com/repos/{APP_1_REPO}/contents/{APP_1_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        try:
            loc = {}
            if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
            if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
            return loc.get('w_list', []), loc.get('s_list', [])
        except: return [], []
    return [], []

def calculate_stats(content):
    if not content: return 0, 0, []
    # Streak Logic
    found_dates = set(re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', content))
    date_objs = {datetime.strptime(d, '%d/%m/%Y').date() for d in found_dates}
    today = be_now.date()
    streak = 0
    curr = today if today in date_objs else (today - timedelta(days=1))
    while curr in date_objs:
        streak += 1
        curr -= timedelta(days=1)
    
    # Points & Spending
    earned = (content.count("DATE:") * 10) + (streak * 5)
    purchases = re.findall(r'PURCHASE: (.*)', content)
    prices = {"Studio Cat": 300, "Neon Layout": 150}
    spent = sum(prices.get(item, 0) for item in purchases)
    return earned - spent, streak, purchases

# --- SECTION 2: DATA BANK (The Sync Hub) ---
words, sentences = get_synced_data()
hist_file = get_github_file(HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""
user_points, user_streak, user_inventory = calculate_stats(full_text)

# ntfy Sync: Only send if not notified today
today_str = be_now.strftime('%d/%m/%Y')
if f"NOTIFIED: {today_str}" not in full_text:
    topic = "rappers_journal_123" 
    headers = {"Title": "🎤 Rap Journal", "Priority": "high", "Click": st.get_option("browser.serverAddress")}
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=f"Streak: {user_streak} days. Get to work!", headers=headers)
        update_github_file(HISTORY_PATH, f"NOTIFIED: {today_str}\n" + full_text, "Notif Logged")
    except: pass

# --- SECTION 3: UI & INTERACTION ---
st.set_page_config(page_title="Studio Pro", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Balance", f"{user_points} RC")
    st.metric("Streak", f"{user_streak} Days")
    
    st.divider()
    st.subheader("🛒 Spend Credits")
    if "Studio Cat" not in user_inventory:
        if st.button(f"Buy Studio Cat (300 RC)", disabled=(user_points < 300)):
            update_github_file(HISTORY_PATH, "PURCHASE: Studio Cat\n" + full_text, "Bought Cat")
            st.rerun()
    else: st.info("🐱 Studio Cat Active")

# Main Interface
st.title("🎤 Daily Lyric Lab")

if "Studio Cat" in user_inventory:
    st.write("🐱 *Your cat is vibing to your flow...*")

# Display Word from Sync
if words:
    dw = words[day_of_year % len(words)]
    st.success(f"**WORD OF THE DAY:** {dw['word'].upper()}")
    st.caption(f"Prompt: {sentences[day_of_year % len(sentences)]}")
else:
    st.warning("🔄 Syncing words from your Daily Rap App...")

# Write and Save
lyrics = st.text_area("Record your bars:", height=250)
if st.button("💾 Save to History"):
    new_entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{lyrics}\n"
    update_github_file(HISTORY_PATH, new_entry + "------------------------------\n" + full_text)
    st.balloons()
    st.rerun()
