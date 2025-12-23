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

# Updated Shop: Focused on SIDEBAR (Studio Rack) Customization
sidebar_customs = {
    "Brushed Steel Rack 🏗️": 500,
    "Wooden Side-Panels 🪵": 800,
    "Analog VU Meters 📈": 1200,
    "Neon Rack Glow 🟣": 2000,
}
# Gear remains from before
gear_items = {"Acoustic Foam 🎚️": 150, "LED Strips 🌈": 400, "Gold XLR Cable 🔌": 800}
all_shop = {**sidebar_customs, **gear_items}

user_points -= sum([all_shop.get(p, 0) for p in purchases])

# --- 4. QUEST LOGIC (STABILIZED) ---
random.seed(today_str)
dynamic_word_goal = random.choice([50, 100, 150, 200])
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": f"Write {dynamic_word_goal} words", "req": today_word_count >= dynamic_word_goal, "rc": 100},
    {"id": "q_streak", "desc": "Maintain streak (1+)", "req": current_streak >= 1, "rc": 75}
]
daily_tasks = quest_pool

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

# --- 5. VISUAL ENGINE ---
# Restore "Blueprint" Classic Studio Theme
themes_css = {
    "Default Dark": "background: #0f0f0f;",
    "Classic Studio 🎙️": """
        background-color: #1a1e23;
        background-image: linear-gradient(0deg, #23282e 1px, transparent 1px), linear-gradient(90deg, #23282e 1px, transparent 1px);
        background-size: 40px 40px;
        color: #d1d8e0;
    """
}

# Sidebar Rack Styles
rack_bg = "#111"
rack_border = "1px solid #333"
if "Brushed Steel Rack 🏗️" in purchases: 
    rack_bg = "linear-gradient(180deg, #2c3e50, #000000)"
    rack_border = "2px solid #95a5a6"
if "Wooden Side-Panels 🪵" in purchases:
    rack_border = "8px solid #5d4037"

rack_glow = "box-shadow: inset 0 0 15px purple;" if "Neon Rack Glow 🟣" in purchases else ""

# Gear Styles
foam_style = "background: repeating-conic-gradient(#000 0% 25%, #111 0% 50%) 50% / 20px 20px !important; color: #fff !important;" if "Acoustic Foam 🎚️" in enabled_gear else ""
led_style = "animation: blink 1.5s infinite;" if "LED Strips 🌈" in enabled_gear else ""
gold_style = "background: #d4af37 !important; color: black !important;" if "Gold XLR Cable 🔌" in enabled_gear else ""

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    @keyframes blink {{ 0% {{ opacity: 0.6; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.6; }} }}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} }}
    
    /* Sidebar / Studio Rack Styling */
    section[data-testid="stSidebar"] {{
        background: {rack_bg} !important;
        border-right: {rack_border} !important;
        {rack_glow}
    }}

    .stats-card {{ background: rgba(0, 0, 0, 0.6); padding: 20px; border-radius: 10px; border: 1px solid #444; text-align: center; {led_style} }}
    div[data-baseweb="textarea"] textarea {{ {foam_style} }}
    button[kind="primary"] {{ {gold_style} }}
    
    /* VU Meter Simulation */
    .vu-meter {{ height: 10px; background: linear-gradient(90deg, green 70%, yellow 85%, red 100%); border-radius: 5px; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR (The Rack) ---
with st.sidebar:
    st.title("🎚️ STUDIO RACK")
    
    if "Analog VU Meters 📈" in purchases:
        st.write("Input Level")
        st.markdown('<div class="vu-meter"></div>', unsafe_allow_html=True)
    
    st.metric("Budget", f"{user_points} RC")
    
    st.divider()
    st.subheader("📋 QUEST LOG")
    tasks_claimed_today = [t for t in daily_tasks if any(t['id'] in x for x in tasks_done if today_str in x)]
    st.progress(len(tasks_claimed_today) / 3)
    
    for t in daily_tasks:
        is_done = any(t['id'] in x for x in tasks_done if today_str in x)
        if is_done: st.success(f"✅ {t['desc']}")
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"q_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}"); save_all(); st.rerun()
        else: st.info(f"⚪ {t['desc']}")

    st.divider()
    st.subheader("⚙️ SETTINGS")
    unlocked_themes = ["Default Dark"]
    if "day1" in claimed: unlocked_themes.append("Classic Studio 🎙️")
    
    sel_theme = st.selectbox("Theme", unlocked_themes, index=unlocked_themes.index(active_theme) if active_theme in unlocked_themes else 0)
    if sel_theme != active_theme:
        save_all(theme_to_save=sel_theme); st.rerun()

    # Fixed Gear Logic - No more selection reset
    st.write("**Enabled Gear**")
    for g in gear_items.keys():
        if g in purchases:
            # We display status, but logic remains locked to what's in history.txt
            st.caption(f"✔️ {g} Active")

    if st.button("🎁 Test Chest", use_container_width=True):
        st.session_state["test_trigger"] = True; st.rerun()

# --- 7. MAIN UI ---
st.markdown("<h1 style='text-align:center;'>STUDIO CONSOLE</h1>", unsafe_allow_html=True)

# THE CHEST
reveal_placeholder = st.empty()
if st.session_state["test_trigger"] or (len(tasks_claimed_today) == 3 and not any("COMPLETION" in x for x in tasks_done if today_str in x)):
    if reveal_placeholder.button("🎁 OPEN SESSION CHEST", type="primary", use_container_width=True):
        for stage in ["🔍 ANALYZING BARS...", "🎛️ LEVELING...", "📀 EXPORTING..."]:
            reveal_placeholder.markdown(f"<div style='text-align:center; padding:50px; background:#000; border:2px solid gold;'><h2>{stage}</h2></div>", unsafe_allow_html=True)
            time.sleep(0.8)
        st.snow()
        if not st.session_state["test_trigger"]:
            tasks_done.append(f"{today_str}_COMPLETION_RC250")
            save_all()
        st.session_state["test_trigger"] = False
        time.sleep(2); st.rerun()

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Session Words</h3><h2>{today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Total Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)

t_rec, t_vau, t_shop, t_car = st.tabs(["🎙️ Booth", "📂 Vault", "🏪 Rack Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area("Drop your lyrics here...", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 SAVE TO HISTORY", type="primary"):
        entry_map[today_str] = lyrics; save_all(); st.rerun()

with t_vau:
    for d, lyr in sorted(entry_map.items(), reverse=True):
        with st.expander(f"📅 {d}"): st.text(lyr)

with t_shop:
    st.subheader("Upgrade your Sidebar (Studio Rack)")
    sc = st.columns(2)
    for i, (item, price) in enumerate(sidebar_customs.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"Installed: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"s_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()
    
    st.divider()
    st.subheader("Recording Gear")
    gc = st.columns(2)
    for i, (item, price) in enumerate(gear_items.items()):
        with gc[i%2]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"g_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()

with t_car:
    st.header("Achievements")
    achs = [
        {"id": "day1", "name": "The Intern", "goal": "Record your 1st session", "target": 1, "curr": active_sessions},
        {"id": "words_500", "name": "Wordsmith", "goal": "Reach 500 total words", "target": 500, "curr": total_words}
    ]
    for a in achs:
        prog = min(a['curr'] / a['target'], 1.0)
        st.subheader(a['name'])
        st.caption(f"Goal: {a['goal']}")
        st.progress(prog)
        if a['id'] in claimed: st.success("Claimed")
        elif prog >= 1.0 and st.button(f"Claim Achievement", key=f"ach_{a['id']}"):
            claimed.append(a['id']); save_all(); st.rerun()
