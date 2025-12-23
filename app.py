import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
# Ensure you have your st.secrets["GITHUB_TOKEN"] set up in the Streamlit dashboard!
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("Secrets not found. Please set GITHUB_TOKEN in your Streamlit settings.")
    st.stop()

# REPO CONFIG
POSSIBLE_REPOS = ["leanderschepers-star/daily-rap-app", "leanderschepers-star/Daily-Rap-App"]
POSSIBLE_FILES = ["streamlit_app.py", "app.py"]
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

# TIME CONFIG
belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday
today_str = be_now.strftime('%d/%m/%Y')
yesterday_str = (be_now - timedelta(days=1)).strftime('%d/%m/%Y')

# --- 2. THE ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json(), "OK"
        return None, f"{r.status_code}"
    except: return None, "Conn Error"

def get_synced_data():
    errors = []
    # Try finding the source code in possible locations to extract lists
    for repo in POSSIBLE_REPOS:
        for filename in POSSIBLE_FILES:
            file_json, status = get_github_file(repo, filename)
            if file_json:
                content = base64.b64decode(file_json['content']).decode('utf-8')
                # Extract lists using Regex
                w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
                s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
                m_match = re.search(r"motivation\s*=\s*(\[.*?\])", content, re.DOTALL)
                try:
                    loc = {}
                    if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
                    if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
                    if m_match: exec(f"m_list = {m_match.group(1)}", {}, loc)
                    return loc.get('w_list', []), loc.get('s_list', []), loc.get('m_list', []), "OK", f"{repo}/{filename}"
                except: continue
            else:
                errors.append(f"{repo}/{filename}: {status}")
    
    return None, None, None, " | ".join(errors), "None"

def update_github_file(path, content, msg="Update"):
    file_data, status = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. DATA PROCESSING ---
words, sentences, motivation, sync_status, active_path = get_synced_data()
hist_file, hist_status = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""

# A. Calculate Balance
total_entries = full_text.count("DATE:")
purchases = re.findall(r'PURCHASE: (.*)', full_text)

shop_items = {
    "Studio Cat 🐈": 300,
    "Golden Mic 🎤": 1000,
    "Coffee Machine ☕": 150
}
spent = sum(shop_items.get(item, 0) for item in purchases)
user_points = (total_entries * 10) - spent

# B. Calculate Streak
dates_found = re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', full_text)
unique_dates = sorted(list(set(dates_found)), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True)

current_streak = 0
if unique_dates:
    # Check if we wrote today
    last_entry = unique_dates[0]
    last_date_obj = datetime.strptime(last_entry, '%d/%m/%Y')
    today_obj = datetime.strptime(today_str, '%d/%m/%Y')
    
    # Logic: If last entry is today or yesterday, the streak is alive
    diff = (today_obj - last_date_obj).days
    if diff <= 1:
        current_streak = 1
        # Count backwards
        previous_date = last_date_obj
        for i in range(1, len(unique_dates)):
            d = datetime.strptime(unique_dates[i], '%d/%m/%Y')
            if (previous_date - d).days == 1:
                current_streak += 1
                previous_date = d
            else:
                break
    else:
        current_streak = 0

# --- 4. THE UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤", layout="centered")

# SIDEBAR
with st.sidebar:
    st.title("🕹️ Studio Control")
    
    # Streak Display
    if current_streak > 0:
        st.metric("🔥 Streak", f"{current_streak} Days")
    else:
        st.write("❄️ Streak frozen (0 days)")
        
    st.metric("💰 Wallet", f"{user_points} RC")
    st.divider()
    
    st.subheader("📡 Connection")
    if sync_status == "OK":
        st.success("System Online")
        st.caption(f"Source: {active_path}")
    else:
        st.error("Offline")
        st.caption(sync_status)

# MAIN TABS
tab1, tab2, tab3 = st.tabs(["🎤 Daily Bars", "📜 History", "🛒 Shop"])

# --- TAB 1: DAILY BARS ---
with tab1:
    st.title("Todays Session")
    
    if words:
        # Use modulo to cycle through list based on day of year
        dw = words[day_of_year % len(words)]
        ds = sentences[day_of_year % len(sentences)]
        dm = motivation[day_of_year % len(motivation)]
        
        st.header(f"Word: {dw['word'].upper()}")
        st.info(f"📝 {ds}")
        st.warning(f"💡 {dm}")
        
        # Check if already wrote today
        if today_str in full_text:
            st.success("✅ You already dropped bars today! See 'History' tab.")
        
        user_lyrics = st.text_area("Drop your bars here:", height=250)
        
        if st.button("🚀 Save Bars"):
            if user_lyrics:
                entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{user_lyrics}\n"
                # Add new entry to the TOP of the file
                new_history = entry + "------------------------------\n" + full_text
                update_github_file(HISTORY_PATH, new_history)
                st.balloons()
                st.success("Saved to the cloud!")
                st.rerun()
            else:
                st.error("Write something first!")
    else:
        st.error("Could not load word lists. Check Github connection.")

# --- TAB 2: HISTORY ---
with tab2:
    st.header("🗄️ The Vault")
    # Split text by separator
    entries = full_text.split("------------------------------")
    for e in entries:
        if "DATE:" in e:
            # Simple parsing for display
            lines = e.strip().split('\n')
            date_line = next((l for l in lines if "DATE:" in l), "Unknown Date")
            word_line = next((l for l in lines if "WORD:" in l), "")
            
            with st.expander(f"🎵 {date_line} {word_line}"):
                st.text(e)

# --- TAB 3: SHOP ---
with tab3:
    st.header("🛒 The Studio Store")
    st.write(f"You have **{user_points} RC** to spend.")
    
    cols = st.columns(2)
    for index, (item, price) in enumerate(shop_items.items()):
        with cols[index % 2]:
            st.markdown(f"### {item}")
            st.write(f"**Price:** {price} RC")
            
            if user_points >= price:
                if st.button(f"Buy {item}", key=item):
                    # Add purchase to history (hidden entry)
                    purchase_entry = f"PURCHASE: {item}\nDATE: {today_str}\n"
                    new_history = purchase_entry + full_text
                    update_github_file(HISTORY_PATH, new_history)
                    st.success(f"Bought {item}!")
                    st.rerun()
            else:
                st.button(f"Buy {item}", disabled=True, key=item)
