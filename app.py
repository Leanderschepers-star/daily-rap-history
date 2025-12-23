import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

MAIN_APP_URL = "https://daily-rap-app-woyet5jhwynnn9fbrjuvct.streamlit.app" 
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_date = be_now.date()
today_str = today_date.strftime('%d/%m/%Y')

# --- 2. GITHUB ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json()
    except: return None
    return None

def update_github_file(content, msg="Update"):
    file_data = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA PARSING & ADVANCED ECONOMY ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# A. Basic Parsing
all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

# B. Date Mapping & Streak Calculation
entry_map = {}
for e in entries_raw:
    m = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if m:
        d_str = m.group(1)
        if datetime.strptime(d_str, '%d/%m/%Y').date() <= today_date:
            entry_map[d_str] = e

unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

current_streak = 0
if unique_dates:
    if (today_date - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# C. Definitions (Crucial to define BEFORE math)
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
achievements = [
    {"id": "first", "name": "Rookie of the Year", "how": "Submit 1st entry.", "req": len(unique_dates) >= 1, "reward_text": "50 RC + Rookie Cap 🧢", "rc": 50, "item": "Rookie Cap 🧢"},
    {"id": "week", "name": "Weekly Grind", "how": "7-day streak.", "req": current_streak >= 7, "reward_text": "250 RC + Silver Chain ⛓️", "rc": 250, "item": "Silver Chain ⛓️"},
    {"id": "month", "name": "Legendary Status", "how": "30-day streak.", "req": current_streak >= 30, "reward_text": "Platinum Plaque 💿", "rc": 0, "item": "Platinum Plaque 💿"}
]

# D. Word Count Calculation
total_words = 0
for entry in entries_raw:
    lyric_content = entry.split("LYRICS:")[-1]
    total_words += len(lyric_content.split())

# E. Studio Level Logic
if total_words < 200: studio_level, level_name = 1, "Bedroom Producer"
elif total_words < 500: studio_level, level_name = 2, "Underground Artist"
elif total_words < 1000: studio_level, level_name = 3, "Studio Sessionist"
elif total_words < 2500: studio_level, level_name = 4, "Professional Rapper"
else: studio_level, level_name = 5, "Chart Topper"

# F. Final Rewards Math
session_rewards = len(unique_dates) * 10
word_rewards = (total_words // 10) * 5
bonus_points = sum([a['rc'] for a in achievements if a['id'] in claimed])
spent_points = sum([shop_items.get(p, 0) for p in purchases])

user_points = session_rewards + word_rewards + bonus_points - spent_points
inventory = purchases + [a['item'] for a in achievements if a['id'] in claimed and 'item' in a]

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤", layout="wide")

with st.sidebar:
    # Artist Profile Emoji
    profile_emoji = "👤"
    if "Rookie Cap 🧢" in inventory: profile_emoji = "🧢"
    if "Silver Chain ⛓️" in inventory: profile_emoji = "💎"

    st.title(f"{profile_emoji} Dashboard")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    
    st.divider()
    st.write(f"📈 **Studio Level: {studio_level}**")
    st.progress(min(total_words / 2500, 1.0))
    st.caption(f"Role: {level_name}")
    st.write(f"Total Words: `{total_words}`")
    
    st.divider()
    st.subheader("📦 Display Manager")
    show_items = {}
    for item in inventory:
        show_items[item] = st.checkbox(f"Show {item}", value=True)
    
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# --- 5. STUDIO SCREEN ---
st.title("🎤 My Studio")

# Physical Decor
studio_cols = st.columns(5)
if "Coffee Machine ☕" in inventory and show_items.get("Coffee Machine ☕"):
    studio_cols[0].info("☕ **Brewing...**")
if "Studio Cat 🐈" in inventory and show_items.get("Studio Cat 🐈"):
    studio_cols[1].warning("🐈 **Napping...**")
if "Neon Sign 🏮" in inventory and show_items.get("Neon Sign 🏮"):
    studio_cols[2].error("🏮 **ON AIR**")
if "Subwoofer 🔊" in inventory and show_items.get("Subwoofer 🔊"):
    studio_cols[3].success("🔊 **Booming**")
if "Platinum Plaque 💿" in inventory and show_items.get("Platinum Plaque 💿"):
    studio_cols[4].help("💿 **Classic**")

st.divider()

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["✍️ Write", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t1:
    if today_str in entry_map: 
        st.success("Session recorded for today!")
    else:
        lyrics = st.text_area("Drop fire bars:", height=300)
        if st.button("🚀 Record Session"):
            update_github_file(f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text)
            st.rerun()

# (Tabs 2, 3, 4 logic follows the same structure as before)
# ... [Rest of your Tab UI code]

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤", layout="wide")

# SIDEBAR: DASHBOARD + DISPLAY MANAGER
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    st.divider()
    
    st.subheader("📦 Display Manager")
    st.caption("Check items to show them in your studio")
    
    # Create a dictionary to track what the user wants to show
    show_items = {}
    for item in inventory:
        show_items[item] = st.checkbox(f"Display {item}", value=True)
    
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# --- 5. THE ACTUAL WEBSITE SCREEN (THE STUDIO) ---
# This section renders items directly on the page based on Display Manager
st.title("🎤 My Recording Studio")

# Physical Studio Layout (Items appear here)
studio_cols = st.columns(5)

if "Coffee Machine ☕" in inventory and show_items.get("Coffee Machine ☕"):
    studio_cols[0].info("☕ **Coffee is Brewing**")
if "Studio Cat 🐈" in inventory and show_items.get("Studio Cat 🐈"):
    studio_cols[1].warning("🐈 **Cat is Napping**")
if "Neon Sign 🏮" in inventory and show_items.get("Neon Sign 🏮"):
    studio_cols[2].error("🏮 **ON AIR**")
if "Subwoofer 🔊" in inventory and show_items.get("Subwoofer 🔊"):
    studio_cols[3].success("🔊 **Bass Booming**")
if "Platinum Plaque 💿" in inventory and show_items.get("Platinum Plaque 💿"):
    studio_cols[4].help("💿 **Top 100 Hit**")

# Wearables (Emojis added to your header)
wearables = ""
if "Rookie Cap 🧢" in inventory and show_items.get("Rookie Cap 🧢"): wearables += " 🧢"
if "Silver Chain ⛓️" in inventory and show_items.get("Silver Chain ⛓️"): wearables += " ⛓️"
st.subheader(f"Current Artist Style: {wearables if wearables else 'Basic 👤'}")

st.divider()

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["✍️ Write Bars", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t1:
    if today_str in entry_map: 
        st.success("Today's session is locked in!")
    else:
        lyrics = st.text_area("Drop your fire here...", height=300)
        if st.button("🚀 Record Session"):
            update_github_file(f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text)
            st.rerun()

with t2:
    st.header("The Vault")
    for i in range(7):
        target_str = (today_date - timedelta(days=i)).strftime('%d/%m/%Y')
        if target_str in entry_map:
            with st.expander(f"📅 {target_str}"):
                st.text(entry_map[target_str])
        else:
            with st.expander(f"❌ {target_str} (Missing)"):
                st.write("No recording found.")

with t3:
    st.header("Shop")
    cols = st.columns(3)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i % 3]:
            if item in purchases: st.write(f"✅ {item} Owned")
            elif st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text)
                    st.rerun()

with t4:
    st.header("Achievements")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{a['name']}**")
            st.caption(f"How: {a['how']} | Reward: {a['reward_text']}")
        with c2:
            if a['id'] in claimed: st.success("Claimed")
            elif a['req']:
                if st.button("Claim", key=a['id']):
                    update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                    st.rerun()
            else: st.write("🔒 Locked")
