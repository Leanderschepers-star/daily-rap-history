import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

# URLs
MAIN_APP_URL = "https://daily-rap-app.streamlit.app" 
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

# TIME
belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
today_str = be_now.strftime('%d/%m/%Y')

# --- 2. THE ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json(), "OK"
        return None, f"{r.status_code}"
    except: return None, "Conn Error"

def update_github_file(path, content, msg="Update"):
    file_data, _ = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA LOAD & FIXES ---
# Fetching fresh data every run
hist_file, _ = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""

# A. Calculations
entries_count = full_text.count("DATE:")
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed_achievements = re.findall(r'CLAIMED: (.*)', full_text)

# B. CORRECT STREAK LOGIC (Strict consecutive days)
dates_found = re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', full_text)
# Convert to set for unique dates, then to objects for math
unique_date_objs = sorted({datetime.strptime(d, '%d/%m/%Y').date() for d in dates_found}, reverse=True)

current_streak = 0
if unique_date_objs:
    today_date = be_now.date()
    last_entry_date = unique_date_objs[0]
    
    # If the last entry was today or yesterday, the streak is alive
    if (today_date - last_entry_date).days <= 1:
        current_streak = 1
        for i in range(len(unique_date_objs) - 1):
            # If the difference between this entry and the next one is exactly 1 day
            if (unique_date_objs[i] - unique_date_objs[i+1]).days == 1:
                current_streak += 1
            else:
                break
    else:
        current_streak = 0

# --- 4. THE UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

# NAVIGATION TOP BAR
col_nav1, col_nav2 = st.columns([4, 1])
with col_nav2:
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

with st.sidebar:
    st.title("🕹️ Control")
    st.metric("Wallet", f"{((entries_count * 10) - sum([150 for p in purchases]))} RC") # Simple math for now
    st.metric("Streak", f"🔥 {current_streak} Days")
    
    # Force Sync Button actually clears cache and reruns
    if st.button("🔄 Sync Cloud"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Write", "📜 History", "🛒 Shop", "🏆 Goals"])

# TAB 1: WRITE
with tab1:
    st.title("Rap Journal")
    if today_str in full_text: 
        st.success("✅ Bars dropped for today!")
    
    user_lyrics = st.text_area("Drop bars:", height=250, placeholder="Write your lyrics here...")
    if st.button("🚀 Save"):
        if user_lyrics:
            # We use a very clear separator to ensure history doesn't break
            separator = "\n" + "-"*30 + "\n"
            new_entry = f"DATE: {today_str}\nLYRICS:\n{user_lyrics}{separator}"
            update_github_file(HISTORY_PATH, new_entry + full_text)
            st.balloons()
            st.rerun()

# TAB 2: HISTORY (Fixed Parsing)
with tab2:
    st.header("The Vault")
    # Split by any number of dashes or specific separator
    entries = [e.strip() for e in re.split(r'-{3,}', full_text) if "DATE:" in e]
    
    if not entries:
        st.info("No history found yet. Write your first bars to start the vault!")
    else:
        for e in entries:
            # Extract date for the header
            date_match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
            title = date_match.group(1) if date_match else "Old Entry"
            with st.expander(f"📅 {title}"):
                st.text(e)

# TAB 3 & 4 (Keep your previous Shop/Goals logic here)
with tab3:
    st.write("Shop content goes here...")
with tab4:
    st.write("Goals content goes here...")
