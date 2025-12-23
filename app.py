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
# Find the saved theme preference
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

# Streak Logic
current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])

# --- 3. MILESTONE ENGINE ---
achievements = [
    {"id": "day1", "name": "First Day on the Block", "reward": "Underground UI 🧱", "target": 1, "current": len(db_dates), "unit": "session", "rc": 20},
    {"id": "week", "name": "Rising Star", "reward": "Blue Booth UI 🟦", "target": 7, "current": current_streak, "unit": "day streak", "rc": 250},
    {"id": "month", "name": "Platinum Artist", "reward": "Gold Vault UI 🟨", "target": 30, "current": current_streak, "unit": "day streak", "rc": 1000},
]

user_points = (len(db_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([150 for p in purchases]) # Simplified math for example

def rebuild_and_save(new_map, new_pur, new_cla, new_theme):
    content = f"ACTIVE_THEME: {new_theme}\n"
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. THEME & UI ENGINE ---
st.set_page_config(page_title="Studio Dashboard", layout="wide")

# Theme Definitions
themes = {
    "Default Dark": "background: #0f0f0f;",
    "Underground UI 🧱": "background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://www.transparenttextures.com/patterns/brick-wall.png'); background-color: #1a1a1a;",
    "Blue Booth UI 🟦": "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);",
    "Gold Vault UI 🟨": "background: radial-gradient(circle, #2b2100 0%, #0f0f0f 100%);"
}

# Apply selected theme
st.markdown(f"""
<style>
    .stApp {{ {themes.get(active_theme, themes["Default Dark"])} }}
    .stats-card {{
        background: rgba(255, 255, 255, 0.03);
        padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }}
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR THEME SELECTOR ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    
    st.divider()
    st.subheader("🎨 Studio Appearance")
    
    # Check which themes are unlocked
    available_themes = ["Default Dark"]
    for a in achievements:
        if a['id'] in claimed:
            available_themes.append(a['reward'])
    
    selected_theme = st.selectbox("Choose Theme", available_themes, index=available_themes.index(active_theme) if active_theme in available_themes else 0)
    
    if selected_theme != active_theme:
        rebuild_and_save(entry_map, purchases, claimed, selected_theme)
        st.rerun()
    
    st.divider()
    st.write("📦 Installed Gear:")
    for item in purchases: st.caption(f"✅ {item}")

# --- 6. MAIN TABS ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO SYSTEMS</h1>", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Points</h3><h2>{user_points}</h2></div>', unsafe_allow_html=True)

tabs = st.tabs(["✍️ Recording", "📂 Vault", "🏆 Career"])

with tabs[0]:
    d_input = st.date_input("Session Date", value=be_now.date())
    d_str = d_input.strftime('%d/%m/%Y')
    new_bars = st.text_area("Drop bars here...", value=entry_map.get(d_str, ""), height=300)
    if st.button("🚀 Record Session"):
        entry_map[d_str] = new_bars
        rebuild_and_save(entry_map, purchases, claimed, active_theme)
        st.rerun()

with tabs[1]:
    days_to_show = (be_now.date() - START_DATE).days
    for i in range(days_to_show + 1):
        target_dt = be_now.date() - timedelta(days=i)
        day_str = target_dt.strftime('%d/%m/%Y')
        with st.expander(f"{'✅' if day_str in entry_map else '⚪'} {day_str}"):
            v_text = st.text_area("Edit Bars", value=entry_map.get(day_str, ""), key=f"edit_{day_str}")
            if st.button("Update Vault", key=f"btn_{day_str}"):
                entry_map[day_str] = v_text
                rebuild_and_save(entry_map, purchases, claimed, active_theme)
                st.rerun()

with tabs[2]:
    st.header("🏆 Career Quest Log")
    for a in achievements:
        is_claimed = a['id'] in claimed
        is_ready = a['current'] >= a['target']
        progress = min(a['current'] / a['target'], 1.0)
        
        col_info, col_status = st.columns([3, 1])
        with col_info:
            st.subheader(f"{a['name']}")
            st.write(f"🎁 **Reward:** {a['reward']}")
            if not is_claimed:
                st.progress(progress)
                st.caption(f"Goal: {a['current']} / {a['target']} {a['unit']}")
        with col_status:
            if is_claimed: st.success("Unlocked")
            elif is_ready:
                if st.button("Claim Reward", key=a['id']):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed, active_theme)
                    st.rerun()
            else: st.button("Locked", disabled=True, key=f"lock_{a['id']}")
        st.divider()
