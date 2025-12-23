import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

POSSIBLE_REPOS = ["leanderschepers-star/daily-rap-app", "leanderschepers-star/Daily-Rap-App"]
POSSIBLE_FILES = ["streamlit_app.py", "app.py"]
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday
today_str = be_now.strftime('%d/%m/%Y')

# --- 2. THE ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json(), "OK"
        return None, f"{r.status_code}"
    except: return None, "Conn Error"

def get_synced_data():
    for repo in POSSIBLE_REPOS:
        for filename in POSSIBLE_FILES:
            file_json, status = get_github_file(repo, filename)
            if file_json:
                content = base64.b64decode(file_json['content']).decode('utf-8')
                w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
                s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
                m_match = re.search(r"motivation\s*=\s*(\[.*?\])", content, re.DOTALL)
                try:
                    loc = {}
                    if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
                    if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
                    if m_match: exec(f"m_list = {m_match.group(1)}", {}, loc)
                    return loc.get('w_list', []), loc.get('s_list', []), loc.get('m_list', []), "OK", f"{repo}/{filename}"
                except: continue
    return None, None, None, "Error", "None"

def update_github_file(path, content, msg="Update"):
    file_data, _ = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA & CALCULATIONS ---
words, sentences, motivation, sync_status, active_path = get_synced_data()
hist_file, _ = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""

# A. Points Calculation
entries_count = full_text.count("DATE:")
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed_achievements = re.findall(r'CLAIMED: (.*)', full_text)

shop_items = {
    "Studio Cat 🐈": 300,
    "Golden Mic 🎤": 1000,
    "Coffee Machine ☕": 150,
    "Noise Panels 🧊": 500,
    "Subwoofer 🔊": 800,
    "Neon Sign 🏮": 400
}

# B. Streak Logic
dates_found = re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', full_text)
unique_dates = sorted(list(set(dates_found)), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True)
current_streak = 0
if unique_dates:
    last_date = datetime.strptime(unique_dates[0], '%d/%m/%Y')
    if (datetime.strptime(today_str, '%d/%m/%Y') - last_date).days <= 1:
        current_streak = 1
        for i in range(1, len(unique_dates)):
            if (datetime.strptime(unique_dates[i-1], '%d/%m/%Y') - datetime.strptime(unique_dates[i], '%d/%m/%Y')).days == 1:
                current_streak += 1
            else: break

# C. Achievements Definition
achievements = [
    {"id": "first_bar", "name": "First Session", "req": entries_count >= 1, "reward": 50, "desc": "Drop your first set of bars"},
    {"id": "week_warrior", "name": "Week Warrior", "req": current_streak >= 7, "reward": 200, "desc": "Keep a 7-day streak"},
    {"id": "lyric_lord", "name": "Lyric Lord", "req": entries_count >= 30, "reward": 500, "desc": "30 total journal entries"},
    {"id": "fire_streak", "name": "Fire Breathing", "req": current_streak >= 30, "reward": 1000, "desc": "30-day streak milestone"}
]

bonus_points = sum(a['reward'] for a in achievements if a['id'] in claimed_achievements)
spent = sum(shop_items.get(item, 0) for item in purchases)
user_points = (entries_count * 10) + bonus_points - spent

# --- 4. THE UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    st.progress(min(current_streak / 30, 1.0), text="Goal: 30 Day Streak")
    st.divider()
    if sync_status == "OK": st.success("Cloud Connected")

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Write", "📜 History", "🛒 Shop", "🏆 Goals"])

# TAB 1: WRITE
with tab1:
    if words:
        dw = words[day_of_year % len(words)]
        st.header(dw['word'].upper())
        st.info(f"📝 {sentences[day_of_year % len(sentences)]}")
        if today_str in full_text: st.success("Session completed for today!")
        user_lyrics = st.text_area("Drop your bars:", height=250)
        if st.button("🚀 Save Bars"):
            entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{user_lyrics}\n"
            update_github_file(HISTORY_PATH, entry + "------------------------------\n" + full_text)
            st.rerun()

# TAB 2: HISTORY
with tab2:
    st.header("The Vault")
    for e in [x for x in full_text.split("------------------------------") if "DATE:" in x]:
        st.text_area(label=e.split('\n')[0], value=e, height=150)

# TAB 3: SHOP
with tab3:
    st.header("Studio Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i%2]:
            st.subheader(item)
            if item in purchases: st.write("✅ Owned")
            elif st.button(f"Buy for {price}", key=item):
                if user_points >= price:
                    update_github_file(HISTORY_PATH, f"PURCHASE: {item}\n" + full_text)
                    st.rerun()

# TAB 4: GOALS & ACHIEVEMENTS
with tab4:
    st.header("Achievements")
    for a in achievements:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**{a['name']}**")
            st.caption(f"{a['desc']} (Reward: {a['reward']} RC)")
        with col2:
            if a['id'] in claimed_achievements:
                st.write("✅ Claimed")
            elif a['req']:
                if st.button("Claim", key=a['id']):
                    update_github_file(HISTORY_PATH, f"CLAIMED: {a['id']}\n" + full_text)
                    st.rerun()
            else:
                st.write("🔒 Locked")
