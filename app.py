import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG & ENGINES ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
START_DATE = datetime(2025, 12, 19).date()

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

# --- 2. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))
current_theme_match = re.search(r'ACTIVE_THEME: (.*)', full_text)
active_theme = current_theme_match.group(1) if current_theme_match else "Default Dark"

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

# Logic
current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])

# --- 3. REWARD & SHOP DEFINITIONS ---
shop_items = {
    "Coffee Machine ☕": 150, 
    "Studio Cat 🐈": 300, 
    "Neon 'VIBE' Sign 🏮": 450, 
    "Bass Subwoofer 🔊": 800, 
    "Smoke Machine 💨": 1200,
    "Golden Mic 🎤": 2500
}

achievements = [
    {"id": "day1", "name": "First Day", "reward": "Underground UI 🧱", "target": 1, "current": len(db_dates), "unit": "session", "rc": 20},
    {"id": "week", "name": "Rising Star", "reward": "Blue Booth UI 🟦", "target": 7, "current": current_streak, "unit": "day streak", "rc": 250},
    {"id": "month", "name": "Platinum", "reward": "Gold Vault UI 🟨", "target": 30, "current": current_streak, "unit": "day streak", "rc": 1000},
]

# Point Calculation
user_points = (len(db_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([shop_items.get(p, 0) for p in purchases])

def rebuild_and_save(new_map, new_pur, new_cla, new_theme):
    content = f"ACTIVE_THEME: {new_theme}\n"
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. VISUAL ENGINE ---
st.set_page_config(page_title="Leander Studio", layout="wide")

# Theme CSS
themes = {
    "Default Dark": "background: #0f0f0f;",
    "Underground UI 🧱": "background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url('https://www.transparenttextures.com/patterns/brick-wall.png'); background-color: #1a1a1a;",
    "Blue Booth UI 🟦": "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);",
    "Gold Vault UI 🟨": "background: radial-gradient(circle, #2b2100 0%, #0f0f0f 100%);"
}

# Gear Effects CSS
neon_fx = "text-shadow: 0 0 10px #00d4ff, 0 0 20px #00d4ff;" if "Neon 'VIBE' Sign 🏮" in purchases else ""
sub_fx = "animation: sub-thump 0.5s infinite alternate;" if "Bass Subwoofer 🔊" in purchases else ""
smoke_fx = "animation: smoke-drift 12s infinite linear; opacity: 0.25;" if "Smoke Machine 💨" in purchases else "display:none;"

st.markdown(f"""
<style>
    .stApp {{ {themes.get(active_theme, themes["Default Dark"])} }}
    @keyframes sub-thump {{ from {{ transform: scale(1); }} to {{ transform: scale(1.01); }} }}
    @keyframes smoke-drift {{ from {{ transform: translateX(-100%); }} to {{ transform: translateX(100%); }} }}
    .stats-card {{
        background: rgba(255, 255, 255, 0.04);
        padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);
        text-align: center; {sub_fx}
    }}
    .neon-title {{ {neon_fx} color: white; text-align: center; font-family: monospace; font-size: 32px; }}
    .smoke-layer {{ position: fixed; top: 0; left: 0; width: 200%; height: 100%; pointer-events: none; z-index: 0; background: url('https://www.transparenttextures.com/patterns/asfalt-dark.png'); {smoke_fx} }}
</style>
<div class="smoke-layer"></div>
""", unsafe_allow_html=True)

# --- 5. UI ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.divider()
    
    # Theme Selector
    available_themes = ["Default Dark"] + [a['reward'] for a in achievements if a['id'] in claimed]
    sel_theme = st.selectbox("Switch Theme", available_themes, index=available_themes.index(active_theme) if active_theme in available_themes else 0)
    if sel_theme != active_theme:
        rebuild_and_save(entry_map, purchases, claimed, sel_theme)
        st.rerun()

    st.divider()
    st.write("📦 **Installed Gear**")
    if not purchases: st.caption("No gear installed yet.")
    for p in purchases: st.success(f"ONLINE: {p}")
    st.divider()
    st.link_button("🔙 Main App", "https://daily-rap-app-woyet5jhwynnn9fbrjuvct.streamlit.app")

st.markdown('<p class="neon-title">LEANDER STUDIO SYSTEMS</p>', unsafe_allow_html=True)

# Stats
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Points</h3><h2>{user_points}</h2></div>', unsafe_allow_html=True)

# Tabs
t1, t2, t3, t4 = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t1:
    d_str = st.date_input("Date").strftime('%d/%m/%Y')
    bars = st.text_area("Write...", value=entry_map.get(d_str, ""), height=300)
    if st.button("🚀 Save Session"):
        entry_map[d_str] = bars
        rebuild_and_save(entry_map, purchases, claimed, active_theme)
        st.rerun()

with t2:
    num_days = (be_now.date() - START_DATE).days
    for i in range(num_days + 1):
        d = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        with st.expander(f"{'✅' if d in entry_map else '⚪'} {d}"):
            edt = st.text_area("Edit", value=entry_map.get(d, ""), key=f"v_{d}")
            if st.button("Update", key=f"b_{d}"):
                entry_map[d] = edt
                rebuild_and_save(entry_map, purchases, claimed, active_theme)
                st.rerun()

with t3:
    st.header("Studio Shop")
    sc1, sc2 = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with (sc1 if i % 2 == 0 else sc2):
            if item in purchases: st.info(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed, active_theme)
                    st.rerun()
                else: st.error("Not enough RC!")

with t4:
    st.header("Career Quests")
    for a in achievements:
        prog = min(a['current'] / a['target'], 1.0)
        col_i, col_s = st.columns([3, 1])
        with col_i:
            st.subheader(a['name'])
            st.write(f"Reward: {a['reward']}")
            if a['id'] not in claimed:
                st.progress(prog)
                st.caption(f"{a['current']} / {a['target']} {a['unit']}")
        with col_s:
            if a['id'] in claimed: st.success("Claimed")
            elif prog >= 1.0:
                if st.button("Claim", key=f"c_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed, active_theme)
                    st.rerun()
            else: st.button("Locked", disabled=True, key=f"l_{a['id']}")
        st.divider()
