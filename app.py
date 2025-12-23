import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# WE TRY BOTH REPO NAMES AND BOTH COMMON FILE NAMES
POSSIBLE_REPOS = ["leanderschepers-star/daily-rap-app", "leanderschepers-star/Daily-Rap-App"]
POSSIBLE_FILES = ["streamlit_app.py", "app.py"]

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday
today_str = be_now.strftime('%d/%m/%Y')

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
    # Attempt all combinations of Repo and File names
    errors = []
    for repo in POSSIBLE_REPOS:
        for filename in POSSIBLE_FILES:
            file_json, status = get_github_file(repo, filename)
            if file_json:
                content = base64.b64decode(file_json['content']).decode('utf-8')
                # Looking for your lists
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

# Calculate Balance
entries = full_text.count("DATE:")
purchases = re.findall(r'PURCHASE: (.*)', full_text)
spent = sum({"Studio Cat": 300}.get(item, 0) for item in purchases)
user_points = (entries * 10) - spent

# --- 4. THE UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.divider()
    st.subheader("📡 Connection Check")
    if sync_status == "OK":
        st.success(f"Connected: {active_path}")
    else:
        st.error("Connection Failed")
        st.write("Tried looking for:")
        st.caption(sync_status)

st.title("🎤 Rap Journal")

if words:
    dw = words[day_of_year % len(words)]
    st.header(dw['word'].upper())
    st.info(f"📝 {sentences[day_of_year % len(sentences)]}")
    st.warning(f"🔥 {motivation[day_of_year % len(motivation)]}")
else:
    st.error("Could not find the word list. Please check the sidebar 'Tried looking for' section.")

user_lyrics = st.text_area("Drop your bars:", height=300)
if st.button("🚀 Save Bars"):
    if words:
        entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{user_lyrics}\n"
        update_github_file(HISTORY_PATH, entry + "------------------------------\n" + full_text)
        st.success("Bars saved!")
        st.rerun()
