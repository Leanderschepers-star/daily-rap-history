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

# --- 3. SYNC ENGINE (REPAIRED) ---
def get_daily_context():
    # Try the most likely repo for your word list
    target_repo = "leanderschepers-star/daily-rap-app"
    file_json = get_github_file(target_repo, "streamlit_app.py")
    if file_json:
        content = base64.b64decode(file_json['content']).decode('utf-8')
        # Cleaner Regex to find the lists
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        if w_match and s_match:
            try:
                # Use a safe dict for execution
                namespace = {}
                exec(f"w_list = {w_match.group(1)}", {}, namespace)
                exec(f"s_list = {s_match.group(1)}", {}, namespace)
                w = namespace['w_list']
                s = namespace['s_list']
                return w[day_of_year % len(w)]['word'], s[day_of_year % len(s)]
            except: pass
    return "MIC CHECK", "Spit some fire today."

daily_word, daily_sentence = get_daily_context()

# --- 4. DATA PARSING (STRICT) ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

# 1. Get ONLY lyrics entries (ignore purchases/claims for the history list)
all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = re.findall(r'PURCHASE: (.*)', full_text)
claimed = re.findall(r'CLAIMED: (.*)', full_text)

# 2. Parse Valid Dates
found_dates = []
for e in entries_raw:
    m = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)
    if m:
        d_obj = datetime.strptime(m.group(1), '%d/%m/%Y').date()
        # Filter out accidental future dates
        if d_obj <= be_now.date():
            found_dates.append(d_obj)

unique_dates = sorted(list(set(found_dates)), reverse=True)

# 3. Calculate Streak
current_streak = 0
if unique_dates:
    if unique_dates[0] >= yesterday_date:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break
    else: current_streak = 0

# 4. Points
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
achievements = [{"id": "r1", "name": "First Bars", "req": len(unique_dates) >= 1, "reward": 50}, {"id": "s7", "name": "7 Day Streak", "req": current_streak >= 7, "reward": 200}]
bonus_pts = sum([a['reward'] for a in achievements if a['id'] in claimed])
spent_pts = sum([shop_items.get(p.strip(), 0) for p in purchases])
user_points = (len(unique_dates) * 10) + bonus_pts - spent_pts

# --- 5. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

col_a, col_b = st.columns([4, 1])
col_b.link_button("🔙 Main App", MAIN_APP_URL)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    if st.button("🔄 Force Refresh"):
        st.cache_data.clear()
        st.rerun()

t1, t2, t3, t4 = st.tabs(["🎤 Write", "📜 Vault", "🛒 Shop", "🏆 Goals"])

with t1:
    st.header(f"Today: {daily_word.upper()}")
    st.info(f"📝 {daily_sentence}")
    
    # Check if entry exists for today (STRICT CHECK)
    if any(d.strftime('%d/%m/%Y') == today_str for d in unique_dates):
        st.success("✅ Session completed for today! Check the Vault to edit.")
    else:
        lyrics = st.text_area("Drop your bars:", height=250)
        if st.button("🚀 Save Session"):
            if lyrics:
                header = f"DATE: {today_str} | WORD: {daily_word}"
                new_entry = f"{header}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_entry, f"Entry {today_str}")
                st.rerun()

with t2:
    st.header("The Vault")
    if not entries_raw:
        st.write("No lyrics recorded yet.")
    else:
        for i, entry in enumerate(entries_raw):
            display_date = entry.splitlines()[0].replace("DATE: ", "")
            # Prevent showing weird claimed tags as titles
            if "CLAIMED" in display_date: continue 
            
            with st.expander(f"📅 {display_date}"):
                edit_area = st.text_area("Edit entry:", value=entry, height=200, key=f"v_{i}")
                if st.button("Save Edit", key=f"b_{i}"):
                    update_github_file(full_text.replace(entry, edit_area))
                    st.rerun()

with t3:
    st.header("Studio Store")
    c1, c2 = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        slot = c1 if i % 2 == 0 else c2
        with slot:
            if item in [p.strip() for p in purchases]:
                st.write(f"✅ {item} (Owned)")
            else:
                if st.button(f"Buy {item} ({price} RC)"):
                    if user_points >= price:
                        update_github_file(f"PURCHASE: {item}\n" + full_text, f"Bought {item}")
                        st.rerun()
                    else: st.error("Not enough RC!")

with t4:
    st.header("Achievements")
    for a in achievements:
        ca, cb = st.columns([3, 1])
        ca.write(f"**{a['name']}** (+{a['reward']} RC)")
        if a['id'] in claimed: cb.write("Claimed")
        elif a['req']:
            if cb.button("Claim", key=a['id']):
                update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                st.rerun()
        else: cb.write("🔒 Locked")
