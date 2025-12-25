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
if "show_reward" not in st.session_state:
    st.session_state["show_reward"] = False

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

# --- 3. DEFINITIONS & RARITY ENGINE ---
RARITIES = {
    "COMMON": {"color": "#9da5b4", "chance": 0.60, "rc_range": (50, 150)},
    "UNCOMMON": {"color": "#1eff00", "chance": 0.25, "rc_range": (200, 400)},
    "RARE": {"color": "#0070dd", "chance": 0.10, "rc_range": (500, 1000)},
    "EPIC": {"color": "#a335ee", "chance": 0.04, "rc_range": (1500, 3000)},
    "LEGENDARY": {"color": "#ff8000", "chance": 0.01, "rc_range": (5000, 10000)}
}

# Procedural Reward Tables (Add as many strings here as you like)
COSMETIC_PREFIXES = ["Cyber", "Vintage", "Ghost", "Neon", "Diamond", "Rusty", "Liquid", "Royal", "Midnight", "Electric"]
COSMETIC_NOUNS = ["Mic", "Cable", "Foam", "Monitor", "Chair", "Desk", "Headphones", "Pre-amp", "Vinyl", "Poster"]

def roll_loot_box():
    roll = random.random()
    cumulative = 0
    for rarity, data in RARITIES.items():
        cumulative += data['chance']
        if roll <= cumulative:
            # 30% chance for a permanent cosmetic item, 70% for Coins
            if random.random() < 0.30:
                item_name = f"{random.choice(COSMETIC_PREFIXES)} {random.choice(COSMETIC_NOUNS)} ({rarity})"
                return {"type": "COSMETIC", "name": item_name, "rarity": rarity}
            else:
                amt = random.randint(*data['rc_range'])
                return {"type": "RC", "name": f"{amt} Rhyme Coins", "val": amt, "rarity": rarity}
    return {"type": "RC", "name": "50 Rhyme Coins", "val": 50, "rarity": "COMMON"}

# Generate 100 Achievement Slots automatically
ACHIEVEMENT_GOALS = []
for i in range(1, 101):
    ACHIEVEMENT_GOALS.append({
        "id": f"milestone_{i}",
        "name": f"Level {i}: {'Rookie' if i<10 else 'Pro' if i<50 else 'Legend'}",
        "target": i * 5, # Every 5 sessions
        "reward": "Exclusive Cosmetic Drop"
    })
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

# SPECIAL UNLOCK: NEON GLOW PULSE
neon_pulse = ""
if "Neon Rack Glow 🟣" in enabled_gear:
    neon_pulse = "@keyframes neon { 0% { box-shadow: 0 0 5px #bc13fe; } 50% { box-shadow: 0 0 20px #bc13fe; } 100% { box-shadow: 0 0 5px #bc13fe; } } section[data-testid='stSidebar'] { animation: neon 2s infinite ease-in-out; }"

# ANIMATED LED STRIPS LOGIC
led_anim_css = ""
if "LED Strips 🌈" in enabled_gear:
    led_anim_css = """
    @keyframes rotate { 100% { transform: rotate(1turn); } }
    div[data-baseweb="textarea"] {
        position: relative; z-index: 0; border-radius: 10px; overflow: hidden; padding: 4px; background: none !important; border: none !important;
    }
    div[data-baseweb="textarea"]::before {
        content: ''; position: absolute; z-index: -2; left: -50%; top: -50%; width: 200%; height: 200%;
        background-image: conic-gradient(#ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8b00ff, #ff0000);
        animation: rotate 4s linear infinite;
    }
    div[data-baseweb="textarea"]::after {
        content: ''; position: absolute; z-index: -1; left: 4px; top: 4px; width: calc(100% - 8px); height: calc(100% - 8px);
        background: #0f0f0f; border-radius: 7px;
    }
    """

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    {led_anim_css}
    {neon_pulse}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} }}
    section[data-testid="stSidebar"] {{ {rack_style} }}
    .stats-card {{ background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 12px; border: 1px solid #444; text-align: center; }}
    div[data-baseweb="textarea"] textarea {{ {foam_style} border: none !important; }}
    button[kind="primary"] {{ {gold_style} }}
    .vu-meter {{ height: 12px; background: linear-gradient(90deg, #2ecc71 70%, #f1c40f 85%, #e74c3c 100%); border-radius: 6px; margin-bottom: 20px; }}
    
    @keyframes rewardFade {{ from {{ opacity: 0; transform: scale(0.5); }} to {{ opacity: 1; transform: scale(1); }} }}
    @keyframes shine {{ 0% {{ background-position: -200%; }} 100% {{ background-position: 200%; }} }}
    
    .reward-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.9); z-index: 9999;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        animation: rewardFade 0.6s ease-out;
    }}
    .reward-card {{
        background: linear-gradient(135deg, #bf953f, #fcf6ba, #b38728);
        padding: 40px; border-radius: 20px; text-align: center;
        box-shadow: 0 0 50px rgba(212, 175, 55, 0.6);
        color: #000; font-weight: bold; width: 300px;
        background-size: 200% auto; animation: shine 3s linear infinite;
    }}
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
    # CAREER THEME UNLOCKS
    unlocked_t = ["Default Dark"]
    if "day1" in claimed: unlocked_t.append("Classic Studio 🎙️")
    if "words_500" in claimed: unlocked_t.append("Golden Era 🪙")
    if "streak_14" in claimed: unlocked_t.append("Midnight Diamond 💎")
    
    sel_theme = st.selectbox("Ambience", unlocked_t, index=unlocked_t.index(active_theme) if active_theme in unlocked_t else 0)
    if sel_theme != active_theme: save_all(theme_to_save=sel_theme); st.rerun()
    
    st.write("**Toggle Gear**")
    new_gear_list = []
    # Combined list of Shop Gear + Career Exclusive Gear
    available_gear = list(gear_items.keys()) + ["Neon Rack Glow 🟣"]
    for g in available_gear:
        # Check if bought OR if career milestone reached
        is_unlocked = (g in purchases) or (g == "Neon Rack Glow 🟣" and "streak_3" in claimed) or (g == "Mastering Console 🎛️" and "words_2000" in claimed)
        if is_unlocked:
            if st.checkbox(g, value=(g in enabled_gear), key=f"chk_{g}"):
                new_gear_list.append(g)
                
    if sorted(new_gear_list) != sorted(enabled_gear):
        save_all(gear_to_save=new_gear_list); st.rerun()

    st.divider()
    if st.button("🎁 TEST CHEST ANIMATION", use_container_width=True):
        st.session_state["test_trigger"] = True
        st.rerun()

# --- 6. CHEST SYSTEM ---
if st.session_state["show_reward"]:
    reward = st.session_state["show_reward"]
    r_color = RARITIES.get(reward.get('rarity', 'COMMON'))['color']
    
    st.markdown(f"""
        <div class="reward-overlay">
            <div class="reward-card" style="border: 5px solid {r_color}; box-shadow: 0 0 40px {r_color};">
                <h3 style="color: {r_color};">{reward['rarity']} DROP</h3>
                <h1 style="color: black;">{reward['name']}</h1>
                <p style="color: #333;">Added to your collection</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(4)
    st.session_state["show_reward"] = None
    st.rerun()

can_open = (len(claimed_today) == 3 and not any("CHEST" in x for x in tasks_done if today_str in x))
if st.button("🎁 OPEN DAILY LOOT BOX", use_container_width=True, disabled=not can_open):
    st.balloons()
    result = roll_loot_box()
    if result['type'] == "COSMETIC":
        purchases.append(result['name'])
    else:
        tasks_done.append(f"{today_str}_CHEST_RC{result['val']}")
    
    st.session_state["show_reward"] = result
    save_all()
    st.rerun()
# --- 7. MAIN UI ---
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
    data_dates = [datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()]
    if today_date not in data_dates: data_dates.append(today_date)
    curr_d, min_d = max(data_dates), min(data_dates)
    while curr_d >= min_d:
        d_s = curr_d.strftime('%d/%m/%Y')
        content = entry_map.get(d_s, "").strip()
        dot = "⚪" if not content else "🟢"
        with st.expander(f"{dot} {d_s} {'(Today)' if d_s == today_str else ''}"):
            new_txt = st.text_area(f"Edit {d_s}", value=content, height=150, key=f"j_{d_s}")
            if st.button(f"Update {d_s}", key=f"b_{d_s}"):
                entry_map[d_s] = new_txt; save_all(); st.rerun()
        curr_d -= timedelta(days=1)

with t_shop:
    sc = st.columns(2)
    for i, (item, price) in enumerate(all_shop.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"s_{i}"):
                if user_points >= price: purchases.append(item); save_all(); st.rerun()

with t_car:
    st.subheader("🏆 YOUR LIFELONG CAREER")
    for a in ACHIEVEMENT_GOALS:
        # Check if milestone is reached (e.g., based on active_sessions)
        is_reached = active_sessions >= a['target']
        is_claimed = a['id'] in claimed
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{a['name']}**")
            st.caption(f"Goal: {a['target']} Sessions | Reward: {a['reward']}")
            st.progress(min(active_sessions / a['target'], 1.0))
        with col2:
            if is_claimed:
                st.success("Claimed")
            elif is_reached:
                if st.button("Claim", key=a['id']):
                    # Achievement rewards are always high rarity
                    drop = roll_loot_box()
                    if drop['type'] == "COSMETIC": purchases.append(drop['name'])
                    else: tasks_done.append(f"{today_str}_ACH_RC{drop['val']}")
                    claimed.append(a['id'])
                    st.session_state["show_reward"] = drop
                    save_all(); st.rerun()
            else:
                st.info(f"{active_sessions}/{a['target']}")
    for a in achs:
        st.subheader(f"{a['name']} ({a['goal']})")
        st.write(f"🎁 Reward: **{a['reward']}**")
        st.progress(min(a['curr'] / a['target'], 1.0))
        if a['id'] not in claimed and a['curr'] >= a['target']:
            if st.button(f"Claim Achievement", key=f"ach_{a['id']}"):
                claimed.append(a['id']); save_all(); st.rerun()
        elif a['id'] in claimed:
            st.success("Claimed & Unlocked!")
