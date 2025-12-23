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

# --- 3. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# Separate the file into Blocks
all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]

# Filter strictly for LYRIC entries to prevent "Empty Today" bug
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

# Map only real lyric sessions
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

# ECONOMY MATH
total_words = sum([len(e.split("LYRICS:")[-1].split()) for e in entries_raw])
user_points = (len(unique_dates) * 10) + ((total_words // 10) * 5)
# Add Achievement RC
if "first" in claimed: user_points += 50
if "week" in claimed: user_points += 250
# Subtract Shop costs
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
user_points -= sum([shop_items.get(p, 0) for p in purchases])

inventory = purchases + (["Rookie Cap 🧢"] if "first" in claimed else []) + (["Silver Chain ⛓️"] if "week" in claimed else []) + (["Platinum Plaque 💿"] if "month" in claimed else [])

# --- 4. UI & ANIMATIONS ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤", layout="wide")
st.markdown("""
<style>
    @keyframes floating { 0% {transform:translateY(0px);} 50% {transform:translateY(-10px);} 100% {transform:translateY(0px);} }
    @keyframes pulse { 0% {transform:scale(1);} 50% {transform:scale(1.1);} 100% {transform:scale(1);} }
    .float { animation: floating 3s ease-in-out infinite; display: inline-block; }
    .pulse { animation: pulse 1.5s ease-in-out infinite; display: inline-block; }
    .neon-text { color: #ff00de; font-weight: bold; text-shadow: 0 0 10px #ff00de; text-align: center; font-size: 22px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"{current_streak} Days")
    st.divider()
    show_items = {item: st.checkbox(f"Show {item}", value=True) for item in inventory}
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# --- 5. STUDIO VISUALS ---
st.title("🎤 My Recording Studio")
v1, v2, v3, v4, v5 = st.columns(5)
with v1: 
    if show_items.get("Coffee Machine ☕"): st.markdown('<div class="float">☕</div>', unsafe_allow_html=True)
with v2:
    if show_items.get("Studio Cat 🐈"): st.markdown('<div class="float"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/3o7TKMGpxx323X3NqE/giphy.gif" width="80"></div>', unsafe_allow_html=True)

with v3: # MANNEQUIN
    cap = "🧢" if show_items.get("Rookie Cap 🧢") else ""
    chain = "⛓️" if show_items.get("Silver Chain ⛓️") else ""
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); border: 1px solid #444; border-radius: 15px; padding: 20px; text-align: center; position: relative;">
        <div style="font-size: 80px;">👤</div>
        <div class="float" style="position: absolute; top: 10px; left: 0; right: 0; font-size: 40px;">{cap}</div>
        <div class="pulse" style="position: absolute; top: 85px; left: 0; right: 0; font-size: 40px;">{chain}</div>
    </div>
    """, unsafe_allow_html=True)
    if show_items.get("Neon Sign 🏮"): st.markdown('<p class="neon-text">ON AIR</p>', unsafe_allow_html=True)

# --- 6. FUNCTIONALITY ---
t1, t2, t3, t4, t5 = st.tabs(["✍️ Sessions", "📂 The Vault", "🏪 Shop", "🏆 Career", "⚙️ Admin"])

with t1:
    if today_str in entry_map:
        st.success("Session finished! See you tomorrow.")
    else:
        lyrics = st.text_area("Record today's bars...", height=200)
        if st.button("🚀 Submit"):
            if lyrics:
                new_block = f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_block)
                st.rerun()

with t2:
    st.header("Session Vault")
    # Shows the last 14 days, even if empty
    for i in range(14):
        check_date = (today_date - timedelta(days=i)).strftime('%d/%m/%Y')
        if check_date in entry_map:
            with st.expander(f"✅ {check_date}"):
                st.text(entry_map[check_date])
        else:
            st.info(f"⚪ {check_date}: No session recorded.")

with t3:
    st.header("Studio Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i%2]:
            if item in purchases: st.write(f"Owned: {item}")
            elif st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text)
                    st.rerun()

with t4:
    st.header("Career achievements")
    for a in [
        {"id": "first", "name": "Rookie", "req": len(unique_dates)>=1},
        {"id": "week", "name": "Grinder", "req": current_streak>=7}
    ]:
        if a['id'] in claimed: st.write(f"🏆 {a['name']}")
        elif a['req']:
            if st.button(f"Claim {a['name']}"):
                update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                st.rerun()
        else: st.write(f"🔒 {a['name']}")

with t5:
    st.header("Danger Zone")
    st.warning("Edit your raw history file below. Be careful!")
    edited_text = st.text_area("Raw History Data", full_text, height=400)
    if st.button("💾 Save All Changes"):
        update_github_file(edited_text, "Manual Admin Edit")
        st.success("History updated!")
        st.rerun()
