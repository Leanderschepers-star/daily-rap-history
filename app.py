import streamlit as st
import datetime, requests, base64, pytz, re, random
from datetime import datetime, timedelta

# --- 1. CONFIG & ENGINES ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("GitHub Token missing.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

# Ensure we are using your local time correctly
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_str = be_now.strftime('%d/%m/%Y')

# This is the date you started your journey
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

# Extract saved data
purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))
tasks_done = list(set(re.findall(r'TASK_DONE: (.*)', full_text)))
active_theme = re.search(r'ACTIVE_THEME: (.*)', full_text).group(1) if "ACTIVE_THEME:" in full_text else "Default Dark"

entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE:\s*(\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr_match = re.search(r'LYRICS:\s*(.*?)(?=\s*---|$)', b, re.DOTALL)
            entry_map[d_str] = lyr_match.group(1).strip() if lyr_match else ""

# --- 3. STATS CALCULATION ---
db_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

# Correct Streak Logic
current_streak = 0
if db_dates:
    # If the latest entry is today or yesterday, start counting
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1:
                current_streak += 1
            else:
                break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())

# RC ECONOMY RESTORED (1 point per 2 words + bonuses)
word_points = total_words // 2
session_points = len(entry_map) * 20
chest_points = len([x for x in tasks_done if "COMPLETION" in x]) * 250
ach_points = len(claimed) * 500 # Estimate per achievement

user_points = word_points + session_points + chest_points + ach_points
user_points -= (len(purchases) * 300) # Subtract gear costs

# --- 4. DYNAMIC QUESTS ---
random.seed(today_str)
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": "Write 100+ words", "req": today_word_count >= 100, "rc": 100},
    {"id": "q_vault", "desc": "Review the Vault", "req": "vault_seen" in st.session_state, "rc": 30},
    {"id": "q_shop", "desc": "Visit the Shop", "req": "shop_seen" in st.session_state, "rc": 20}
]
daily_tasks = random.sample(quest_pool, 3)

def rebuild_and_save(new_map, new_pur, new_cla, new_theme, new_tasks):
    content = f"ACTIVE_THEME: {new_theme}\n"
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for t in sorted(new_tasks): content += f"TASK_DONE: {t}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 5. UI DESIGN ---
st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown("""
<style>
    .stApp { background: #0f0f0f; color: white; }
    .stats-card { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); text-align: center; margin-bottom: 10px; }
    .quest-box { background: rgba(255,255,255,0.03); padding:10px; border-radius:8px; border-left: 4px solid #444; margin-bottom:8px; }
    .quest-ready { border-left-color: #ffaa00; background: rgba(255, 170, 0, 0.05); }
    .quest-done { border-left-color: #00ff88; background: rgba(0, 255, 136, 0.05); color: #00ff88; }
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR: QUEST BOARD ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet Balance", f"{user_points} RC")
    st.divider()
    
    st.subheader("📋 Daily Missions")
    tasks_claimed_today = [t for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done]
    
    for t in daily_tasks:
        t_key = f"{today_str}_{t['id']}"
        if t_key in tasks_done:
            st.markdown(f"<div class='quest-box quest-done'>✅ {t['desc']}</div>", unsafe_allow_html=True)
        elif t['req']:
            st.markdown(f"<div class='quest-box quest-ready'>⭐ {t['desc']} (Ready!)</div>", unsafe_allow_html=True)
            if st.button(f"Claim {t['rc']} RC", key=f"c_{t['id']}"):
                tasks_done.append(t_key)
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()
        else:
            st.markdown(f"<div class='quest-box'>⚪ {t['desc']}</div>", unsafe_allow_html=True)
    
    if len(tasks_claimed_today) == 3 and f"{today_str}_COMPLETION" not in tasks_done:
        if st.button("🎁 CLAIM DAILY CHEST (+250 RC)", use_container_width=True):
            tasks_done.append(f"{today_str}_COMPLETION")
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.rerun()

# --- 7. MAIN DASHBOARD ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO SYSTEMS</h1>", unsafe_allow_html=True)

# THE THREE CARDS ARE BACK:
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak} Days</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Words Today</h3><h2>{today_word_count}</h2><p>Goal: 100</p></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Rank</h3><h2>Lv.{len(claimed)+1}</h2></div>', unsafe_allow_html=True)

tabs = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop", "🏆 Career"])

with tabs[0]:
    with st.form("record_session"):
        d_input = st.date_input("Session Date", value=be_now.date())
        current_text = entry_map.get(d_input.strftime('%d/%m/%Y'), "")
        new_text = st.text_area("Write your lyrics...", value=current_text, height=350)
        if st.form_submit_button("🚀 SAVE TO VAULT"):
            entry_map[d_input.strftime('%d/%m/%Y')] = new_text
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.rerun()

with tabs[1]:
    st.session_state["vault_seen"] = True
    st.subheader("Your Catalog")
    # Show the entries sorted by newest first
    for date in sorted(entry_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        with st.expander(f"📅 {date} - {len(entry_map[date].split())} words"):
            st.text(entry_map[date])

with tabs[2]:
    st.session_state["shop_seen"] = True
    st.header("Studio Equipment")
    # Shop items...

with tabs[3]:
    st.header("Career Milestones")
    # Achievement logic...
