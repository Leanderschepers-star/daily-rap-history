import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

# URLs
MAIN_APP_URL = "https://daily-rap-app.streamlit.app" # Change this to your actual Main App URL
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

# TIME
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

def update_github_file(path, content, msg="Update"):
    file_data, _ = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA LOAD ---
hist_file, _ = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""

# A. Calculations
entries_count = full_text.count("DATE:")
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed_achievements = re.findall(r'CLAIMED: (.*)', full_text)

# B. Expanded Shop
shop_items = {
    "Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400,
    "Noise Panels 🧊": 500, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000,
    "Pro Headphones 🎧": 1200, "Synthesizer 🎹": 2000, "Gold Record 📀": 5000,
    "Private Jet 🛩️": 50000, "Recording Mansion 🏰": 100000
}

# C. Streak Logic
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

# D. Dynamic Streak Goal
streak_milestones = [7, 14, 30, 60, 90, 150, 365]
next_streak_goal = next((m for m in streak_milestones if m > current_streak), streak_milestones[-1])

# E. Expanded Achievements
achievements = [
    {"id": "first_bar", "name": "Rookie", "req": entries_count >= 1, "reward": 50, "desc": "First entry"},
    {"id": "streak_7", "name": "Weekly Hustle", "req": current_streak >= 7, "reward": 200, "desc": "7-day streak"},
    {"id": "streak_14", "name": "Fortnight Flame", "req": current_streak >= 14, "reward": 500, "desc": "14-day streak"},
    {"id": "streak_30", "name": "Monthly Legend", "req": current_streak >= 30, "reward": 1500, "desc": "30-day streak"},
    {"id": "entries_50", "name": "Workaholic", "req": entries_count >= 50, "reward": 2000, "desc": "50 total entries"},
    {"id": "whale", "name": "Big Spender", "req": len(purchases) >= 5, "reward": 1000, "desc": "Buy 5 shop items"}
]

bonus_points = sum(a['reward'] for a in achievements if a['id'] in claimed_achievements)
spent = sum(shop_items.get(item, 0) for item in purchases)
user_points = (entries_count * 10) + bonus_points - spent

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

# NAVIGATION TOP BAR
col_nav1, col_nav2 = st.columns([4, 1])
with col_nav2:
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

with st.sidebar:
    st.title("🕹️ Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Current Streak", f"🔥 {current_streak} Days")
    st.write(f"**Next Goal:** {next_streak_goal} Days")
    st.progress(min(current_streak / next_streak_goal, 1.0))
    st.divider()
    if st.button("🔄 Sync Cloud"): st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Write", "📜 History", "🛒 Shop", "🏆 Goals"])

# TAB 1: WRITE (Simplified for brevity)
with tab1:
    st.title("Rap Journal")
    if today_str in full_text: st.success("Bars dropped for today! See you tomorrow.")
    user_lyrics = st.text_area("Drop bars:", height=250)
    if st.button("🚀 Save"):
        update_github_file(HISTORY_PATH, f"DATE: {today_str}\nLYRICS:\n{user_lyrics}\n" + "---" + full_text)
        st.rerun()

# TAB 3: SHOP (Grid)
with tab3:
    st.header("Studio Shop")
    cols = st.columns(3)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i%3]:
            st.write(f"**{item}**")
            st.caption(f"{price} RC")
            if item in purchases: st.write("✅")
            elif user_points >= price:
                if st.button("Buy", key=f"buy_{item}"):
                    update_github_file(HISTORY_PATH, f"PURCHASE: {item}\n" + full_text)
                    st.rerun()
            else: st.button("Locked", disabled=True, key=f"lock_{item}")

# TAB 4: GOALS
with tab4:
    st.header("Achievements")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1: st.write(f"**{a['name']}** ({a['reward']} RC)")
        with c2:
            if a['id'] in claimed_achievements: st.write("Claimed")
            elif a['req']:
                if st.button("Claim", key=f"claim_{a['id']}"):
                    update_github_file(HISTORY_PATH, f"CLAIMED: {a['id']}\n" + full_text)
                    st.rerun()
            else: st.write("🔒")
