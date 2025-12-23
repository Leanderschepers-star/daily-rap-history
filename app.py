import streamlit as st
import datetime, requests, base64, pytz, re
from datetime import datetime, timedelta

# --- 1. CONFIG ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
# Double check these names on GitHub. Are they exactly like this?
APP_1_REPO = "leanderschepers-star/daily-rap-app" 
APP_1_FILE = "streamlit_app.py" 
REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday
today_str = be_now.strftime('%d/%m/%Y')

# --- 2. THE ENGINE (WITH DEBUGGING) ---
def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json(), "OK"
        else:
            return None, f"Error {r.status_code}: {r.reason}"
    except Exception as e:
        return None, str(e)

def update_github_file(path, content, msg="Update"):
    file_data, status = get_github_file(REPO_NAME, path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

def get_synced_data():
    file_json, status = get_github_file(APP_1_REPO, APP_1_FILE)
    if file_json:
        content = base64.b64decode(file_json['content']).decode('utf-8')
        # We look for the lists in your code
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        m_match = re.search(r"motivation\s*=\s*(\[.*?\])", content, re.DOTALL)
        try:
            loc = {}
            if w_match: exec(f"w_list = {w_match.group(1)}", {}, loc)
            if s_match: exec(f"s_list = {s_match.group(1)}", {}, loc)
            if m_match: exec(f"m_list = {m_match.group(1)}", {}, loc)
            return loc.get('w_list', []), loc.get('s_list', []), loc.get('m_list', []), "OK"
        except Exception as e:
            return [], [], [], f"Regex Error: {e}"
    return None, None, None, status

def calculate_stats(content):
    if not content: return 0, 0, []
    found_dates = set(re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', content))
    date_objs = {datetime.strptime(d, '%d/%m/%Y').date() for d in found_dates}
    today = be_now.date()
    streak = 0
    curr = today if today in date_objs else (today - timedelta(days=1))
    while curr in date_objs:
        streak += 1
        curr -= timedelta(days=1)
    earned = (content.count("DATE:") * 10) + (streak * 5)
    purchases = re.findall(r'PURCHASE: (.*)', content)
    prices = {"Studio Cat": 300, "Neon Layout": 150}
    spent = sum(prices.get(item, 0) for item in purchases)
    return earned - spent, streak, purchases

# --- 3. DATA FETCHING ---
words, sentences, motivation, sync_status = get_synced_data()
hist_file, hist_status = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""
user_points, user_streak, user_inventory = calculate_stats(full_text)

# --- 4. THE UI ---
st.set_page_config(page_title="Rap Studio", page_icon="🎤")

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"{user_streak} Days")
    
    st.divider()
    st.subheader("📡 Connection Status")
    if sync_status == "OK":
        st.success("Sync: Connected ✅")
    else:
        st.error(f"Sync: {sync_status} ❌")
        st.caption(f"Target: {APP_1_REPO}")

    st.divider()
    if "Studio Cat" not in user_inventory:
        if st.button(f"Buy Studio Cat (300 RC)", disabled=(user_points < 300)):
            update_github_file(HISTORY_PATH, "PURCHASE: Studio Cat\n" + full_text, "Bought Cat")
            st.rerun()
    else: st.info("🐱 Studio Cat Active")

st.title("🎤 Rap Journal")

if words:
    dw = words[day_of_year % len(words)]
    st.header(dw['word'].upper())
    st.info(f"📝 {sentences[day_of_year % len(sentences)]}")
    st.warning(f"🔥 {motivation[day_of_year % len(motivation)]}")
else:
    st.error("No words found. Please check the Connection Status in the sidebar.")

user_lyrics = st.text_area("Drop your bars:", height=300)
if st.button("🚀 Save Bars"):
    if words:
        entry = f"DATE: {today_str}\nWORD: {dw['word']}\nLYRICS:\n{user_lyrics}\n"
        update_github_file(HISTORY_PATH, entry + "------------------------------\n" + full_text)
        st.success("Bars saved!")
        st.rerun()
