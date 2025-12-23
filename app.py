import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

# YOUR UPDATED URL
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

def update_github_file(content, msg="Update Content"):
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

# Separate system logs from lyrics
all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed = re.findall(r'CLAIMED: (.*)', full_text)

# Map entries to dates (Strictly ignore future dates here)
entry_map = {}
for e in entries_raw:
    m = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if m:
        date_str = m.group(1)
        d_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
        if d_obj <= today_date: # Stop the "Future" entries bug
            entry_map[date_str] = e

# Streak Logic
unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)
current_streak = 0
if unique_dates:
    if (today_date - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# Points Math
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
user_points = (len(unique_dates) * 10) - sum([shop_items.get(p.strip(), 0) for p in purchases])

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)
    if st.button("🔄 Refresh Data"): st.rerun()

t1, t2, t3, t4 = st.tabs(["🎤 Write", "📜 Vault", "🛒 Shop", "🏆 Goals"])

# TAB 1: DAILY ENTRY
with t1:
    st.header("Today's Session")
    if today_str in entry_map:
        st.success(f"✅ Entry for {today_str} is secure in the vault.")
    else:
        lyrics = st.text_area("Drop your bars for today:", height=250)
        if st.button("🚀 Submit to Cloud"):
            if lyrics:
                # Add word of the day manually if needed, or just save lyrics
                new_entry = f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_entry, f"Daily bars: {today_str}")
                st.rerun()

# TAB 2: THE VAULT (Including Missing Days)
with t2:
    st.header("Historical Records")
    st.caption("Last 7 days of activity:")
    
    for i in range(7):
        target_date = today_date - timedelta(days=i)
        target_str = target_date.strftime('%d/%m/%Y')
        
        if target_str in entry_map:
            with st.expander(f"📅 {target_str}"):
                content = entry_map[target_str]
                edited_content = st.text_area("Edit recorded bars:", value=content, height=150, key=f"v_edit_{i}")
                if st.button("Update Entry", key=f"v_btn_{i}"):
                    update_github_file(full_text.replace(content, edited_content))
                    st.success("Updated!")
                    st.rerun()
        else:
            with st.expander(f"❌ {target_str} (No Entry Found)", expanded=False):
                st.error("Missing data for this date.")
                retro_lyrics = st.text_area("Recover missed bars:", placeholder="What did you write this day?", key=f"v_miss_{i}")
                if st.button("Fix This Day", key=f"v_rec_{i}"):
                    if retro_lyrics:
                        recovered = f"DATE: {target_str}\nLYRICS:\n{retro_lyrics}\n" + "-"*30 + "\n"
                        update_github_file(recovered + full_text, f"Recovered entry for {target_str}")
                        st.rerun()

# TAB 3 & 4: (Full Shop and Goals logic here)
with t3:
    st.header("The Shop")
    for item, price in shop_items.items():
        if item not in [p.strip() for p in purchases]:
            if st.button(f"Buy {item} ({price} RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text)
                    st.rerun()
        else: st.write(f"✅ {item} Owned")

with t4:
    st.header("Achievements")
    st.write(f"**Total Sessions:** {len(unique_dates)}")
    st.write(f"**Current Streak:** {current_streak} days")
