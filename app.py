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

# --- 3. DATA PARSING & ECONOMY ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

# Mapping entries to check for "Today" correctly
entry_map = {}
for e in entries_raw:
    date_match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if date_match:
        entry_map[date_match.group(1)] = e

unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

# STREAK CALC
current_streak = 0
if unique_dates:
    if (today_date - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# WORD COUNT & LEVEL
total_words = 0
for entry in entries_raw:
    lyric_part = entry.split("LYRICS:")[-1]
    total_words += len(lyric_part.split())

if total_words < 200: studio_level, level_name = 1, "Bedroom Producer"
elif total_words < 500: studio_level, level_name = 2, "Underground Artist"
elif total_words < 1000: studio_level, level_name = 3, "Studio Sessionist"
elif total_words < 2500: studio_level, level_name = 4, "Professional Rapper"
else: studio_level, level_name = 5, "Chart Topper"

# SHOP & POINTS
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
achievements = [
    {"id": "first", "name": "Rookie of the Year", "how": "Submit 1st entry.", "req": len(unique_dates) >= 1, "reward_text": "50 RC + Rookie Cap 🧢", "rc": 50, "item": "Rookie Cap 🧢"},
    {"id": "week", "name": "Weekly Grind", "how": "7-day streak.", "req": current_streak >= 7, "reward_text": "250 RC + Silver Chain ⛓️", "rc": 250, "item": "Silver Chain ⛓️"},
    {"id": "month", "name": "Legendary Status", "how": "30-day streak.", "req": current_streak >= 30, "reward_text": "Platinum Plaque 💿", "rc": 0, "item": "Platinum Plaque 💿"}
]

user_points = (len(unique_dates) * 10) + ((total_words // 10) * 5) + sum([a['rc'] for a in achievements if a['id'] in claimed]) - sum([shop_items.get(p, 0) for p in purchases])
inventory = purchases + [a['item'] for a in achievements if a['id'] in claimed and 'item' in a]

# --- 4. UI SETUP & CSS ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    @keyframes floating { 0% {transform:translateY(0px);} 50% {transform:translateY(-10px);} 100% {transform:translateY(0px);} }
    @keyframes pulse { 0% {transform:scale(1);} 50% {transform:scale(1.1);} 100% {transform:scale(1);} }
    @keyframes neon { 0% {text-shadow: 0 0 5px #fff, 0 0 10px #ff00de;} 100% {text-shadow: 0 0 10px #fff, 0 0 20px #ff00de, 0 0 30px #ff00de;} }
    @keyframes rotate { from {transform: rotate(0deg);} to {transform: rotate(360deg);} }
    .float { animation: floating 3s ease-in-out infinite; display: inline-block; }
    .pulse { animation: pulse 1.5s ease-in-out infinite; display: inline-block; }
    .neon-text { color: #ff00de; font-weight: bold; animation: neon 1.5s ease-in-out infinite alternate; text-align: center; font-size: 22px; }
    .disc { animation: rotate 4s linear infinite; border-radius: 50%; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.markdown(f"### 💰 Wallet: **{user_points} RC**")
    st.markdown(f"### 🔥 Streak: **{current_streak} Days**")
    st.divider()
    st.write(f"📈 **Level {studio_level}: {level_name}**")
    st.progress(min(total_words / 2500, 1.0))
    st.divider()
    st.subheader("📦 Display Manager")
    show_items = {item: st.checkbox(f"Show {item}", value=True, key=f"inv_{item}") for item in inventory}
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)
    if st.button("🔄 Refresh Studio"): st.rerun()

# --- 5. VISUAL STUDIO SCREEN ---
st.title("🎤 My Recording Studio")

v1, v2, v3, v4, v5 = st.columns(5)

with v1: 
    if "Coffee Machine ☕" in inventory and show_items.get("Coffee Machine ☕"):
        st.markdown('<div class="float"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHJqM2Z3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3bmZ3JlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/Xev9z0XG0O2KszJshO/giphy.gif" width="70"></div>', unsafe_allow_html=True)
        st.caption("Fresh Brew")

with v2:
    if "Studio Cat 🐈" in inventory and show_items.get("Studio Cat 🐈"):
        st.markdown('<div class="float"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/3o7TKMGpxx323X3NqE/giphy.gif" width="80"></div>', unsafe_allow_html=True)
        st.caption("Studio Manager")

with v3: # MANNEQUIN SECTION
    cap_icon = "🧢" if "Rookie Cap 🧢" in inventory and show_items.get("Rookie Cap 🧢") else ""
    chain_icon = "⛓️" if "Silver Chain ⛓️" in inventory and show_items.get("Silver Chain ⛓️") else ""
    
    # We build the HTML string carefully to avoid rendering errors
    mannequin_html = f"""
    <div style="background: rgba(255, 255, 255, 0.05); border: 2px solid #444; border-radius: 15px; padding: 20px; text-align: center; position: relative; min-height: 200px;">
        <div style="font-size: 80px; position: relative; z-index: 1;">👤</div>
        <div class="float" style="position: absolute; top: 10px; left: 0; right: 0; font-size: 40px; z-index: 2;">{cap_icon}</div>
        <div class="pulse" style="position: absolute; top: 85px; left: 0; right: 0; font-size: 40px; z-index: 2;">{chain_icon}</div>
        <p style="color: gray; font-size: 12px; margin-top: 10px;">Artist Avatar</p>
    </div>
    """
    st.markdown(mannequin_html, unsafe_allow_html=True)
    
    if "Neon Sign 🏮" in inventory and show_items.get("Neon Sign 🏮"):
        st.markdown('<br><div class="neon-text">🔴 ON AIR</div>', unsafe_allow_html=True)

with v4:
    if "Subwoofer 🔊" in inventory and show_items.get("Subwoofer 🔊"):
        st.markdown('<div class="pulse"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/3o7TKXpT097m0R9F2E/giphy.gif" width="80"></div>', unsafe_allow_html=True)
        st.caption("Feel the Bass")

with v5:
    if "Golden Mic 🎤" in inventory and show_items.get("Golden Mic 🎤"):
        st.markdown('<div class="float"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/l41lTfO3vDskGf7UY/giphy.gif" width="70"></div>', unsafe_allow_html=True)
        st.caption("Pro Mic")
    elif "Platinum Plaque 💿" in inventory and show_items.get("Platinum Plaque 💿"):
        st.markdown('<div class="float"><img class="disc" src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/3o7TKDkDbIDJieU2Zy/giphy.gif" width="60"></div>', unsafe_allow_html=True)
        st.caption("Hit Record")

st.divider()

# --- 6. TABS ---
t1, t2, t3, t4 = st.tabs(["✍️ Sessions", "📂 The Vault", "🏪 Shop", "🏆 Career"])

with t1:
    if today_str in entry_map:
        st.success("Today's session is locked in!")
        st.info("Come back tomorrow to drop more bars!")
    else:
        lyrics = st.text_area("Record your bars...", height=250, placeholder="Drop your fire here...")
        if st.button("🚀 Finalize Recording"):
            if lyrics.strip():
                new_entry = f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_entry, msg=f"Session {today_str}")
                st.rerun()
            else:
                st.warning("Write something first!")

with t2:
    st.header("The Vault")
    for i in range(10):
        d = (today_date - timedelta(days=i)).strftime('%d/%m/%Y')
        if d in entry_map:
            with st.expander(f"📅 {d}"):
                st.text(entry_map[d])

with t3:
    st.header("Shop")
    cols = st.columns(3)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i % 3]:
            if item in purchases: st.success(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text)
                    st.rerun()
                else: st.error("Not enough RC!")

with t4:
    st.header("Achievements")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{a['name']}**")
            st.caption(f"{a['how']} | Reward: {a['reward_text']}")
        with c2:
            if a['id'] in claimed: st.success("Claimed")
            elif a['req']:
                if st.button("Claim", key=a['id']):
                    update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                    st.rerun()
            else: st.write("🔒 Locked")
