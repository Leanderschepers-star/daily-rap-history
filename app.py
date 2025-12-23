import streamlit as st
import datetime, requests, base64, pytz, re, random, time
from datetime import datetime, timedelta

# --- 1. CONFIG & SETUP ---
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

# --- 3. EXPANDED SHOP & CAREER ---
sidebar_customs = {
    "Brushed Steel Rack 🏗️": 500, "Wooden Side-Panels 🪵": 800,
    "Analog VU Meters 📈": 1200, "Neon Rack Glow 🟣": 2000,
    "Solid Gold Frame 🪙": 5000, "Diamond Studded Trim 💎": 10000
}
gear_items = {
    "Acoustic Foam 🎚️": 150, "LED Strips 🌈": 400, "Gold XLR Cable 🔌": 800,
    "Vintage Tube Mic 🎙️": 2500, "Mastering Console 🎛️": 6000, "Holographic Display ⚡": 15000
}
all_shop = {**sidebar_customs, **gear_items}

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())
active_sessions = len([k for k, v in entry_map.items() if v.strip()])
bonus_rc = sum([int(re.search(r'_RC(\d+)', x).group(1)) if "_RC" in x else 0 for x in tasks_done])
user_points = (total_words // 2) + (active_sessions * 10) + bonus_rc - sum([all_shop.get(p, 0) for p in purchases])

current_streak = 0
check_date = today_date
if today_str not in entry_map: check_date = today_date - timedelta(days=1)
while True:
    d_key = check_date.strftime('%d/%m/%Y')
    if d_key in entry_map and entry_map[d_key].strip():
        current_streak += 1
        check_date -= timedelta(days=1)
    else: break

random.seed(today_str)
dynamic_goal = random.choice([50, 100, 150, 250])
daily_tasks = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": f"Write {dynamic_goal} words", "req": today_word_count >= dynamic_goal, "rc": 100},
    {"id": "q_streak", "desc": "Maintain streak (1+)", "req": current_streak >= 1, "rc": 75}
]

def save_all(theme_to_save=None, gear_to_save=None):
    t = theme_to_save if theme_to_save else active_theme
    g_list = gear_to_save if gear_to_save is not None else enabled_gear
    content = f"ACTIVE_THEME: {t}\n"
    for g in g_list: content += f"ENABLED_GEAR: {g}\n"
    for p in sorted(purchases): content += f"PURCHASE: {p}\n"
    for c in sorted(claimed): content += f"CLAIMED: {c}\n"
    for t_done in sorted(tasks_done): content += f"TASK_DONE: {t_done}\n"
    clean_map = {k: v for k, v in entry_map.items() if v.strip()}
    for d in sorted(clean_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{clean_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. VISUAL ENGINE ---
themes_css = {
    "Default Dark": "background: #0f0f0f;",
    "Classic Studio 🎙️": "background-color: #1a1e23; background-image: linear-gradient(0deg, #23282e 1px, transparent 1px), linear-gradient(90deg, #23282e 1px, transparent 1px); background-size: 40px 40px; color: #d1d8e0;",
    "Golden Era 🪙": "background: linear-gradient(135deg, #1a1a1a 0%, #3d2b00 100%); color: #ffd700;",
    "Midnight Diamond 💎": "background: radial-gradient(circle, #0a0e14 0%, #000000 100%); color: #b9f2ff;"
}

rack_style = "background: #111; border-right: 1px solid #333;"
if "Brushed Steel Rack 🏗️" in purchases: rack_style = "background: linear-gradient(180deg, #2c3e50, #000); border-right: 2px solid #95a5a6;"
if "Wooden Side-Panels 🪵" in purchases: rack_style += "border-right: 10px solid #5d4037;"
if "Solid Gold Frame 🪙" in purchases: rack_style = "background: linear-gradient(180deg, #bf953f, #fcf6ba, #b38728); border-right: 4px solid #aa771c; color: black !important;"
if "Diamond Studded Trim 💎" in purchases: rack_style += "box-shadow: 10px 0px 30px rgba(185, 242, 255, 0.4);"

foam_style = "background: repeating-conic-gradient(#000 0% 25%, #111 0% 50%) 50% / 20px 20px !important; color: #fff !important;" if "Acoustic Foam 🎚️" in enabled_gear else ""
gold_style = "background: #d4af37 !important; color: black !important;" if "Gold XLR Cable 🔌" in enabled_gear else ""

rainbow_anim = ""
if "LED Strips 🌈" in enabled_gear:
    rainbow_anim = """
    @keyframes rainbow { 0% { border-color: #ff0000; } 33% { border-color: #00ff00; } 66% { border-color: #0000ff; } 100% { border-color: #ff0000; } }
    div[data-baseweb="textarea"] { border: 4px solid red !important; animation: rainbow 3s linear infinite !important; border-radius: 8px; }
    """

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    {rainbow_anim}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} }}
    section[data-testid="stSidebar"] {{ {rack_style} }}
    .stats-card {{ background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 12px; border: 1px solid #444; text-align: center; }}
    div[data-baseweb="textarea"] textarea {{ {foam_style} }}
    button[kind="primary"] {{ {gold_style} }}
    .vu-meter {{ height: 12px; background: linear-gradient(90deg, #2ecc71 70%, #f1c40f 85%, #e74c3c 100%); border-radius: 6px; margin-bottom: 20px; }}
    
    /* Missed Day Styling */
    .status-tag {{ padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; margin-left: 10px; }}
    .status-missed {{ background: #ff4b4b; color: white; }}
    .status-recorded {{ background: #2ecc71; color: white; }}
</style>
""", unsafe_allow_html=True)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🎚️ STUDIO RACK")
    if "Analog VU Meters 📈" in purchases:
        st.write("Input Levels"); st.markdown('<div class="vu-meter"></div>', unsafe_allow_html=True)
    st.metric("Budget", f"{user_points} RC")
    
    st.divider(); st.subheader("📋 QUEST LOG")
    claimed_today = [t for t in daily_tasks if any(t['id'] in x for x in tasks_done if today_str in x)]
    st.progress(len(claimed_today) / 3)
    for t in daily_tasks:
        if any(t['id'] in x for x in tasks_done if today_str in x): st.success(f"✅ {t['desc']}")
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"q_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}"); save_all(); st.rerun()
        else: st.info(f"⚪ {t['desc']}")

    st.divider(); st.subheader("⚙️ SETTINGS")
    unlocked_t = ["Default Dark"]
    if "streak_3" in claimed: unlocked_t.append("Classic Studio 🎙️")
    if "words_500" in claimed: unlocked_t.append("Golden Era 🪙")
    if "streak_14" in claimed: unlocked_t.append("Midnight Diamond 💎")
    sel_theme = st.selectbox("Ambience", unlocked_t, index=unlocked_t.index(active_theme) if active_theme in unlocked_t else 0)
    if sel_theme != active_theme: save_all(theme_to_save=sel_theme); st.rerun()
    
    st.write("**Toggle Gear**")
    new_gear_list = []
    for g in gear_items.keys():
        if g in purchases:
            if st.checkbox(g, value=(g in enabled_gear), key=f"chk_{g}"):
                new_gear_list.append(g)
    if sorted(new_gear_list) != sorted(enabled_gear):
        save_all(gear_to_save=new_gear_list); st.rerun()

# --- 6. MAIN UI ---
st.markdown("<h1 style='text-align:center;'>STUDIO CONSOLE</h1>", unsafe_allow_html=True)

if st.session_state["test_trigger"] or (len(claimed_today) == 3 and not any("COMPLETION" in x for x in tasks_done if today_str in x)):
    if st.button("🎁 OPEN SESSION CHEST", type="primary", use_container_width=True):
        st.snow()
        if not st.session_state["test_trigger"]: tasks_done.append(f"{today_str}_COMPLETION_RC250"); save_all()
        st.session_state["test_trigger"] = False; time.sleep(1); st.rerun()

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>🔥 {current_streak}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Session Words</h3><h2>📝 {today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Total Words</h3><h2>🌎 {total_words}</h2></div>', unsafe_allow_html=True)

t_rec, t_jou, t_shop, t_car = st.tabs(["🎙️ Booth", "📖 Journal", "🏪 Rack Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area("Drop your lyrics here...", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 SAVE TO HISTORY", type="primary", use_container_width=True):
        entry_map[today_str] = lyrics; save_all(); st.rerun()

with t_jou:
    # Get all dates that have entries
    data_dates = [datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()]
    if today_date not in data_dates: data_dates.append(today_date)
    
    # Range from the very first entry to today
    curr_d, min_d = max(data_dates), min(data_dates)
    
    while curr_d >= min_d:
        d_s = curr_d.strftime('%d/%m/%Y')
        content = entry_map.get(d_s, "").strip()
        
        # Check if day was missed
        is_empty = not content
        dot_char = "⚪" if is_empty else "🟢"
        status_label = '<span class="status-tag status-missed">MISSED</span>' if is_empty else '<span class="status-tag status-recorded">RECORDED</span>'
        
        # Special styling for today
        display_name = f"{dot_char} {d_s}"
        if d_s == today_str: display_name += " (Today)"
        
        with st.expander(display_name, expanded=(d_s == today_str)):
            st.markdown(f"Status: {status_label}", unsafe_allow_html=True)
            new_txt = st.text_area(f"Lyrics for {d_s}", value=content, height=150, key=f"j_{d_s}")
            if st.button(f"Update {d_s}", key=f"b_{d_s}"):
                entry_map[d_s] = new_txt; save_all(); st.rerun()
        curr_d -= timedelta(days=1)

with t_shop:
    st.subheader("Studio Rack Upgrades")
    sc = st.columns(2)
    for i, (item, price) in enumerate(sidebar_customs.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"Installed: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"s_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()
    st.divider(); st.subheader("Recording Gear")
    gc = st.columns(2)
    for i, (item, price) in enumerate(gear_items.items()):
        with gc[i%2]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"g_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()

with t_car:
    st.header("Achievements")
    achs = [
        {"id": "day1", "name": "Intern", "goal": "1 Session", "target": 1, "curr": active_sessions},
        {"id": "streak_3", "name": "Rookie", "goal": "3 Day Streak", "target": 3, "curr": current_streak},
        {"id": "streak_7", "name": "Local", "goal": "7 Day Streak", "target": 7, "curr": current_streak},
        {"id": "streak_14", "name": "Pro", "goal": "14 Day Streak", "target": 14, "curr": current_streak},
        {"id": "words_100", "name": "Dabbler", "goal": "100 Words", "target": 100, "curr": total_words},
        {"id": "words_500", "name": "Writer", "goal": "500 Words", "target": 500, "curr": total_words},
        {"id": "words_1000", "name": "Lyricist", "goal": "1k Words", "target": 1000, "curr": total_words},
        {"id": "words_5000", "name": "Rap God", "goal": "5k Words", "target": 5000, "curr": total_words},
    ]
    for a in achs:
        prog = min(a['curr'] / a['target'], 1.0)
        st.subheader(f"{a['name']} ({a['goal']})")
        st.progress(prog)
        if a['id'] in claimed: st.caption("Claimed ✅")
        elif prog >= 1.0 and st.button(f"Claim Achievement", key=f"ach_{a['id']}"):
            claimed.append(a['id']); save_all(); st.rerun()
