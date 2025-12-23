import streamlit as st
import datetime
import requests
import base64
import pytz
import re
from datetime import datetime, timedelta

# --- 1. CONFIG (MATCHED TO YOUR URL) ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
APP_1_REPO = "Leanderschepers-star/Daily-Rap-App" # Fixed: Capitalized to match GitHub
APP_1_FILE = "streamlit_app.py" 
REPO_NAME = "Leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday

# --- 2. GITHUB & SYNC HELPERS ---
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
    url = f"https://api.github.com/repos/{APP_1_REPO}/contents/{APP_1_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        # Regex to find words/sentences list in your first app
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        try:
            loc = {}
            if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
            if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
            return loc.get('w_list', []), loc.get('s_list', [])
        except: return [], []
    return [], []

# --- 3. THE REWARD & SHOP LOGIC ---
def calculate_stats(content):
    if not content: return 0, 0, []
    # Streak
    found_dates = set(re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', content))
    date_objs = {datetime.strptime(d, '%d/%m/%Y').date() for d in found_dates}
    today = be_now.date()
    streak = 0
    curr = today if today in date_objs else (today - timedelta(days=1))
    while curr in date_objs:
        streak += 1
        curr -= timedelta(days=1)
    
    # Points Calculation
    earned = (content.count("DATE:") * 10) + (streak * 5)
    
    # Check for "Big Verse" Achievement (e.g., more than 50 words in one entry)
    # This is an UNLOCK, not a purchase
    has_big_verse = any(len(v.split()) > 50 for v in content.split("LYRICS:")[1:])

    # Purchases (Deductions)
    purchases = re.findall(r'PURCHASE: (.*)', content)
    prices = {"Studio Cat": 300, "Neon Layout": 150}
    spent = sum(prices.get(item, 0) for item in purchases)
    
    return earned - spent, streak, purchases, has_big_verse

# --- 4. TOP PART & DATA HUB ---
words, sentences = get_synced_data()
hist_file = get_github_file(HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""
user_points, user_streak, user_inventory, achievement_wordsmith = calculate_stats(full_text)

# ntfy Notification (Send once per day)
today_str = be_now.strftime('%d/%m/%Y')
if f"NOTIFIED: {today_str}" not in full_text:
    topic = "rappers_journal_123" # Subscribe to this in your ntfy app
    headers = {
        "Title": "🎤 Time to Rap!",
        "Priority": "high",
        "Click": "https://daily-rap-history.streamlit.app"
    }
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=f"Streak: {user_streak} Days. Don't break it!", headers=headers)
        update_github_file(HISTORY_PATH, f"NOTIFIED: {today_str}\n" + full_text, "Daily Notif Logged")
    except: pass

# --- 5. BOTTOM PART: UI ---
st.set_page_config(page_title="Rap Studio Journal", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Dashboard")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Current Streak", f"{user_streak} Days")
    
    st.divider()
    st.subheader("🏆 Achievements (Unlocks)")
    if user_streak >= 7: st.success("🎖️ 7-Day Warrior")
    if achievement_wordsmith: st.success("✍️ Wordsmith (50+ Words Verse)")
    
    st.divider()
    st.subheader("🛒 Studio Shop (Buy)")
    if "Studio Cat" not in user_inventory:
        if st.button(f"Buy Studio Cat (300 RC)", disabled=(user_points < 300)):
            update_github_file(HISTORY_PATH, "PURCHASE: Studio Cat\n" + full_text, "Spent 300 RC")
            st.rerun()
    else: st.info("🐱 Studio Cat: Active")

st.title("🎤 Daily Lyric Journal")

# Sync Display
if words:
    dw = words[day_of_year % len(words)]
    st.info(f"**WORD OF THE DAY:** {dw['word'].upper()}")
    st.write(f"Prompt: {sentences[day_of_year % len(sentences)]}")
else:
    st.error("🔄 Syncing... If this persists, ensure GITHUB_TOKEN has 'repo' permissions.")

# Writing
lyrics = st.text_area("Write your daily bars here:", height=300)
if st.button("🚀 Save Bars"):
    new_entry = f"DATE: {today_str}\nWORD: {dw['word'] if words else 'N/A'}\nLYRICS:\n{lyrics}\n"
    update_github_file(HISTORY_PATH, new_entry + "------------------------------\n" + full_text)
    st.success("Bars saved to your GitHub History!")
    st.rerun()
