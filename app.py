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

if "test_trigger" not in st.session_state:
    st.session_state["test_trigger"] = False
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

# --- 3. DATA PARSING (LOAD FILE) ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# Extract Lists
purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))
tasks_done = list(set(re.findall(r'TASK_DONE: (.*)', full_text)))
active_theme = re.search(r'ACTIVE_THEME: (.*)', full_text).group(1) if "ACTIVE_THEME:" in full_text else "Default Dark"
enabled_gear = list(set(re.findall(r'ENABLED_GEAR: (.*)', full_text)))

# Extract Lyrics Map
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

# --- 4. ENGINE: DEFINITIONS (MUST BE HERE) ---

# Rarity & Reward System
RARITIES = {
    "COMMON": {"color": "#9da5b4", "chance": 0.60, "rc_range": (50, 150)},
    "UNCOMMON": {"color": "#1eff00", "chance": 0.25, "rc_range": (200, 400)},
    "RARE": {"color": "#0070dd", "chance": 0.10, "rc_range": (500, 1000)},
    "EPIC": {"color": "#a335ee", "chance": 0.04, "rc_range": (1500, 3000)},
    "LEGENDARY": {"color": "#ff8000", "chance": 0.01, "rc_range": (5000, 10000)}
}

COSMETIC_PREFIXES = ["Cyber", "Vintage", "Ghost", "Neon", "Diamond", "Rusty", "Liquid", "Royal", "Midnight", "Electric", "Obsidian", "Chrome", "Golden", "Toxic", "Frozen", "Holographic"]
COSMETIC_NOUNS = ["Mic", "Cable", "Foam", "Monitor", "Chair", "Desk", "Headphones", "Pre-amp", "Vinyl", "Poster", "Speaker", "Pop-filter", "Sampler", "Synth"]

def roll_loot_box():
    """Generates a random reward based on rarity."""
    roll = random.random()
    cumulative = 0
    for rarity, data in RARITIES.items():
        cumulative += data['chance']
        if roll <= cumulative:
            # 35% chance for a permanent cosmetic item, 65% for Coins
            if random.random() < 0.35:
                item_name = f"{random.choice(COSMETIC_PREFIXES)} {random.choice(COSMETIC_NOUNS)} ({rarity})"
                return {"type": "COSMETIC", "name": item_name, "rarity": rarity}
            else:
                amt = random.randint(*data['rc_range'])
                return {"type": "RC", "name": f"{amt} Rhyme Coins", "val": amt, "rarity": rarity}
    return {"type": "RC", "name": "50 RC", "val": 50, "rarity": "COMMON"}

# Save Function (This fixes your error: It is defined BEFORE use)
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

# --- 5. CALCULATIONS (STATE) ---

# 1. Stats
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())
active_sessions = len([k for k, v in entry_map.items() if v.strip()])

# 2. Points & Shop
sidebar_customs = {
    "Brushed Steel Rack 🏗️": 500, "Wooden Side-Panels 🪵": 800,
    "Analog VU Meters 📈": 1200, "Neon Rack Glow 🟣": 2000,
    "Solid Gold Frame 🪙": 5000, "Diamond Studded Trim 💎": 10000,
    "Obsidian VU Meters 🌑": 15000
}
gear_items = {
    "Acoustic Foam 🎚️": 150, "LED Strips 🌈": 400, "Gold XLR Cable 🔌": 800,
    "Vintage Tube Mic 🎙️": 2500, "Mastering Console 🎛️": 6000, "Holographic Display ⚡": 15000,
    "Platinum Record 💿": 20000, "Grammy Shelf 🏆": 50000
}
all_shop = {**sidebar_customs, **gear_items}

bonus_rc = sum([int(re.search(r'RC(\d+)', x).group(1)) for x in tasks_done if "RC" in x])
spent_rc = sum([all_shop.get(p, 0) for p in purchases if p in all_shop])
user_points = (total_words // 2) + (active_sessions * 10) + bonus_rc - spent_rc

# 3. Streak Logic
current_streak = 0
check_date = today_date
if today_str not in entry_map: check_date = today_date - timedelta(days=1)
while True:
    d_key = check_date.strftime('%d/%m/%Y')
    if d_key in entry_map and entry_map[d_key].strip():
        current_streak += 1
        check_date -= timedelta(days=1)
    else: break

# 4. Daily Quests
random.seed(today_str)
dynamic_goal = random.choice([50, 100, 150, 250])
daily_tasks = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": f"Write {dynamic_goal} words", "req": today_word_count >= dynamic_goal, "rc": 100},
    {"id": "q_streak", "desc": "Maintain streak (1+)", "req": current_streak >= 1, "rc": 75}
]

# 5. Achievement Generation (500 Levels)
ACHIEVEMENT_GOALS = []
for i in range(1, 501):
    ACHIEVEMENT_GOALS.append({
        "id": f"mil_{i}",
        "name": f"Level {i}: {'Rookie' if i<10 else 'Pro' if i<50 else 'Legend'}",
        "target": i * 5, 
        "reward": "Mystery Loot Box"
    })

# --- 6. VISUAL CSS & STYLE ENGINE ---
themes_css = {
    "Default Dark": "background: #0f0f0f;",
    "Classic Studio 🎙️": "background-color: #1a1e23; background-image: linear-gradient(0deg, #23282e 1px, transparent 1px), linear-gradient(90deg, #23282e 1px, transparent 1px); background-size: 40px 40px; color: #d1d8e0;",
    "Golden Era 🪙": "background: linear-gradient(135deg, #1a1a1a 0%, #3d2b00 100%); color: #ffd700;",
    "Midnight Reflection 🌧️": "background: radial-gradient(circle, #0a0e14 0%, #000000 100%); color: #b9f2ff;"
}

# 1. Prefix Effects Logic (Keep this OUTSIDE the st.markdown string)
prefix_css = ""
if any("Toxic" in g for g in enabled_gear): 
    prefix_css += "color: #39ff14 !important; text-shadow: 0 0 10px #39ff14;"
if any("Frozen" in g for g in enabled_gear): 
    prefix_css += "background-color: rgba(0, 242, 255, 0.15) !important; border: 1px solid #00f2ff !important;"
if any("Electric" in g for g in enabled_gear): 
    prefix_css += "border-left: 5px solid #f1c40f !important; border-right: 5px solid #f1c40f !important;"
if any("Chrome" in g for g in enabled_gear): 
    prefix_css += "background-color: rgba(255, 255, 255, 0.1) !important; box-shadow: inset 0 0 20px white; color: black !important;"

# 2. Sidebar Rack Styles
rack_style = "background: #111; border-right: 1px solid #333;"
if "Brushed Steel Rack 🏗️" in purchases: rack_style = "background: linear-gradient(180deg, #2c3e50, #000); border-right: 2px solid #95a5a6;"
if "Wooden Side-Panels 🪵" in purchases: rack_style += "border-right: 10px solid #5d4037;"
if "Solid Gold Frame 🪙" in purchases: rack_style = "background: linear-gradient(180deg, #bf953f, #fcf6ba, #b38728); border-right: 4px solid #aa771c; color: black !important;"
if "Diamond Studded Trim 💎" in purchases: rack_style += "box-shadow: 10px 0px 30px rgba(185, 242, 255, 0.4);"

# 3. Acoustic Foam Style
foam_style = ""
if "Acoustic Foam 🎚️" in enabled_gear:
    foam_style = """
    background-color: #111 !important;
    background-image: 
        radial-gradient(circle at 2px 2px, #333 1px, transparent 0),
        radial-gradient(circle at 12px 12px, #000 1px, transparent 0),
        repeating-conic-gradient(#1a1a1a 0% 25%, #111 25% 50%) !important;
    background-size: 20px 20px !important;
    """

gold_style = "background: #d4af37 !important; color: black !important;" if "Gold XLR Cable 🔌" in enabled_gear else ""

neon_pulse = ""
if "Neon Rack Glow 🟣" in enabled_gear or any("Neon" in g for g in enabled_gear):
    neon_pulse = "@keyframes neon { 0% { box-shadow: 0 0 5px #bc13fe; } 50% { box-shadow: 0 0 20px #bc13fe; } 100% { box-shadow: 0 0 5px #bc13fe; } } section[data-testid='stSidebar'] { animation: neon 2s infinite ease-in-out; }"

led_anim_css = ""
if "LED Strips 🌈" in enabled_gear:
    led_anim_css = """
    @keyframes rotate { 100% { transform: rotate(1turn); } }
    div[data-baseweb="textarea"] { position: relative; z-index: 0; border-radius: 10px; overflow: hidden; padding: 4px; background: none !important; border: none !important; }
    div[data-baseweb="textarea"]::before { content: ''; position: absolute; z-index: -2; left: -50%; top: -50%; width: 200%; height: 200%; background-image: conic-gradient(#ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #8b00ff, #ff0000); animation: rotate 4s linear infinite; }
    div[data-baseweb="textarea"]::after { content: ''; position: absolute; z-index: -1; left: 4px; top: 4px; width: calc(100% - 8px); height: calc(100% - 8px); background: #0f0f0f; border-radius: 7px; }
    """

# --- 7. APPLY STYLES & PAGE CONFIG ---
st.set_page_config(page_title="Leander Studio", layout="wide")

st.markdown(f"""
<style>
    {led_anim_css}
    {neon_pulse}
    .stApp {{ {themes_css.get(active_theme, themes_css['Default Dark'])} }}
    section[data-testid="stSidebar"] {{ {rack_style} }}
    .stats-card {{ background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 12px; border: 1px solid #444; text-align: center; }}
    
    /* THE BOOTH INTERIOR (Text Area) */
    div[data-baseweb="textarea"] textarea {{ 
        {foam_style} 
        {prefix_css} 
        background-attachment: local !important;
        border: none !important; 
    }}

    /* Essential for LED Strips and Foam visibility */
    div[data-baseweb="textarea"] {{
        background: transparent !important;
        border: none !important;
    }}
    
    button[kind="primary"] {{ {gold_style} }}
    .vu-meter {{ height: 12px; background: linear-gradient(90deg, #2ecc71 70%, #f1c40f 85%, #e74c3c 100%); border-radius: 6px; margin-bottom: 20px; }}
    
    @keyframes rewardFade {{ from {{ opacity: 0; transform: scale(0.5); }} to {{ opacity: 1; transform: scale(1); }} }}
    @keyframes shake {{
      0% {{ transform: translate(1px, 1px) rotate(0deg); }}
      100% {{ transform: translate(1px, -2px) rotate(-1deg); }}
    }}

    .reward-card {{
        background: #000 !important;
        padding: 40px; border-radius: 20px; text-align: center;
        color: white !important; font-weight: bold; width: 350px;
        border: 4px solid white;
        animation: shake 0.2s infinite, rewardFade 0.6s ease-out;
    }}
    
    .reward-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.9); z-index: 9999;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        animation: rewardFade 0.6s ease-out;
    }}
</style>
""", unsafe_allow_html=True)

# --- 8. REWARD OVERLAY & CHEST ---
claimed_today = [t for t in daily_tasks if any(t['id'] in x for x in tasks_done if today_str in x)]

if st.session_state.get("show_reward"):
    reward = st.session_state["show_reward"]
    r_color = RARITIES.get(reward.get('rarity', 'COMMON'), RARITIES['COMMON'])['color']
    st.markdown(f"""
        <div class="reward-overlay">
            <div class="reward-card" style="border: 5px solid {r_color}; box-shadow: 0 0 40px {r_color};">
                <h3 style="color: {r_color};">{reward.get('rarity', 'COMMON')} DROP</h3>
                <h1 style="color: white !important;">{reward['name']}</h1>
                <p style="color: #aaa;">Added to your collection</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(4)
    st.session_state["show_reward"] = False
    st.rerun()

can_open = (len(claimed_today) == 3 and not any("CHEST" in x for x in tasks_done if today_str in x))
if st.button("🎁 OPEN DAILY LOOT BOX", use_container_width=True, disabled=not can_open, key="chest_btn"):
    st.balloons()
    result = roll_loot_box()
    if result['type'] == "COSMETIC": purchases.append(result['name'])
    else: tasks_done.append(f"{today_str}_CHEST_RC{result['val']}")
    st.session_state["show_reward"] = result
    save_all()
    st.rerun()

# --- 9. SIDEBAR (The Missing Bar) ---
with st.sidebar:
    st.title("🎚️ STUDIO RACK")
    st.metric("Budget", f"{user_points} RC")
    st.divider()
    st.subheader("📋 QUEST LOG")
    for t in daily_tasks:
        is_done = any(t['id'] in x for x in tasks_done if today_str in x)
        if is_done: st.success(f"✅ {t['desc']}")
        elif t['req']:
            if st.button(f"Claim {t['rc']} RC", key=f"side_{t['id']}"):
                tasks_done.append(f"{today_str}_{t['id']}_RC{t['rc']}")
                save_all()
                st.rerun()
        else: st.info(f"⚪ {t['desc']}")
    
    st.divider()
    st.subheader("⚙️ GEAR TOGGLE")
    # This allows you to turn on the Foam you bought
    current_gear = st.multiselect("Active Gear", options=purchases, default=enabled_gear)
    if set(current_gear) != set(enabled_gear):
        save_all(gear_to_save=current_gear)
        st.rerun()

# --- 10. MAIN APP TABS --- 
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>🔥 {current_streak}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Session Words</h3><h2>📝 {today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Total Words</h3><h2>🌎 {total_words}</h2></div>', unsafe_allow_html=True)

t_rec, t_jou, t_shop, t_car = st.tabs(["🎙️ Booth", "📖 Journal", "🏪 Rack Shop", "🏆 Career"])

with t_rec:
    lyrics = st.text_area("Drop your lyrics here...", value=entry_map.get(today_str, ""), height=400)
    if st.button("🚀 SAVE TO HISTORY", type="primary", use_container_width=True):
        entry_map[today_str] = lyrics
        save_all()
        st.rerun()

with t_jou:
    data_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)
    for d in data_dates:
        d_s = d.strftime('%d/%m/%Y')
        with st.expander(f"📅 {d_s}"):
            st.text_area("Edit", value=entry_map.get(d_s, ""), height=150, key=f"jou_{d_s}")

with t_shop:
    sc = st.columns(2)
    for i, (item, price) in enumerate(all_shop.items()):
        with sc[i%2]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)", key=f"buy_{i}"):
                if user_points >= price:
                    purchases.append(item)
                    save_all()
                    st.rerun()
                else: st.error("Not enough RC!")

with t_car:
    st.subheader("🏆 CAREER MILESTONES")
    upcoming = [a for a in ACHIEVEMENT_GOALS if a['id'] not in claimed][:5]
    for a in upcoming:
        is_reached = active_sessions >= a['target']
        st.write(f"**{a['name']}** ({active_sessions}/{a['target']})")
        if is_reached and st.button(f"Claim {a['id']}", key=f"ach_{a['id']}"):
            drop = roll_loot_box()
            if drop['type'] == "COSMETIC": purchases.append(drop['name'])
            else: tasks_done.append(f"{today_str}_ACH_RC{drop['val']}")
            claimed.append(a['id'])
            st.session_state["show_reward"] = drop
            save_all()
            st.rerun()
