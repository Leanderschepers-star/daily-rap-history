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
NTFY_TOPIC = "leanders_daily_bars"

be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
START_DATE = datetime(2025, 12, 19).date()

# --- 2. NOTIFICATION ENGINE ---
def send_notif(title, message):
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                     data=message.encode('utf-8'),
                     headers={"Title": title, "Priority": "default", "Tags": "microphone,fire"})
    except:
        pass

# --- 3. GITHUB ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(content, msg="Update"):
    file_data = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 4. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))

entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr = b.split("LYRICS:")[-1].strip() if "LYRICS:" in b else ""
            if lyr: entry_map[d_str] = lyr

valid_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys() if datetime.strptime(d, '%d/%m/%Y').date() >= START_DATE], reverse=True)

# --- 5. STATS & ACHIEVEMENTS ---
current_streak = 0
if valid_dates:
    if (be_now.date() - valid_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(valid_dates)-1):
            if (valid_dates[i] - valid_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
shop_items = {
    "Coffee Machine ☕": 150, 
    "Studio Cat 🐈": 300, 
    "Neon Sign 🏮": 400, 
    "Subwoofer 🔊": 800, 
    "Golden Mic 🎤": 1000
}

achievements = [
    {"id": "first", "name": "Rookie", "desc": "1st Session", "req": len(valid_dates) >= 1, "rc": 50},
    {"id": "week", "name": "Weekly Grind", "desc": "7-day streak", "req": current_streak >= 7, "rc": 250},
    {"id": "month", "name": "Legendary", "desc": "30-day streak", "req": current_streak >= 30, "rc": 500}
]

user_points = (len(valid_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([shop_items.get(p, 0) for p in purchases])

def rebuild_and_save(new_map, new_pur, new_cla):
    content = ""
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 6. DYNAMIC CSS (STREAK BASED) ---
streak_color = "#1E1E1E" # Default Dark
if current_streak >= 30: streak_color = "linear-gradient(135deg, #1e1e1e 0%, #4a3b00 100%)" # Gold glow
elif current_streak >= 7: streak_color = "linear-gradient(135deg, #1e1e1e 0%, #001a33 100%)" # Blue glow

st.set_page_config(page_title="Studio Journal", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background: {streak_color}; }}
    .stats-card {{
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        margin-bottom: 20px;
    }}
</style>
""", unsafe_allow_html=True)

# --- 7. UI ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"{current_streak} Days")
    st.divider()
    st.write("📦 **Studio Inventory**")
    for item in purchases:
        st.caption(f"✅ {item}")
    st.divider()
    if st.button("📢 Test Phone Notif"):
        send_notif("Mic Check!", "Studio connection live.")
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# Top Dashboard
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>📝 Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>🔥 Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>💰 Rap Coins</h3><h2>{user_points}</h2></div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["✍️ New Session", "📂 The Vault", "🏪 Shop", "🏆 Career"])

with t1:
    target_date = st.date_input("Session Date", value=be_now.date())
    d_str = target_date.strftime('%d/%m/%Y')
    new_lyr = st.text_area("Write lyrics...", height=300)
    if st.button("🚀 Record Session"):
        entry_map[d_str] = new_lyr
        rebuild_and_save(entry_map, purchases, claimed)
        send_notif("Bars Saved!", f"Session recorded for {d_str}")
        st.rerun()

with t2:
    st.header("The Vault")
    for day in sorted(entry_map.keys(), reverse=True):
        with st.expander(f"📅 {day}"):
            edt = st.text_area("Edit", value=entry_map[day], height=200, key=f"v_{day}")
            if st.button("💾 Save Changes", key=f"b_{day}"):
                entry_map[day] = edt
                rebuild_and_save(entry_map, purchases, claimed)
                st.rerun()

with t3:
    st.header("Studio Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i%2]:
            if item in purchases: st.success(f"Installed: {item}")
            elif st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed)
                    send_notif("New Equipment!", f"Purchased {item}")
                    st.rerun()

with t4:
    st.header("🏆 Career achievements")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{a['name']}**")
            st.caption(f"{a['desc']} | Reward: {a['rc']} RC")
        with c2:
            if a['id'] in claimed: st.success("Claimed")
            elif a['req']:
                if st.button("Claim", key=f"c_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()
            else: st.write("🔒 Locked")
