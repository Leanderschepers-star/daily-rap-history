import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
MAIN_APP_URL = "https://daily-rap-app.streamlit.app" 

# TIME (STRICT BELGIUM)
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz).date() 
today_str = be_now.strftime('%d/%m/%Y')
yesterday_date = be_now - timedelta(days=1)

# --- 2. GITHUB ENGINE ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json()
    except: return None
    return None

def update_github_file(content, msg="Update Content"):
    file_data = get_github_file(HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA PROCESSING ---
hist_json = get_github_file(HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# Separate entries by the dash separator
entries_raw = [e.strip() for e in re.split(r'-{3,}', full_text) if "DATE:" in e]
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed = re.findall(r'CLAIMED: (.*)', full_text)

# Parse Dates for Streak
found_dates = []
for e in entries_raw:
    match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if match:
        found_dates.append(datetime.strptime(match.group(1), '%d/%m/%Y').date())

unique_dates = sorted(list(set(found_dates)), reverse=True)

# CALCULATE STRICT STREAK
current_streak = 0
if unique_dates:
    last_entry = unique_dates[0]
    if last_entry >= yesterday_date:
        current_streak = 1
        for i in range(len(unique_dates) - 1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1:
                current_streak += 1
            else: break
    else: current_streak = 0

# SHOP & ACHIEVEMENTS DATA
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
achievements = [{"id": "r1", "name": "First Bars", "req": len(unique_dates) >= 1, "reward": 50}, {"id": "s7", "name": "7 Day Streak", "req": current_streak >= 7, "reward": 200}]

user_points = (len(unique_dates) * 10) + sum([a['reward'] for a in achievements if a['id'] in claimed]) - sum([shop_items.get(p, 0) for p in purchases])

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

# Top Nav
col_a, col_b = st.columns([4, 1])
col_b.link_button("🔙 Main App", MAIN_APP_URL)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    if st.button("🔄 Force Refresh"): st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Write", "📜 Vault & Edit", "🛒 Shop", "🏆 Goals"])

# TAB 1: WRITE
with tab1:
    st.header("Daily Session")
    if today_str in full_text: st.success("✅ Bars already saved for today!")
    lyrics = st.text_area("Write here:", height=200)
    if st.button("🚀 Save Session"):
        if lyrics:
            new_text = f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
            update_github_file(new_text, f"Entry for {today_str}")
            st.rerun()

# TAB 2: HISTORY & EDITING
with tab2:
    st.header("The Vault")
    if not entries_raw:
        st.write("No entries yet.")
    else:
        for i, entry in enumerate(entries_raw):
            # Extract header for display
            date_line = entry.splitlines()[0]
            with st.expander(f"📝 {date_line}"):
                # Local edit area
                edited_lyrics = st.text_area("Edit text:", value=entry, height=200, key=f"edit_{i}")
                if st.button("💾 Save Changes", key=f"btn_{i}"):
                    # Find the old entry in the full text and replace it with the new one
                    updated_full_text = full_text.replace(entry, edited_lyrics)
                    update_github_file(updated_full_text, f"Edited {date_line}")
                    st.success("Changes saved to GitHub!")
                    st.rerun()

# TAB 3: SHOP
with tab3:
    st.header("Studio Store")
    c1, c2 = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        target = c1 if i % 2 == 0 else c2
        with target:
            if item in purchases: st.write(f"✅ {item} (Owned)")
            elif st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text, f"Purchased {item}")
                    st.rerun()

# TAB 4: GOALS
with tab4:
    st.header("Milestones")
    for a in achievements:
        col1, col2 = st.columns([3, 1])
        col1.write(f"**{a['name']}** ({a['reward']} RC)")
        if a['id'] in claimed: col2.write("Claimed")
        elif a['req']:
            if col2.button("Claim", key=a['id']):
                update_github_file(f"CLAIMED: {a['id']}\n" + full_text, f"Claimed {a['name']}")
                st.rerun()
