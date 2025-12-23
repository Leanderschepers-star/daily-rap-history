import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

MAIN_APP_URL = "https://daily-rap-app-woyet5jhwynnn9fbrjuvct.streamlit.app" 
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_date = be_now.date()
today_str = today_date.strftime('%d/%m/%Y')

# --- 2. GITHUB ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json()
    except: return None
    return None

def update_github_file(content, msg="Update Content"):
    file_data = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA PARSING & ECONOMY ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

# Map entries to dates
entry_map = {}
for e in entries_raw:
    m = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if m:
        date_str = m.group(1)
        d_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
        if d_obj <= today_date:
            entry_map[date_str] = e

# Streak Logic
unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)
current_streak = 0
if unique_dates:
    if (today_date - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# --- NEW: SHOP & ACHIEVEMENT DEFINITIONS ---
shop_items = {
    "Coffee Machine ☕": 150, 
    "Studio Cat 🐈": 300, 
    "Neon Sign 🏮": 400, 
    "Subwoofer 🔊": 800, 
    "Golden Mic 🎤": 1000,
    "Diamond Grillz 💎": 5000,
    "Private Island 🏝️": 50000
}

achievements = [
    {"id": "first", "name": "Humble Beginnings", "req": len(unique_dates) >= 1, "reward": 50, "desc": "Write your first entry"},
    {"id": "week", "name": "Weekly Grind", "req": current_streak >= 7, "reward": 250, "desc": "Maintain a 7-day streak"},
    {"id": "month", "name": "Consistency King", "req": current_streak >= 30, "reward": 1000, "desc": "30-Day Milestone (Unlocks Platinum Plaque)"},
    {"id": "collector", "name": "The Mogul", "req": len(purchases) >= 5, "reward": 2000, "desc": "Own 5 studio items"}
]

# Points Calculation
bonus_points = sum([a['reward'] for a in achievements if a['id'] in claimed])
spent_points = sum([shop_items.get(p, 0) for p in purchases])
user_points = (len(unique_dates) * 10) + bonus_points - spent_points

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)
    if st.button("🔄 Refresh Data"): st.rerun()

t1, t2, t3, t4 = st.tabs(["🎤 Write", "📜 Vault", "🛒 Shop", "🏆 Goals"])

# TAB 1: DAILY ENTRY
with t1:
    st.header("Today's Session")
    if today_str in entry_map:
        st.success(f"✅ Entry for {today_str} is secure.")
    else:
        lyrics = st.text_area("Drop your bars:", height=250)
        if st.button("🚀 Submit"):
            if lyrics:
                new_entry = f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_entry, f"Entry: {today_str}")
                st.rerun()

# TAB 2: VAULT
with t2:
    st.header("Records")
    for i in range(7):
        target_date = today_date - timedelta(days=i)
        target_str = target_date.strftime('%d/%m/%Y')
        if target_str in entry_map:
            with st.expander(f"📅 {target_str}"):
                content = entry_map[target_str]
                edit_val = st.text_area("Edit:", value=content, height=150, key=f"v_edit_{i}")
                if st.button("Update", key=f"v_btn_{i}"):
                    update_github_file(full_text.replace(content, edit_val))
                    st.rerun()
        else:
            with st.expander(f"❌ {target_str} (Missing)", expanded=False):
                retro = st.text_area("Recover bars:", key=f"v_miss_{i}")
                if st.button("Fix Day", key=f"v_rec_{i}"):
                    update_github_file(f"DATE: {target_str}\nLYRICS:\n{retro}\n" + "-"*30 + "\n" + full_text)
                    st.rerun()

# TAB 3: SHOP
with t3:
    st.header("The Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i % 2]:
            if item in purchases:
                st.write(f"✅ {item} Owned")
            else:
                if st.button(f"Buy {item} ({price} RC)"):
                    if user_points >= price:
                        update_github_file(f"PURCHASE: {item}\n" + full_text)
                        st.rerun()
                    else: st.error("Poor!")

# TAB 4: GOALS & ACHIEVEMENTS
with t4:
    st.header("🏆 Achievement Vault")
    st.write("Complete goals for big bonuses.")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(a['name'])
            st.caption(f"{a['desc']} | Reward: +{a['reward']} RC")
        with c2:
            if a['id'] in claimed:
                st.success("CLAIMED")
            elif a['req']:
                if st.button("CLAIM", key=f"claim_{a['id']}"):
                    update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                    st.rerun()
            else:
                st.button("LOCKED", disabled=True, key=f"lock_{a['id']}")
