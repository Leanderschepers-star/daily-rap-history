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
START_DATE = datetime(2025, 12, 19).date()

# Initialize Session States for Debugging
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

# --- 3. MATH & STREAK ---
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
shop_prices = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 400, "Neon 'VIBE' Sign 🏮": 800, "Bass Subwoofer 🔊": 1500, "Smoke Machine 💨": 2500, "Golden Mic 🎤": 5000}
user_points -= sum([shop_prices.get(p, 0) for p in purchases])

# --- 4. DYNAMIC QUESTS ---
random.seed(today_str)
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": "Hit the 100-word mark", "req": today_word_count >= 100, "rc": 100},
    {"id": "q_streak", "desc": "Keep the streak alive (2+)", "req": current_streak >= 2, "rc": 50},
    {"id": "q_shop", "desc": "Browse Studio Shop", "req": "shop_seen" in st.session_state, "rc": 20}
]
daily_tasks = random.sample(quest_pool, 3)

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

# --- 5. UI & STYLING ---
foam_active = "Acoustic Foam 🎚️" in enabled_gear
led_active = "LED Strips 🌈" in enabled_gear

foam_css = "border: 6px double #444; padding: 15px; background: #0a0a0a !important; border-radius: 12px;" if foam_active else ""
led_css = "box-shadow: 0 0 25px rgba(0, 255, 136, 0.6);" if led_active else ""

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    .stApp {{ background-color: #0f0f0f; color: white; }}
    .stats-card {{ background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); text-align: center; {led_css} }}
    .quest-item {{ padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #444; background: rgba(255,255,255,0.02); }}
    .done {{ border-left-color: #00ff88; color: #00ff88; }}
    div[data-baseweb="textarea"] {{ {foam_css} }}
    .reveal-box {{ text-align: center; padding: 40px; background: #000; border: 3px solid #ffaa00; border-radius: 20px; margin: 20px auto; max-width: 600px; }}
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    
    st.divider()
    st.subheader("🎨 Customization")
    unlocked_themes = ["Default Dark"]
    if "day1" in claimed: unlocked_themes.append("Underground UI 🧱")
    if "words_500" in claimed: unlocked_themes.append("Classic Studio 🎙️")
    
    selected_theme = st.selectbox("Theme", unlocked_themes, index=unlocked_themes.index(active_theme) if active_theme in unlocked_themes else 0)
    if selected_theme != active_theme:
        save_all(theme_to_save=selected_theme); st.rerun()

    st.write("**Gear Effects**")
    gear_available = ["Acoustic Foam 🎚️", "LED Strips 🌈", "Gold XLR Cable 🔌", "Pop Filter 🎙️", "Studio Monitor Stands 🔊"]
    new_gear_states = []
    for g in gear_available:
        if g in purchases or g.replace("🎚️", "🔇") in purchases:
            if st.checkbox(g, value=(g in enabled_gear)):
                new_gear_states.append(g)
    
    if set(new_gear_states) != set(enabled_gear):
        save_all(gear_to_save=new_gear_states); st.rerun()

    st.divider()
    st.subheader("📋 Quests")
    tasks_claimed_today = [t for t in daily_tasks if any(t['id'] in x for x in tasks_done if today_str in x)]
    st.progress(len(tasks_claimed_today) / 3)
    
    for t in daily_tasks:
        is_done = any(t['id'] in x for x in tasks_done if today_str in x)
        if is_done: st.markdown(f"<div class='quest-item done'>✅ {t['desc']}</div>", unsafe_allow_html=True)
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"q_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}"); save_all(); st.rerun()

    st.divider()
    if st.button("🛠️ Test Chest Animation", use_container_width=True):
        st.session_state["test_trigger"] = True
        st.rerun()

# --- 7. MAIN UI ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO</h1>", unsafe_allow_html=True)

# THE CENTER REVEAL LOGIC
reveal_placeholder = st.empty()
if st.session_state["test_trigger"] or (len(tasks_claimed_today) == 3 and not any("COMPLETION" in x for x in tasks_done if today_str in x)):
    is_test = st.session_state["test_trigger"]
    
    if reveal_placeholder.button("🎁 OPEN TEST CHEST" if is_test else "🎁 OPEN DAILY CHEST", type="primary", use_container_width=True):
        for stage in ["🎵 PREPARING SAMPLES...", "🎧 EQUALIZING LOOT...", "🎤 EXPORTING REWARD..."]:
            reveal_placeholder.markdown(f"<div class='reveal-box'><h2>{stage}</h2></div>", unsafe_allow_html=True)
            time.sleep(0.8)
        
        st.snow()
        if is_test:
            reveal_placeholder.markdown("<div class='reveal-box'><h1>✨ TEST COMPLETE</h1><p>No rewards were given (Safe Mode).</p></div>", unsafe_allow_html=True)
            st.session_state["test_trigger"] = False
        else:
            tasks_done.append(f"{today_str}_COMPLETION_RC200")
            new_gear = next((g for g in gear_available if g not in purchases), None)
            if new_gear: purchases.append(new_gear)
            save_all()
            reveal_placeholder.markdown(f"<div class='reveal-box'><h1>🎊 PAYDAY!</h1><h3>+200 RC {'+ ' + new_gear if new_gear else ""}</h3></div>", unsafe_allow_html=True)
            
        time.sleep(3); st.rerun()

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Words</h3><h2>{today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Rank</h3><h2>Lv.{len(claimed)+1}</h2></div>', unsafe_allow_html=True)

t_rec, t_vau, t_shop, t_car = st.tabs(["✍️ Record Today", "📂 Vault", "🏪 Studio Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area(f"Booth: {today_str}", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 Save Session"):
        entry_map[today_str] = lyrics; save_all(); st.toast("Saved!"); st.rerun()

with t_vau:
    for d, lyr in sorted(entry_map.items(), reverse=True):
        with st.expander(f"📅 {d}"): st.text(lyr)

with t_shop:
    st.session_state["shop_seen"] = True
    sc1, sc2 = st.columns(2)
    for i, (item, price) in enumerate(shop_prices.items()):
        with (sc1 if i%2==0 else sc2):
            if item in purchases: st.success(f"OWNED: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"buy_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()
                else: st.error("Low RC!")

with t_car:
    st.header("Achievements")
    achievements = [
        {"id": "day1", "name": "First Day", "goal": "Write your first entry", "target": 1, "curr": active_sessions},
        {"id": "words_500", "name": "Wordsmith", "goal": "Reach 500 total words", "target": 500, "curr": total_words}
    ]
    for a in achievements:
        prog = min(a['curr'] / a['target'], 1.0)
        st.subheader(a['name'])
        st.progress(prog)
        if a['id'] in claimed: st.success("Unlocked")
        elif prog >= 1.0 and st.button(f"Unlock Reward", key=f"claim_{a['id']}"):
            claimed.append(a['id']); save_all(); st.rerun()
        else: st.write(f"Goal: {a['goal']} ({a['curr']}/{a['target']})")
