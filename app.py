import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG & ENGINES ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("GitHub Token missing in Secrets.")
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

# Calculation Logic
current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())

# --- 3. REWARD DEFINITIONS ---
shop_items = {
    "Coffee Machine ☕": 150, "Studio Cat 🐈": 300, 
    "Neon 'VIBE' Sign 🏮": 450, "Bass Subwoofer 🔊": 800, 
    "Smoke Machine 💨": 1200, "Golden Mic 🎤": 2500
}

achievements = [
    {"id": "day1", "name": "First Day", "reward": "Underground UI 🧱", "target": 1, "current": len(db_dates), "unit": "session", "rc": 50},
    {"id": "words_500", "name": "Wordsmith", "reward": "Classic Studio Theme 🎙️", "target": 500, "current": total_words, "unit": "total words", "rc": 300},
    {"id": "week", "name": "Rising Star", "reward": "Blue Booth UI 🟦", "target": 7, "current": current_streak, "unit": "day streak", "rc": 500},
    {"id": "all_tasks_5", "name": "Efficient Producer", "reward": "Neon 'LIVE' Sign 🔴", "target": 5, "current": len([x for x in tasks_done if "COMPLETION" in x]), "unit": "days cleared", "rc": 1000},
]

# Daily Task Logic
daily_tasks = [
    {"id": "t1", "desc": "Record today's session", "req": today_str in entry_map, "rc": 40},
    {"id": "t2", "desc": "Write 60+ words today", "req": today_word_count >= 60, "rc": 60},
    {"id": "t3", "desc": "Check the Vault", "req": "vault_seen" in st.session_state, "rc": 20}
]

# Points calculation (Simplified for performance)
claimed_ach_points = sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points = (len(db_dates) * 10) + ((total_words // 10) * 5) + claimed_ach_points
user_points -= sum([shop_items.get(p, 0) for p in purchases])

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
st.set_page_config(page_title="Leander Studio", layout="wide")
themes = {
    "Default Dark": "background: #0f0f0f;",
    "Underground UI 🧱": "background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url('https://www.transparenttextures.com/patterns/brick-wall.png'); background-color: #1a1a1a;",
    "Classic Studio Theme 🎙️": "background: #1e272e;",
    "Blue Booth UI 🟦": "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);",
    "Gold Vault UI 🟨": "background: radial-gradient(circle, #2b2100 0%, #0f0f0f 100%);"
}

# Gear Styling
live_sign = "border-top: 5px solid #ff0000; box-shadow: 0px 5px 20px #ff0000;" if "Neon 'LIVE' Sign 🔴" in purchases or "all_tasks_5" in claimed else ""

st.markdown(f"""
<style>
    .stApp {{ {themes.get(active_theme, themes['Default Dark'])} {live_sign} }}
    .stats-card {{ background: rgba(255, 255, 255, 0.04); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); text-align: center; }}
    .quest-done {{ color: #00ff88; font-weight: bold; border-left: 4px solid #00ff88; padding-left: 10px; margin: 5px 0; }}
    .quest-pending {{ color: #888; border-left: 4px solid #444; padding-left: 10px; margin: 5px 0; }}
    .quest-ready {{ color: #ffaa00; font-weight: bold; border-left: 4px solid #ffaa00; padding-left: 10px; cursor: pointer; }}
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: QUEST BOARD ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    
    st.divider()
    st.subheader("📋 Daily Quests")
    
    current_tasks_done_today = [t for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done]
    
    for t in daily_tasks:
        t_key = f"{today_str}_{t['id']}"
        if t_key in tasks_done:
            st.markdown(f"<div class='quest-done'>✅ {t['desc']} (+{t['rc']}RC)</div>", unsafe_allow_html=True)
        elif t['req']:
            st.markdown(f"<div class='quest-ready'>⭐ {t['desc']} (Ready!)</div>", unsafe_allow_html=True)
            if st.button(f"Claim {t['rc']} RC", key=f"claim_{t['id']}"):
                tasks_done.append(t_key)
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()
        else:
            st.markdown(f"<div class='quest-pending'>⚪ {t['desc']}</div>", unsafe_allow_html=True)
    
    # BIG COMPLETION REWARD
    if len(current_tasks_done_today) == 3 and f"{today_str}_COMPLETION" not in tasks_done:
        st.balloons()
        if st.button("🎁 CLAIM DAILY CHEST (+100 RC)", use_container_width=True, type="primary"):
            tasks_done.append(f"{today_str}_COMPLETION")
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.rerun()
    elif f"{today_str}_COMPLETION" in tasks_done:
        st.success("🎉 All Daily Tasks Cleared!")

    st.divider()
    available_themes = ["Default Dark"] + [a['reward'] for a in achievements if a['id'] in claimed]
    sel_theme = st.selectbox("Current Theme", available_themes, index=available_themes.index(active_theme) if active_theme in available_themes else 0)
    if sel_theme != active_theme:
        rebuild_and_save(entry_map, purchases, claimed, sel_theme, tasks_done)
        st.rerun()

# --- 6. DASHBOARD ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO</h1>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Words Today</h3><h2>{today_word_count}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Rank</h3><h2>Lv.{len(claimed)+1}</h2></div>', unsafe_allow_html=True)

tabs = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop", "🏆 Career"])

with tabs[0]:
    d_input = st.date_input("Date", value=be_now.date())
    d_str = d_input.strftime('%d/%m/%Y')
    bars = st.text_area("Write lyrics...", value=entry_map.get(d_str, ""), height=350)
    if st.button("🚀 Record Session", use_container_width=True):
        entry_map[d_str] = bars
        rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
        st.rerun()

with tabs[1]:
    st.session_state["vault_seen"] = True
    days = (be_now.date() - START_DATE).days
    for i in range(days + 1):
        dt = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        with st.expander(f"{'✅' if dt in entry_map else '⚪'} {dt}"):
            v_lyr = st.text_area("Edit", value=entry_map.get(dt, ""), key=f"edit_{dt}")
            if st.button("Update", key=f"upd_{dt}"):
                entry_map[dt] = v_lyr
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()

with tabs[2]:
    st.header("Studio Upgrades")
    sc1, sc2 = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with (sc1 if i%2==0 else sc2):
            if item in purchases: st.success(f"OWNED: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"buy_{i}"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                    st.rerun()
                else: st.error("Need more RC!")

with tabs[3]:
    st.header("🏆 Career Milestones")
    for a in achievements:
        prog = min(a['current'] / a['target'], 1.0)
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.subheader(a['name'])
            st.write(f"🎁 Reward: {a['reward']}")
            st.progress(prog)
            st.caption(f"Progress: {a['current']} / {a['target']} {a['unit']}")
        with col_b:
            if a['id'] in claimed: st.success("Claimed")
            elif prog >= 1.0:
                if st.button("Claim Reward", key=f"clm_ach_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                    st.rerun()
            else: st.button("Locked", disabled=True, key=f"lck_{a['id']}")
        st.divider()
