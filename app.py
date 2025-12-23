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
MAIN_APP_URL = "https://daily-rap-app-woyet5jhwynnn9fbrjuvct.streamlit.app" 

# TIME (STRICT BELGIUM)
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_str = be_now.strftime('%d/%m/%Y')
day_of_year = be_now.timetuple().tm_yday
yesterday_date = (be_now - timedelta(days=1)).date()

# --- 2. GITHUB ENGINE ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200: return r.json(), "OK"
    except: return None, "Error"
    return None, "Error"

def update_github_file(content, msg="Update Content"):
    file_data, _ = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 3. SYNC WORDS FROM MAIN APP ---
# We try to grab the word lists so the Journal knows what the daily word is
POSSIBLE_REPOS = ["leanderschepers-star/daily-rap-app", "leanderschepers-star/Daily-Rap-App"]
def get_daily_context():
    for repo in POSSIBLE_REPOS:
        file_json, _ = get_github_file(repo, "streamlit_app.py")
        if file_json:
            content = base64.b64decode(file_json['content']).decode('utf-8')
            w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
            s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
            try:
                loc = {}
                exec(f"w = {w_match.group(1)}", {}, loc)
                exec(f"s = {s_match.group(1)}", {}, loc)
                word_obj = loc['w'][day_of_year % len(loc['w'])]
                sent_obj = loc['s'][day_of_year % len(loc['s'])]
                return word_obj['word'], sent_obj
            except: continue
    return "UNKNOWN", "No sentence found."

daily_word, daily_sentence = get_daily_context()

# --- 4. DATA PROCESSING ---
hist_json, _ = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

entries_raw = [e.strip() for e in re.split(r'-{3,}', full_text) if "DATE:" in e]
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed = re.findall(r'CLAIMED: (.*)', full_text)

# Streak Logic
found_dates = []
for e in entries_raw:
    m = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if m: found_dates.append(datetime.strptime(m.group(1), '%d/%m/%Y').date())
unique_dates = sorted(list(set(found_dates)), reverse=True)

current_streak = 0
if unique_dates:
    if unique_dates[0] >= yesterday_date:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break
    else: current_streak = 0

# Calculations
user_points = (len(unique_dates) * 10) - (len(purchases) * 150) # Simplified for now

# --- 5. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")
col_a, col_b = st.columns([4, 1])
col_b.link_button("🔙 Main App", MAIN_APP_URL)

tab1, tab2, tab3, tab4 = st.tabs(["🎤 Write", "📜 Vault", "🛒 Shop", "🏆 Goals"])

with tab1:
    st.title(f"Today: {daily_word.upper()}")
    st.caption(f"Sentence: {daily_sentence}")
    if today_str in full_text: st.success("✅ Already submitted for today.")
    
    lyrics = st.text_area("Drop bars:", height=200)
    if st.button("🚀 Save Session"):
        # WE SAVE THE WORD AND SENTENCE IN THE TEXT NOW
        header = f"DATE: {today_str} | WORD: {daily_word} | SENT: {daily_sentence}"
        new_entry = f"{header}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
        update_github_file(new_entry)
        st.rerun()

with tab2:
    st.header("The Vault")
    for i, entry in enumerate(entries_raw):
        # We clean the header for the expander title
        title = entry.splitlines()[0].replace("DATE: ", "")
        with st.expander(f"📅 {title}"):
            edited = st.text_area("Edit:", value=entry, height=150, key=f"v_{i}")
            if st.button("Save Edit", key=f"b_{i}"):
                update_github_file(full_text.replace(entry, edited))
                st.rerun()

with tab3: st.write("Shop content...")
with tab4: st.write("Goals content...")
