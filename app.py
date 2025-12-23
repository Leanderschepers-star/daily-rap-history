import streamlit as st
import datetime, requests, base64, pytz, re, random, time
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("GitHub Token missing.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_date = be_now.date()
today_str = today_date.strftime('%d/%m/%Y')

if "test_trigger" not in st.session_state:
    st.session_state["test_trigger"] = False

def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(content, msg="Update Studio Data"):
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
enabled_gear = list(set(re.findall(r'ENABLED_GEAR: (.*)', full_text)))

entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE:\s*(\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr_match = re.search(r'LYRICS:\s*(.*?)(?=\s*---|$)', b, re.DOTALL)
            lyr_content = lyr_match.group(1).strip() if lyr_match else ""
            if lyr_content: entry_map[d_str] = lyr_content

# --- 3. MATH ---
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())

current_streak = 0
check_date = today_date
if today_str not in entry_map: check_date = today_date - timedelta(days=1)
while True:
    d_key = check_date.strftime('%d/%m/%Y')
    if d_key in entry_map and entry_map[d_key].strip():
        current_streak += 1
        check_date -= timedelta(days=1)
    else: break

active_sessions = len([k for k, v in entry_map.items() if v.strip()])
bonus_rc = sum([int(re.search(r'_RC(\d+)', x).group(1)) if "_RC" in x else 0 for x in tasks_done])
user_points = (total_words // 2) + (active_sessions * 10) + bonus_rc

# Updated Shop Items focusing on VISUALS
visual_shop = {
    "Acoustic Foam 🎚️": 150, 
    "LED Strips 🌈": 400, 
    "Gold XLR Cable 🔌": 800, 
    "Classic Rack 📻": 1500,
    "Neon Sign 🏮": 2500
}
user_points -= sum([visual_shop.get(p, 0) for p in purchases])

# --- 4. QUEST LOGIC (FIXED) ---
random.seed(today_str) # Fixed seed per day
dynamic_word_goal = random.choice([50, 75, 100, 125])
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": f"Write {dynamic_word_goal} words", "req": today_word_count >= dynamic_word_goal, "rc": 100},
    {"id": "q_streak", "desc": "Maintain streak (1+)", "req": current_streak >= 1, "rc": 75}
]
daily_tasks = quest_pool # Fixed to 3 specific tasks to ensure chest is reachable

def save_all(theme_to_save=None, gear_to_save=None):
    t = theme_to_save if theme_to_save else active_theme
    g_list = gear_to_save if gear_to_save is not None else enabled_gear
    content = f"ACTIVE_THEME: {t}\n"
    for g in g_list: content += f"ENABLED_GEAR: {g}\n"
    for p in sorted(purchases): content += f"PURCHASE: {p}\n"
    for c in sorted(claimed): content += f"CLAIMED: {c}\n"
    for t_done in sorted(tasks_done): content += f"TASK_DONE: {t_done}\n"
    for d in sorted(entry_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{entry_map[d]}\n------------------------------"
    update_github_file(content)

# --- 5. VISUAL EFFECTS ENGINE ---
# Theme Definitions
themes_css = {
    "Default Dark": "background: #0f0f0f;",
    "Classic Studio 🎙️": """
        background-color: #2c1e1a;
        background-image: repeating-linear-gradient(0deg, transparent, transparent 1px, rgba(0,0,0,0.1) 1px, rgba(0,0,0,0.1) 2px);
        border: 10px solid #3d2b1f;
    """
}

# Gear CSS
foam_active = "Acoustic Foam 🎚️" in enabled_gear
foam_style = """
    background-image: radial-gradient(#1a1a1a 20%, transparent 20%), radial-gradient(#1a1a1a 20%, transparent 20%) !important;
    background-position: 0 0, 10px 10px !important;
    background-size: 20px 20px !important;
    background-color: #050505 !important;
    border: 4px solid #333 !important;
    color: #00ff88 !important;
""" if foam_active else ""

led_active = "LED Strips 🌈" in enabled_gear
led_style = "animation: pulse 2s infinite;" if led_active else ""

gold_active = "Gold XLR Cable 🔌" in enabled_gear
gold_style = "background: linear-gradient(45deg, #ffd700, #b8860b) !important; color: black !important; font-weight: bold;" if gold_active else ""

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    @keyframes pulse {{ 0% {{ box-shadow: 0 0 5px #00ff88; }} 50% {{ box-shadow: 0 0 25px #00ff88; }} 100% {{ box-shadow: 0 0 5px #00ff88; }} }}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} color: white; }}
    .stats-card {{ background: rgba(0, 0, 0, 0.4); padding: 20px; border-radius: 15px; border: 1px solid #444; text-align: center; {led_style} }}
    .quest-item {{ padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #444; background: rgba(255,255,255,0.05); }}
    .done {{ border-left-color: #00ff88; color: #00ff88; background: rgba(0,255,136,0.1); }}
    div[data-baseweb="textarea"] textarea {{ {foam_style} }}
    button[kind="primary"] {{ {gold_style} }}
    .reveal-box {{ text-align: center; padding: 40px; background: #000; border: 5px solid #ffd700; border-radius: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🕹️ STUDIO CONTROL")
    st.metric("Balance", f"{user_points} RC")
    
    st.divider()
    st.subheader("📋 DAILY TASKS")
    tasks_claimed_today = [t for t in daily_tasks if any(t['id'] in x for x in tasks_done if today_str in x)]
    st.progress(len(tasks_claimed_today) / 3)
    
    for t in daily_tasks:
        is_done = any(t['id'] in x for x in tasks_done if today_str in x)
        if is_done: st.markdown(f"<div class='quest-item done'>✅ {t['desc']}</div>", unsafe_allow_html=True)
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"q_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}"); save_all(); st.rerun()
        else: st.markdown(f"<div class='quest-item'>⚪ {t['desc']}</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("🎨 VISUALS")
    unlocked_themes = ["Default Dark"]
    if "day1" in claimed: unlocked_themes.append("Classic Studio 🎙️")
    
    sel_theme = st.selectbox("Current Theme", unlocked_themes, index=unlocked_themes.index(active_theme) if active_theme in unlocked_themes else 0)
    if sel_theme != active_theme:
        save_all(theme_to_save=sel_theme); st.rerun()

    new_gear = []
    for g in visual_shop.keys():
        if g in purchases:
            if st.checkbox(g, value=(g in enabled_gear)): new_gear.append(g)
    if set(new_gear) != set(enabled_gear):
        save_all(gear_to_save=new_gear); st.rerun()

    if st.button("🛠️ Test Chest Animation", use_container_width=True):
        st.session_state["test_trigger"] = True; st.rerun()

# --- 7. MAIN UI ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO</h1>", unsafe_allow_html=True)

# THE CHEST (Visible only when tasks are done or testing)
reveal_placeholder = st.empty()
if st.session_state["test_trigger"] or (len(tasks_claimed_today) == 3 and not any("COMPLETION" in x for x in tasks_done if today_str in x)):
    if reveal_placeholder.button("🎁 OPEN STUDIO CHEST", type="primary", use_container_width=True):
        for stage in ["🔨 BUILDING SAMPLES...", "🎙️ WARMING UP MIC...", "✨ FINALIZING LOOT..."]:
            reveal_placeholder.markdown(f"<div class='reveal-box'><h2>{stage}</h2></div>", unsafe_allow_html=True)
            time.sleep(0.8)
        st.snow()
        if not st.session_state["test_trigger"]:
            tasks_done.append(f"{today_str}_COMPLETION_RC250")
            save_all()
        st.session_state["test_trigger"] = False
        time.sleep(2); st.rerun()

# STAT CARDS
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak} Days</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Session</h3><h2>{today_word_count} Words</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Total</h3><h2>{total_words} Words</h2></div>', unsafe_allow_html=True)

t_rec, t_vau, t_shop, t_car = st.tabs(["✍️ Recording Booth", "📂 The Vault", "🏪 Gear Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area("Write your bars here...", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 SAVE SESSION", type="primary"):
        entry_map[today_str] = lyrics; save_all(); st.rerun()

with t_vau:
    for d, lyr in sorted(entry_map.items(), reverse=True):
        with st.expander(f"📅 {d}"): st.text(lyr)

with t_shop:
    sc = st.columns(2)
    for i, (item, price) in enumerate(visual_shop.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"OWNED: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"shop_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()

with t_car:
    st.header("Achievements & Milestones")
    achs = [
        {"id": "day1", "name": "The Intern", "goal": "Record your 1st session", "target": 1, "curr": active_sessions},
        {"id": "words_500", "name": "Wordsmith", "goal": "Write 500 total words", "target": 500, "curr": total_words},
        {"id": "streak_7", "name": "Dedicated", "goal": "7-Day Streak", "target": 7, "curr": current_streak}
    ]
    for a in achs:
        prog = min(a['curr'] / a['target'], 1.0)
        st.subheader(a['name'])
        st.write(f"Objective: {a['goal']}")
        st.progress(prog)
        if a['id'] in claimed: st.success("Claimed")
        elif prog >= 1.0:
            if st.button(f"Unlock Reward", key=f"ach_{a['id']}"):
                claimed.append(a['id']); save_all(); st.rerun()
