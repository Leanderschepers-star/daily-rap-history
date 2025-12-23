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

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())

# --- 3. DYNAMIC QUEST ENGINE ---
# Seed the randomizer with the date so quests are the same for the whole day but change tomorrow
random.seed(today_str)
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": "Write 120+ words", "req": today_word_count >= 120, "rc": 100},
    {"id": "q_vault", "desc": "Check old bars in Vault", "req": "vault_seen" in st.session_state, "rc": 30},
    {"id": "q_shop", "desc": "Browse the Shop", "req": "shop_seen" in st.session_state, "rc": 20},
    {"id": "q_streak", "desc": "Maintain any streak", "req": len(entry_map) > 1, "rc": 40}
]
daily_tasks = random.sample(quest_pool, 3)

# Economics
word_points = total_words // 2
chest_points = len([x for x in tasks_done if "COMPLETION" in x]) * 250
user_points = word_points + chest_points + (len(entry_map) * 20) - (len(purchases) * 300)

def rebuild_and_save(new_map, new_pur, new_cla, new_theme, new_tasks):
    content = f"ACTIVE_THEME: {new_theme}\n"
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for t in sorted(new_tasks): content += f"TASK_DONE: {t}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip():
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. UI ---
st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background: #0f0f0f; }}
    .quest-box {{ background: rgba(255,255,255,0.05); padding:10px; border-radius:10px; border-left: 5px solid #444; margin-bottom:5px; }}
    .quest-ready {{ border-left: 5px solid #ffaa00; background: rgba(255, 170, 0, 0.1); }}
    .quest-done {{ border-left: 5px solid #00ff88; background: rgba(0, 255, 136, 0.1); }}
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR: QUEST LOG & REWARDS ---
with st.sidebar:
    st.header("🎯 Daily Missions")
    st.caption("New quests every 24 hours")
    
    tasks_claimed_today = [t for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done]
    
    for t in daily_tasks:
        t_key = f"{today_str}_{t['id']}"
        is_claimed = t_key in tasks_done
        
        if is_claimed:
            st.markdown(f"<div class='quest-box quest-done'>✅ {t['desc']}<br><small>+ {t['rc']} RC Claimed</small></div>", unsafe_allow_html=True)
        elif t['req']:
            st.markdown(f"<div class='quest-box quest-ready'>⭐ {t['desc']}<br><small>Ready to claim!</small></div>", unsafe_allow_html=True)
            if st.button(f"Claim {t['rc']} RC", key=f"btn_{t['id']}"):
                tasks_done.append(t_key)
                rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
                st.rerun()
        else:
            st.markdown(f"<div class='quest-box'>⚪ {t['desc']}<br><small>Reward: {t['rc']} RC</small></div>", unsafe_allow_html=True)
    
    st.divider()
    # THE BIG REWARD
    if len(tasks_claimed_today) == 3 and f"{today_str}_COMPLETION" not in tasks_done:
        st.warning("🏆 ALL TASKS COMPLETE!")
        if st.button("🎁 OPEN DAILY CHEST", use_container_width=True):
            tasks_done.append(f"{today_str}_COMPLETION")
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.rerun()
    elif f"{today_str}_COMPLETION" in tasks_done:
        st.success("💎 Daily Chest Collected: +250 RC")

# --- 6. TABS ---
t_rec, t_vau, t_shop = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop"])

with t_rec:
    st.subheader("Recording Booth")
    # BUG FIX: We use a form to ensure the data is captured correctly
    with st.form("record_form"):
        d_input = st.date_input("Session Date", value=be_now.date())
        current_bars = entry_map.get(d_input.strftime('%d/%m/%Y'), "")
        new_bars = st.text_area("Drop bars...", value=current_bars, height=300)
        submit = st.form_submit_button("🚀 COMMIT TO VAULT")
        
        if submit:
            entry_map[d_input.strftime('%d/%m/%Y')] = new_bars
            rebuild_and_save(entry_map, purchases, claimed, active_theme, tasks_done)
            st.success("Saved to Vault! Checking tasks...")
            st.rerun()

with t_vau:
    st.session_state["vault_seen"] = True
    st.subheader("The Lyric Vault")
    for d, lyr in sorted(entry_map.items(), reverse=True):
        with st.expander(f"📅 {d} ({len(lyr.split())} words)"):
            st.code(lyr, language="text")

with t_shop:
    st.session_state["shop_seen"] = True
    st.header("Studio Shop")
    st.write(f"Your Balance: {user_points} RC")
    # ... Shop logic remains same ...
