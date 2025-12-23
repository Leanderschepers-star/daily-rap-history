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
START_DATE = datetime(2025, 12, 19).date() # The official start date

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

all_blocks = [b.strip() for b in re.split(r'-{3,}', full_text) if b.strip()]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

entry_map = {}
for b in all_blocks:
    if "DATE:" in b and "LYRICS:" in b:
        d_str = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', b).group(1)
        d_obj = datetime.strptime(d_str, '%d/%m/%Y').date()
        # FILTER: Only include if on or after Dec 19th
        if d_obj >= START_DATE:
            entry_map[d_str] = b

unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys()], reverse=True)

# STREAK CALC (Logic stays same but starts from START_DATE)
current_streak = 0
if unique_dates:
    today_check = be_now.date()
    if (today_check - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# ECONOMY MATH
total_words = sum([len(e.split("LYRICS:")[-1].split()) for e in entry_map.values()])
user_points = (len(unique_dates) * 10) + ((total_words // 10) * 5)
if "first" in claimed: user_points += 50
if "week" in claimed: user_points += 250
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
user_points -= sum([shop_items.get(p, 0) for p in purchases])

inventory = purchases + (["Rookie Cap 🧢"] if "first" in claimed else []) + (["Silver Chain ⛓️"] if "week" in claimed else [])

# --- 4. UI SETUP ---
st.set_page_config(page_title="Studio Journal", layout="wide")
st.markdown("""<style>
    @keyframes floating { 0% {transform:translateY(0px);} 50% {transform:translateY(-10px);} 100% {transform:translateY(0px);} }
    .float { animation: floating 3s ease-in-out infinite; display: inline-block; }
    .neon-text { color: #ff00de; font-weight: bold; text-shadow: 0 0 10px #ff00de; text-align: center; font-size: 22px; }
</style>""", unsafe_allow_html=True)

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
with v2:
    if show_items.get("Studio Cat 🐈"): st.markdown('<div class="float"><img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueGZueCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/3o7TKMGpxx323X3NqE/giphy.gif" width="80"></div>', unsafe_allow_html=True)
with v3:
    cap = "🧢" if show_items.get("Rookie Cap 🧢") else ""
    st.markdown(f'<div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; text-align: center; position: relative;"><div style="font-size: 80px;">👤</div><div class="float" style="position: absolute; top: 10px; left: 0; right: 0; font-size: 40px;">{cap}</div></div>', unsafe_allow_html=True)
    if show_items.get("Neon Sign 🏮"): st.markdown('<p class="neon-text">ON AIR</p>', unsafe_allow_html=True)

# --- 6. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["✍️ New Session", "📂 The Vault", "🏪 Shop", "🏆 Career", "⚙️ Admin"])

with t1:
    st.subheader("Add Daily Bars")
    target_date = st.date_input("Which day are you recording for?", value=be_now.date(), min_value=START_DATE, max_value=be_now.date())
    target_str = target_date.strftime('%d/%m/%Y')
    
    if target_str in entry_map:
        st.warning(f"Session for {target_str} already exists in the Vault.")
        if st.button("Edit this day in Admin Tab"): st.write("Navigate to the Admin tab to modify old sessions.")
    else:
        lyrics = st.text_area(f"Write your lyrics for {target_str}...", height=250)
        if st.button("🚀 Record Session"):
            if lyrics.strip():
                # Logic: Add new entry to the TOP of the file
                new_entry = f"DATE: {target_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text
                update_github_file(new_entry)
                st.success(f"Bars for {target_str} locked in!")
                st.rerun()

with t2:
    st.header("Session Vault")
    # Loop from today back to the 19th
    delta = (be_now.date() - START_DATE).days
    for i in range(delta + 1):
        day = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        if day in entry_map:
            with st.expander(f"✅ {day}"):
                st.text(entry_map[day])
        else:
            st.info(f"⚪ {day}: No bars recorded.")

with t3:
    st.header("Shop")
    for item, price in shop_items.items():
        if item not in purchases:
            if st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    update_github_file(f"PURCHASE: {item}\n" + full_text)
                    st.rerun()

with t5:
    st.header("Admin Edit")
    st.caption("Fix typos or delete sessions manually here.")
    raw_edit = st.text_area("History File", full_text, height=500)
    if st.button("💾 Save History"):
        update_github_file(raw_edit, "Manual Update")
        st.rerun()
