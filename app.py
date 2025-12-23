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
NTFY_TOPIC = "leanders_daily_bars"

be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
START_DATE = datetime(2025, 12, 19).date()

# --- 2. GITHUB & NOTIF ENGINES ---
def send_notif(title, message):
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", 
                     data=message.encode('utf-8'),
                     headers={"Title": title, "Priority": "default", "Tags": "microphone,fire"})
    except: pass

def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(content, msg="Update"):
    file_data = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA & LOGIC ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))

entry_map = {}
# Improved Regex: Handles spaces and different line breaks better
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE:\s*(\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            # Find lyrics between "LYRICS:" and the next separator/end
            lyr_match = re.search(r'LYRICS:\s*(.*?)(?=\s*---|$)', b, re.DOTALL)
            lyr = lyr_match.group(1).strip() if lyr_match else ""
            if lyr: entry_map[d_str] = lyr

# Determine valid dates for streak
db_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

current_streak = 0
if db_dates:
    if (be_now.date() - db_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(db_dates)-1):
            if (db_dates[i] - db_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}

achievements = [
    {"id": "first", "name": "Underground Artist", "reward": "Standard Theme", "req": len(db_dates) >= 1, "rc": 50},
    {"id": "week", "name": "Rising Star", "reward": "Blue Studio Theme 🟦", "req": current_streak >= 7, "rc": 250},
    {"id": "month", "name": "Rap Legend", "reward": "Gold Vault Theme 🟨", "req": current_streak >= 30, "rc": 500}
]

user_points = (len(db_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([shop_items.get(p, 0) for p in purchases])

def rebuild_and_save(new_map, new_pur, new_cla):
    content = ""
    for p in sorted(new_pur): content += f"PURCHASE: {p}\n"
    for c in sorted(new_cla): content += f"CLAIMED: {c}\n"
    for d in sorted(new_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        if new_map[d].strip(): # Only save if there is content
            content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_map[d]}\n------------------------------"
    update_github_file(content)

# --- 4. THEME ENGINE ---
st.set_page_config(page_title="Studio Journal", layout="wide")

bg_style = "background: #121212;" 
if "month" in claimed: bg_style = "background: radial-gradient(circle, #2b2100 0%, #121212 100%);"
elif "week" in claimed: bg_style = "background: radial-gradient(circle, #001a33 0%, #121212 100%);"

neon_effect = "text-shadow: 0 0 10px #ff0055, 0 0 20px #ff0055;" if "Neon Sign 🏮" in purchases else ""
sub_animation = "animation: bass 0.5s infinite alternate;" if "Subwoofer 🔊" in purchases else ""

st.markdown(f"""
<style>
    .stApp {{ {bg_style} }}
    @keyframes bass {{ from {{ transform: scale(1); }} to {{ transform: scale(1.02); }} }}
    .stats-card {{
        background: rgba(255, 255, 255, 0.05);
        padding: 20px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center; {sub_animation}
    }}
    .neon-text {{ {neon_effect} color: white; font-weight: bold; font-size: 24px; }}
</style>
""", unsafe_allow_html=True)

# --- 5. UI ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.write("Current Status:")
    for a in achievements:
        if a['id'] in claimed: st.success(f"🏆 {a['name']}")
    st.divider()
    st.write("📦 Installed Gear:")
    for item in purchases: st.caption(f"✅ {item}")
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

st.markdown(f'<p class="neon-text">STUDIO SESSION: {be_now.strftime("%H:%M")}</p>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Words</h3><h2>{total_words}</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{current_streak}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Balance</h3><h2>{user_points}</h2></div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["✍️ Recording", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t1:
    d_input = st.date_input("Session Date", value=be_now.date())
    d_str = d_input.strftime('%d/%m/%Y')
    existing_lyr = entry_map.get(d_str, "")
    if existing_lyr: st.warning("Bars already exist for this date. Editing will overwrite.")
    new_lyr = st.text_area("Drop bars...", value=existing_lyr, height=300)
    if st.button("🚀 Record Session"):
        entry_map[d_str] = new_lyr
        rebuild_and_save(entry_map, purchases, claimed)
        st.rerun()

with t2:
    st.header("The Vault")
    # THE FIX: Generate ALL dates from start until today
    num_days = (be_now.date() - START_DATE).days
    for i in range(num_days + 1):
        target_dt = be_now.date() - timedelta(days=i)
        day_str = target_dt.strftime('%d/%m/%Y')
        
        has_entry = day_str in entry_map
        icon = "✅" if has_entry else "⚪"
        
        with st.expander(f"{icon} {day_str}"):
            v_lyr = st.text_area("Lyrics", value=entry_map.get(day_str, ""), key=f"v_{day_str}", height=200)
            if st.button("Save to Vault", key=f"b_{day_str}"):
                entry_map[day_str] = v_lyr
                rebuild_and_save(entry_map, purchases, claimed)
                st.rerun()

with t3:
    st.header("Studio Upgrades")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i%2]:
            if item in purchases: st.info(f"OWNED: {item}")
            elif st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()

with t4:
    st.header("Career Rewards")
    for a in achievements:
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.write(f"**{a['name']}**")
            st.caption(f"Unlocks: {a['reward']}")
        with col_b:
            if a['id'] in claimed: st.success("Active")
            elif a['req']:
                if st.button("Unlock", key=a['id']):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()
            else: st.write("🔒 Locked")
