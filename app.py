import streamlit as st
import datetime, requests, base64, pytz, re, random, time
from datetime import datetime, timedelta

# --- 1. CONFIG & SETUP ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("GitHub Token missing. Please add it to Streamlit Secrets.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_date = be_now.date()
today_str = today_date.strftime('%d/%m/%Y')

if "show_reward" not in st.session_state:
    st.session_state["show_reward"] = False

# --- 2. GITHUB FUNCTIONS ---
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

# --- 3. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# State Extractions
purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))
tasks_done = list(set(re.findall(r'TASK_DONE: (.*)', full_text)))
active_theme = re.search(r'ACTIVE_THEME: (.*)', full_text).group(1) if "ACTIVE_THEME:" in full_text else "Default Dark"
enabled_gear = list(set(re.findall(r'ENABLED_GEAR: (.*)', full_text)))

# Lyrics Map Parsing
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

# --- 4. ENGINE: THE HUGE REWARD & RARITY SYSTEM ---
RARITIES = {
    "COMMON": {"color": "#9da5b4", "chance": 0.55, "rc_range": (50, 150), "icon": "📦"},
    "UNCOMMON": {"color": "#1eff00", "chance": 0.25, "rc_range": (200, 400), "icon": "🟢"},
    "RARE": {"color": "#0070dd", "chance": 0.12, "rc_range": (500, 1200), "icon": "🔵"},
    "EPIC": {"color": "#a335ee", "chance": 0.06, "rc_range": (2000, 5000), "icon": "🟣"},
    "LEGENDARY": {"color": "#ff8000", "chance": 0.02, "rc_range": (10000, 25000), "icon": "🟠"}
}

# 1,500+ Combinations possible here
PREFIXES = ["Cyber", "Vintage", "Ghost", "Neon", "Diamond", "Rusty", "Liquid", "Royal", "Midnight", "Electric", "Obsidian", "Chrome", "Golden", "Toxic", "Frozen", "Holographic", "Synthwave", "Industrial", "Angelic", "Demonic", "Infused", "Carbon", "Polished", "Infinite", "Prismatic", "Ancient", "Vanta-Black", "Marble"]
NOUNS = ["Mic", "Cable", "Foam", "Monitor", "Chair", "Desk", "Headphones", "Pre-amp", "Vinyl", "Poster", "Speaker", "Pop-filter", "Sampler", "Synth", "Drum Pad", "Mixer", "Subwoofer", "Tube Amp", "Acoustic Shield", "Tape Machine", "Patch Bay", "Reference Monitor"]

def roll_loot_box():
    roll = random.random()
    cumulative = 0
    for rarity, data in RARITIES.items():
        cumulative += data['chance']
        if roll <= cumulative:
            if random.random() < 0.45: # High chance for unique items
                item_name = f"{random.choice(PREFIXES)} {random.choice(NOUNS)} ({rarity}) 🎨"
                return {"type": "COSMETIC", "name": item_name, "rarity": rarity, "icon": data['icon']}
            else:
                amt = random.randint(*data['rc_range'])
                return {"type": "RC", "name": f"{amt} Rhyme Coins", "val": amt, "rarity": rarity, "icon": "🪙"}
    return {"type": "RC", "name": "75 RC", "val": 75, "rarity": "COMMON", "icon": "🪙"}

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

# --- 5. CALCULATIONS & SHOP ---
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())
active_sessions = len([k for k, v in entry_map.items() if v.strip()])

gear_items = {
    "Acoustic Foam 🎚️": 150, "LED Strips 🌈": 400, "Gold XLR Cable 🔌": 800,
    "Vintage Tube Mic 🎙️": 2500, "Mastering Console 🎛️": 6000, "Holographic Display ⚡": 15000,
    "Platinum Record 💿": 20000, "Grammy Shelf 🏆": 50000
}
sidebar_customs = {
    "Brushed Steel Rack 🏗️": 500, "Wooden Side-Panels 🪵": 800, 
    "Analog VU Meters 📈": 1200, "Neon Rack Glow 🟣": 2000, 
    "Solid Gold Frame 🪙": 5000, "Diamond Studded Trim 💎": 10000,
    "Obsidian VU Meters 🌑": 15000
}
all_shop = {**sidebar_customs, **gear_items}

bonus_rc = sum([int(re.search(r'RC(\d+)', x).group(1)) for x in tasks_done if "RC" in x])
spent_rc = sum([all_shop.get(p, 0) for p in purchases if p in all_shop])
user_points = (total_words // 2) + (active_sessions * 10) + bonus_rc - spent_rc

# Streak
current_streak = 0
check_date = today_date
if today_str not in entry_map: check_date = today_date - timedelta(days=1)
while True:
    d_key = check_date.strftime('%d/%m/%Y')
    if d_key in entry_map and entry_map[d_key].strip():
        current_streak += 1
        check_date -= timedelta(days=1)
    else: break

# 500 Achievement Levels
ACHIEVEMENT_GOALS = []
for i in range(1, 501):
    tier = 'Ghostwriter' if i<10 else 'Underground Icon' if i<30 else 'Major Label' if i<100 else 'Hall of Famer'
    ACHIEVEMENT_GOALS.append({
        "id": f"mil_{i}",
        "name": f"Lvl {i}: {tier}",
        "target": i * 5,
        "reward": "Epic Chest" if i % 10 == 0 else "Mystery Chest"
    })

# Daily Tasks
random.seed(today_str)
tasks_pool = [
    {"id": "q_rec", "desc": "Record session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": "Write 150+ words", "req": today_word_count >= 150, "rc": 120},
    {"id": "q_streak", "desc": "Maintain streak", "req": current_streak >= 1, "rc": 80}
]

# --- 6. FULL VISUAL CSS (THE 120 LINES OF POLISH) ---
themes_css = {
    "Default Dark": "background: #0f0f0f;",
    "Classic Studio 🎙️": "background-color: #1a1e23; background-image: linear-gradient(0deg, #23282e 1px, transparent 1px), linear-gradient(90deg, #23282e 1px, transparent 1px); background-size: 40px 40px; color: #d1d8e0;",
    "Golden Era 🪙": "background: linear-gradient(135deg, #1a1a1a 0%, #3d2b00 100%); color: #ffd700;",
    "Midnight Reflection 🌧️": "background: radial-gradient(circle, #0a0e14 0%, #000000 100%); color: #b9f2ff;"
}

# Sidebar Rack Physics
rack_style = "background: #111; border-right: 1px solid #333;"
if "Brushed Steel Rack 🏗️" in purchases: rack_style = "background: linear-gradient(180deg, #2c3e50, #000); border-right: 2px solid #95a5a6;"
if "Wooden Side-Panels 🪵" in purchases: rack_style += "border-right: 10px solid #5d4037;"
if "Solid Gold Frame 🪙" in purchases: rack_style = "background: linear-gradient(180deg, #bf953f, #fcf6ba, #b38728); border-right: 4px solid #aa771c; color: black !important;"
if "Diamond Studded Trim 💎" in purchases: rack_style += "box-shadow: 10px 0px 30px rgba(185, 242, 255, 0.4);"

foam_style = "background: repeating-conic-gradient(#000 0% 25%, #111 0% 50%) 50% / 20px 20px !important; color: #fff !important;" if "Acoustic Foam 🎚️" in enabled_gear else ""
gold_style = "background: #d4af37 !important; color: black !important;" if "Gold XLR Cable 🔌" in enabled_gear else ""

neon_pulse = ""
if "Neon Rack Glow 🟣" in enabled_gear:
    neon_pulse = "@keyframes neon { 0% { box-shadow: 0 0 5px #bc13fe; } 50% { box-shadow: 0 0 20px #bc13fe; } 100% { box-shadow: 0 0 5px #bc13fe; } } section[data-testid='stSidebar'] { animation: neon 2s infinite ease-in-out; }"

led_anim_css = ""
if "LED Strips 🌈" in enabled_gear:
    led_anim_css = """
    @keyframes rotate { 100% { transform: rotate(1turn); } }
    div[data-baseweb="textarea"] { position: relative; z-index: 0; border-radius: 10px; overflow: hidden; padding: 4px; background: none !important; border: none !important; }
    div[data-baseweb="textarea"]::before { content: ''; position: absolute; z-index: -2; left: -50%; top: -50%; width: 200%; height: 200%; background-image: conic-gradient(#ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8b00ff, #ff0000); animation: rotate 4s linear infinite; }
    div[data-baseweb="textarea"]::after { content: ''; position: absolute; z-index: -1; left: 4px; top: 4px; width: calc(100% - 8px); height: calc(100% - 8px); background: #0f0f0f; border-radius: 7px; }
    """

st.set_page_config(page_title="Leander Studio", layout="wide")
st.markdown(f"""
<style>
    {led_anim_css} {neon_pulse}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} }}
    section[data-testid="stSidebar"] {{ {rack_style} }}
    .stats-card {{ background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 12px; border: 1px solid #444; text-align: center; }}
    div[data-baseweb="textarea"] textarea {{ {foam_style} border: none !important; }}
    button[kind="primary"] {{ {gold_style} }}
    
    /* Gacha Overlay */
    @keyframes reveal-card {{ 0% {{ transform: scale(0) rotate(-10deg); opacity: 0; }} 100% {{ transform: scale(1) rotate(0deg); opacity: 1; }} }}
    .gacha-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 9999; display: flex; align-items: center; justify-content: center; }}
    .reward-card {{ background: #1a1a1a; padding: 60px; border-radius: 30px; text-align: center; border: 5px solid gold; animation: reveal-card 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
</style>
""", unsafe_allow_html=True)

# --- 7. REWARD LOGIC ---
if st.session_state["show_reward"]:
    res = st.session_state["show_reward"]
    color = RARITIES.get(res.get('rarity', 'COMMON'), RARITIES['COMMON'])['color']
    st.markdown(f"""
    <div class="gacha-overlay">
        <div class="reward-card" style="border-color: {color}; box-shadow: 0 0 80px {color}66;">
            <h2 style="color: {color}; letter-spacing: 5px;">{res['rarity']} UNLOCKED</h2>
            <div style="font-size: 100px; margin: 30px;">{res['icon']}</div>
            <h1 style="color: white; font-size: 40px;">{res['name']}</h1>
            <p style="color: #666; margin-top: 20px;">Added to your collection</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(4.0)
    st.session_state["show_reward"] = False
    st.rerun()

# --- 8. SIDEBAR UI ---
with st.sidebar:
    st.title("🎚️ STUDIO RACK")
    if any(x in purchases for x in ["Analog VU Meters 📈", "Obsidian VU Meters 🌑"]):
        st.write("Input Levels")
        st.markdown('<div style="height: 12px; background: linear-gradient(90deg, #2ecc71 70%, #f1c40f 85%, #e74c3c 100%); border-radius: 6px; margin-bottom: 20px;"></div>', unsafe_allow_html=True)
    
    st.metric("Rhyme Coins", f"{user_points} RC")
    
    with st.expander("💎 Rarity Guide"):
        for r, d in RARITIES.items():
            st.markdown(f"<span style='color:{d['color']}'>{d['icon']} {r}</span>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 QUESTS")
    claimed_today = [t for t in tasks_pool if any(t['id'] in x for x in tasks_done if today_str in x)]
    for t in tasks_pool:
        if any(t['id'] in x for x in tasks_done if today_str in x):
            st.success(f"✅ {t['desc']}")
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"q_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}"); save_all(); st.rerun()
        else:
            st.info(f"⚪ {t['desc']}")

    st.divider()
    can_open = (len(claimed_today) >= 2 and not any("CHEST" in x for x in tasks_done if today_str in x))
    if st.button("🎁 OPEN DAILY BOX", use_container_width=True, disabled=not can_open, type="primary"):
        res = roll_loot_box()
        if res['type'] == "COSMETIC": purchases.append(res['name'])
        else: tasks_done.append(f"{today_str}_CHEST_RC{res['val']}")
        st.session_state["show_reward"] = res
        save_all(); st.rerun()

    st.divider()
    st.subheader("⚙️ SETTINGS")
    unlocked_t = ["Default Dark"]
    if any("mil_1" in c for c in claimed): unlocked_t.append("Classic Studio 🎙️")
    if any("mil_5" in c for c in claimed): unlocked_t.append("Golden Era 🪙")
    if any("mil_20" in c for c in claimed): unlocked_t.append("Midnight Reflection 🌧️")
    
    sel_theme = st.selectbox("Ambience", unlocked_t, index=unlocked_t.index(active_theme) if active_theme in unlocked_t else 0)
    if sel_theme != active_theme:
        save_all(theme_to_save=sel_theme); st.rerun()
    
    st.write("**Active Gear**")
    gear_pool = list(set(list(gear_items.keys()) + ["Neon Rack Glow 🟣"] + [p for p in purchases if "🎨" in p or "(" in p]))
    new_gear = []
    for g in sorted(gear_pool):
        if st.checkbox(g, value=(g in enabled_gear)):
            new_gear.append(g)
    if sorted(new_gear) != sorted(enabled_gear):
        save_all(gear_to_save=new_gear); st.rerun()

# --- 9. MAIN APP ---
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>🔥 {current_streak}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Today</h3><h2>📝 {today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Total Sessions</h3><h2>🎙️ {active_sessions}</h2></div>', unsafe_allow_html=True)

t_rec, t_jou, t_shop, t_car = st.tabs(["🎙️ Booth", "📖 Journal", "🏪 Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area("Write lyrics...", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 SAVE TO HISTORY", type="primary", use_container_width=True):
        entry_map[today_str] = lyrics; save_all(); st.rerun()

with t_jou:
    for d_key in sorted(entry_map.keys(), reverse=True):
        with st.expander(f"📅 {d_key}"):
            st.write(entry_map[d_key])

with t_shop:
    sc = st.columns(2)
    for i, (item, price) in enumerate(all_shop.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"shop_{i}"):
                if user_points >= price:
                    purchases.append(item); save_all(); st.rerun()
                else: st.error("Lacking Rhyme Coins!")

with t_car:
    st.subheader("🏆 YOUR LIFELONG CAREER")
    upcoming = [a for a in ACHIEVEMENT_GOALS if a['id'] not in claimed][:5]
    for a in upcoming:
        reached = active_sessions >= a['target']
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{a['name']}**")
            st.progress(min(active_sessions / a['target'], 1.0))
        with col2:
            if reached and st.button("Claim", key=f"btn_{a['id']}"):
                res = roll_loot_box()
                if res['type'] == "COSMETIC": purchases.append(res['name'])
                else: tasks_done.append(f"{today_str}_ACH_RC{res['val']}")
                claimed.append(a['id']); st.session_state["show_reward"] = res
                save_all(); st.rerun()
