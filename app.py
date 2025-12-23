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
today_str = be_now.strftime('%d/%m/%Y')

# --- 2. LOGIC FUNCTIONS ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        return r.json() if r.status_code == 200 else None
    except: return None

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
    return None, None

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

# --- 3. DATA FETCHING ---
words, sentences = get_synced_data()
hist_file = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""
user_points, user_streak, user_inventory = calculate_stats(full_text)

# Rank Logic
if user_streak >= 30: rank = "RAP LEGEND"
elif user_streak >= 7: rank = "PROPHET"
else: rank = "STUDIO ROOKIE"

# ntfy Sync
if f"NOTIFIED: {today_str}" not in full_text:
    topic = "rappers_journal_123" 
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=f"Streak: {user_streak} Days!", 
                      headers={"Title": f"🎤 {rank} Status", "Priority": "high"})
        update_github_file(HISTORY_PATH, f"NOTIFIED: {today_str}\n" + full_text, "Notif Logged")
    except: pass

# --- 4. THE UI (THE PART THAT WAS GONE) ---
st.set_page_config(page_title="Rap Studio", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.write(f"**Current Rank:** {rank}")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"{user_streak} Days")
    st.divider()
    
    st.subheader("🛒 Shop")
    if "Studio Cat" not in user_inventory:
        if st.button(f"Buy Studio Cat (300 RC)", disabled=(user_points < 300)):
            update_github_file(HISTORY_PATH, "PURCHASE: Studio Cat\n" + full_text, "Bought Cat")
            st.rerun()
    else: st.info("🐱 Studio Cat Active")

st.title(f"🎤 {rank} Journal")

# Word Display
if words:
    dw = words[day_of_year % len(words)]
    st.info(f"**WORD OF THE DAY:** {dw['word'].upper()}")
    st.write(f"Prompt: {sentences[day_of_year % len(sentences)]}")
elif words is None:
    st.error("❌ Sync Connection Failed. Check your Token permissions.")
else:
    st.warning("🔄 Waiting for words...")

# Writing Area
user_lyrics = st.text_area("Drop your bars:", height=300)
if st.button("🚀 Save Bars"):
    if words:
        entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{user_lyrics}\n"
        update_github_file(HISTORY_PATH, entry + "------------------------------\n" + full_text)
        st.success("Bars saved!")
        st.rerun()
    else:
        st.error("Cannot save without a word. Check your sync.")
