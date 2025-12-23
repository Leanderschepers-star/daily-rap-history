import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG & ENGINES ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets found in wrong place or missing.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
START_DATE = datetime(2025, 12, 19).date()
today_str = be_now.strftime('%d/%m/%Y')

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
# Track daily task completion in the file: TASK_DONE: 23/12/2025_1
tasks_done = list(set(re.findall(r'TASK_DONE: (.*)', full_text)))

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

# Stats
current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())

# --- 3. DAILY TASKS & CAREER ---
# Define tasks for today
daily_tasks = [
    {"id": "t1", "desc": "Record a Daily Session", "req": today_str in entry_map, "rc": 30},
    {"id": "t2", "desc": "Write at least 50 words today", "req": today_word_count >= 50, "rc": 50},
    {"id": "t3", "desc": "Visit the Vault", "req": "vault_visited" in st.session_state, "rc": 20}
]

completed_today_count = sum(1 for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done)

achievements = [
    {"id": "day1", "name": "First Day", "reward": "Underground UI 🧱", "target": 1, "current": len(db_dates), "unit": "session", "rc": 20},
    {"id": "words_500", "name": "Wordsmith", "reward": "Classic Studio Theme 🎙️", "target": 500, "current": total_words, "unit": "total words", "rc": 300},
    {"id": "week", "name": "Rising Star", "reward": "Blue Booth UI 🟦", "target": 7, "current": current_streak, "unit": "day streak", "rc": 250},
    {"id": "all_tasks_5", "name": "Efficient Producer", "reward": "Neon 'LIVE' Sign 🔴", "target": 5, "current": len([x for x in tasks_done if "COMPLETION" in x]), "unit": "full days cleared", "rc": 500},
]

# Balance calculation
user_points = (len(db_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points += sum([30 for x in tasks_done if "t1" in x]) # Rough estimate for simplicity
user_points -= sum([150 for p in purchases])

def rebuild_and_save(new_map, new_pur, new_cla, new_theme, new_tasks):
    content = f"ACTIVE_THEME: {new_theme}\n"
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for t in sorted(new_tasks): content += f"TASK_DONE: {t}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. THEME & UI ---
st.set_page_config(page_title="Studio Dashboard", layout="wide")
themes = {
    "Default Dark": "background: #0f0f0f;",
    "Underground UI 🧱": "background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://www.transparenttextures.com/patterns/brick-wall.png'); background-color: #1a1a1a;",
    "Classic Studio Theme 🎙️": "background: #2c3e50;",
    "Blue Booth UI 🟦": "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);"
}

st.markdown(f"<style>.stApp {{ {themes.get(active_theme, themes['Default Dark'])} }} .stats-card {{ background: rgba(255, 255, 255, 0.04); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); text-align: center; }} </style>", unsafe_allow_html=True)

# --- 5. SIDEBAR & DASHBOARD ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    
    st.subheader("📋 Daily Quests")
    for t in daily_tasks:
        done = f"{today_str}_{t['id']}" in tasks_done
        if done:
            st.write(f"✅ ~~{t['desc']}~~")
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"btn_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}")
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()
        else:
            st.write(f"⚪ {t['desc']}")
            
    # Check if all 3 are done to claim a "Day Clear"
    daily_completion_id = f"{today_str}_COMPLETION"
    if sum(1 for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done) == 3 and daily_completion_id not in tasks_done:
        if st.button("🎁 CLAIM DAILY CHEST", use_container_width=True):
            tasks_done.append(daily_completion_id)
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.rerun()

    st.divider()
    available_themes = ["Default Dark"] + [a['reward'] for a in achievements if a['id'] in claimed]
    sel_theme = st.selectbox("Switch Theme", available_themes, index=available_themes.index(active_theme) if active_theme in available_themes else 0)
    if sel_theme != active_theme:
        rebuild_and_save(entry_map, purchases, claimed, sel_theme, tasks_done)
        st.rerun()

# --- 6. MAIN CONTENT ---
st.markdown("<h2 style='text-align:center;'>LEANDER STUDIO SYSTEMS</h2>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Words Today</h3><h2>{today_word_count}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Studio Rank</h3><h2>Lv.{len(claimed)+1}</h2></div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t1:
    d_str = st.date_input("Date").strftime('%d/%m/%Y')
    bars = st.text_area("Write...", value=entry_map.get(d_str, ""), height=300)
    if st.button("🚀 Save Session"):
        entry_map[d_str] = bars
        rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
        st.rerun()

with t2:
    st.session_state["vault_visited"] = True # Triggers the daily task
    days_to_show = (be_now.date() - START_DATE).days
    for i in range(days_to_show + 1):
        d = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        with st.expander(f"{'✅' if d in entry_map else '⚪'} {d}"):
            edt = st.text_area("Edit", value=entry_map.get(d, ""), key=f"v_{d}")
            if st.button("Update", key=f"b_{d}"):
                entry_map[d] = edt
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()

with t3:
    st.header("Studio Shop")
    st.write("Purchased Gear adds permanent animations to your Studio.")
    # (Shop code same as before...)

with t4:
    st.header("🏆 Career Achievements")
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
                if st.button("Claim Reward", key=f"c_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                    st.rerun()
            else: st.button("Locked", disabled=True)
        st.divider()
