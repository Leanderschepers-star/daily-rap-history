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

# --- 2. ENGINES ---
def send_notif(title, message):
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                     data=message.encode('utf-8'),
                     headers={"Title": title, "Priority": "default", "Tags": "microphone,fire"})
    except: pass

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

# --- 3. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))

entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE:\s*(\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr_match = re.search(r'LYRICS:\s*(.*?)(?=\s*---|$)', b, re.DOTALL)
            lyr = lyr_match.group(1).strip() if lyr_match else ""
            if lyr: entry_map[d_str] = lyr

db_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

# Streak Logic
current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])

# --- 4. THE REWARD ARRAYS ---
shop_items = {
    "Coffee Machine ☕": 150, 
    "Studio Cat 🐈": 300, 
    "Neon Sign 🏮": 450, 
    "Recording 'ON AIR' Sign 🔴": 600,
    "Subwoofer 🔊": 800, 
    "Smoke Machine 💨": 1200,
    "Golden Mic 🎤": 2000
}

achievements = [
    {"id": "first", "name": "Underground Legend", "reward": "Standard UI", "req": len(db_dates) >= 1, "rc": 50},
    {"id": "week", "name": "Rising Star", "reward": "Blue Booth Theme 🟦", "req": current_streak >= 7, "rc": 250},
    {"id": "words_1k", "name": "Lyrical Genius", "reward": "Silver Border Stats 🥈", "req": total_words >= 1000, "rc": 400},
    {"id": "month", "name": "Platinum Artist", "reward": "Gold Vault Theme 🟨", "req": current_streak >= 30, "rc": 1000},
    {"id": "hall_fame", "name": "Hall of Fame", "reward": "Animated Smoke Effect 🌫️", "req": len(db_dates) >= 50, "rc": 2500}
]

# Calculate Points
user_points = (len(db_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([shop_items.get(p, 0) for p in purchases])

def rebuild_and_save(new_map, new_pur, new_cla):
    content = ""
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 5. VISUAL THEME ENGINE (CSS) ---
st.set_page_config(page_title="Studio Dashboard", layout="wide")

# Theme Selection
bg_style = "background: #0f0f0f;"
if "month" in claimed: bg_style = "background: radial-gradient(circle, #2b2100 0%, #0f0f0f 100%);"
elif "week" in claimed: bg_style = "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);"

# Item Effects
neon_css = "text-shadow: 0 0 10px #00d4ff, 0 0 20px #00d4ff;" if "Neon Sign 🏮" in purchases else ""
on_air_css = "border-top: 4px solid #ff0000; box-shadow: 0px 10px 15px -10px #ff0000;" if "Recording 'ON AIR' Sign 🔴" in purchases else ""
sub_css = "animation: shake 0.4s infinite alternate;" if "Subwoofer 🔊" in purchases else ""
smoke_css = "animation: drift 10s infinite linear; opacity: 0.3;" if "Smoke Machine 💨" in purchases or "hall_fame" in claimed else "display:none;"

st.markdown(f"""
<style>
    .stApp {{ {bg_style} }}
    @keyframes shake {{ from {{ transform: translateY(0); }} to {{ transform: translateY(2px); }} }}
    @keyframes drift {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(100%); }} }}
    
    .stats-card {{
        background: rgba(255, 255, 255, 0.03);
        padding: 25px; border-radius: 15px; 
        border: 1px solid {"#c0c0c0" if "words_1k" in claimed else "rgba(255, 255, 255, 0.1)"};
        text-align: center; {sub_css}
    }}
    .header-box {{ {on_air_css} padding: 10px; text-align: center; margin-bottom: 20px; }}
    .neon-text {{ {neon_css} color: white; font-family: 'Courier New', monospace; font-size: 28px; }}
    .smoke-layer {{ position: fixed; top: 0; left: 0; width: 200%; height: 100%; pointer-events: none; z-index: 0; background: url('https://www.transparenttextures.com/patterns/asfalt-dark.png'); {smoke_css} }}
</style>
<div class="smoke-layer"></div>
""", unsafe_allow_html=True)

# --- 6. UI ---
with st.sidebar:
    st.title("🎙️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.divider()
    st.write("🏆 **Career Badges**")
    for a in achievements:
        if a['id'] in claimed: st.success(f"{a['name']}")
    st.divider()
    st.write("📦 **Studio Gear**")
    for item in purchases: st.caption(f"Installed: {item}")
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# Main Dashboard
st.markdown('<div class="header-box"><p class="neon-text">LEANDER STUDIO SYSTEMS</p></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stats-card"><h3>Total Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div class="stats-card"><h3>Active Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div class="stats-card"><h3>Rap Coins</h3><h2>{user_points}</h2></div>', unsafe_allow_html=True)

tabs = st.tabs(["✍️ New Session", "📂 The Vault", "🏪 Studio Shop", "🏆 Career"])

with tabs[0]:
    d_input = st.date_input("Session Date", value=be_now.date())
    d_str = d_input.strftime('%d/%m/%Y')
    lyr_val = entry_map.get(d_str, "")
    if lyr_val: st.info("Loading existing bars for this date...")
    new_bars = st.text_area("Drop bars here...", value=lyr_val, height=350)
    if st.button("🚀 Commit to History"):
        entry_map[d_str] = new_bars
        rebuild_and_save(entry_map, purchases, claimed)
        send_notif("Bars Recorded", f"Session saved for {d_str}")
        st.rerun()

with tabs[1]:
    st.header("The Vault")
    days_to_show = (be_now.date() - START_DATE).days
    for i in range(days_to_show + 1):
        target_dt = be_now.date() - timedelta(days=i)
        day_str = target_dt.strftime('%d/%m/%Y')
        has_data = day_str in entry_map
        with st.expander(f"{'✅' if has_data else '⚪'} {day_str}"):
            v_text = st.text_area("Edit Bars", value=entry_map.get(day_str, ""), key=f"edit_{day_str}")
            if st.button("Update Vault", key=f"btn_{day_str}"):
                entry_map[day_str] = v_text
                rebuild_and_save(entry_map, purchases, claimed)
                st.rerun()

with tabs[2]:
    st.header("Shop Upgrades")
    s_cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with s_cols[i%2]:
            if item in purchases: st.success(f"Installed: {item}")
            elif st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()

with tabs[3]:
    st.header("Career Milestones")
    for a in achievements:
        c_a, c_b = st.columns([3, 1])
        with c_a:
            st.write(f"**{a['name']}**")
            st.caption(f"Unlock: {a['reward']} | Reward: +{a['rc']} RC")
        with c_b:
            if a['id'] in claimed: st.info("Claimed")
            elif a['req']:
                if st.button("Claim", key=f"claim_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()
            else: st.write("🔒 Locked")
