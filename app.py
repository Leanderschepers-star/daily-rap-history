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
START_DATE = datetime(2025, 12, 19).date()

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

# Regex to find blocks of sessions
blocks = [b.strip() for b in re.split(r'-{10,}', full_text) if b.strip()]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

entry_map = {}
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            # Only keep actual lyric content, strip out metadata for editing
            lyric_content = b.split("LYRICS:")[-1].strip() if "LYRICS:" in b else ""
            entry_map[d_str] = lyric_content

# --- 4. ECONOMY & INVENTORY ---
unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys() if datetime.strptime(d, '%d/%m/%Y').date() >= START_DATE], reverse=True)
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
user_points = (len(unique_dates) * 10) + ((total_words // 10) * 5)
if "first" in claimed: user_points += 50
if "week" in claimed: user_points += 250
shop_costs = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}
user_points -= sum([shop_costs.get(p, 0) for p in purchases])
inventory = purchases + (["Rookie Cap 🧢"] if "first" in claimed else []) + (["Silver Chain ⛓️"] if "week" in claimed else [])

# --- 5. UI SETUP ---
st.set_page_config(page_title="Studio Journal", layout="wide")
st.markdown("""<style>
    @keyframes floating { 0% {transform:translateY(0px);} 50% {transform:translateY(-10px);} 100% {transform:translateY(0px);} }
    .float { animation: floating 3s ease-in-out infinite; display: inline-block; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(255,255,255,0.05); border-radius: 5px; padding: 10px; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.divider()
    show_items = {item: st.checkbox(f"Show {item}", value=True) for item in inventory}
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# --- 6. STUDIO VISUALS ---
v1, v2, v3, v4, v5 = st.columns(5)
with v3:
    cap = "🧢" if show_items.get("Rookie Cap 🧢") else ""
    st.markdown(f'<div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; text-align: center; position: relative;"><div style="font-size: 80px;">👤</div><div class="float" style="position: absolute; top: 10px; left: 0; right: 0; font-size: 40px;">{cap}</div></div>', unsafe_allow_html=True)

# --- 7. TABS ---
t1, t2, t3, t4 = st.tabs(["✍️ New Session", "📂 The Vault", "🏪 Shop", "🏆 Career"])

with t1:
    st.subheader("New Session")
    target_date = st.date_input("Date", value=be_now.date(), min_value=START_DATE)
    t_str = target_date.strftime('%d/%m/%Y')
    
    if t_str in entry_map:
        st.info(f"Day {t_str} is already in the Vault. Go there to edit it.")
    else:
        new_lyr = st.text_area("Drop your bars...", height=300)
        if st.button("🚀 Record"):
            # Construct new history: Metadata first, then sessions
            meta = "\n".join([f"PURCHASE: {p}" for p in purchases] + [f"CLAIMED: {c}" for c in claimed])
            sessions = f"\n------------------------------\nDATE: {t_str}\nLYRICS:\n{new_lyr}\n------------------------------"
            # Add existing entries
            for d, l in entry_map.items():
                sessions += f"\nDATE: {d}\nLYRICS:\n{l}\n------------------------------"
            update_github_file(meta + sessions)
            st.rerun()

with t2:
    st.header("The Vault")
    delta = (be_now.date() - START_DATE).days
    for i in range(delta + 1):
        day = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        
        with st.expander(f"{'✅' if day in entry_map else '⚪'} {day}"):
            if day in entry_map:
                # EDIT MODE FOR SPECIFIC DATE
                edited_lyrics = st.text_area("Edit Lyrics", value=entry_map[day], height=200, key=f"edit_{day}")
                if st.button("💾 Save Changes", key=f"btn_{day}"):
                    # Rebuild the entire file with the updated lyric for this date
                    entry_map[day] = edited_lyrics
                    meta = "\n".join([f"PURCHASE: {p}" for p in purchases] + [f"CLAIMED: {c}" for c in claimed])
                    sessions = ""
                    for d, l in entry_map.items():
                        sessions += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{l}\n------------------------------"
                    update_github_file(meta + sessions)
                    st.success(f"Updated {day}!")
                    st.rerun()
            else:
                st.write("No session recorded.")

with t3:
    st.header("Shop")
    for item, price in shop_costs.items():
        if item not in purchases:
            if st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    update_github_file(full_text + f"\nPURCHASE: {item}")
                    st.rerun()

with t4:
    st.header("Career")
    # Quick claim for First Entry
    if "first" not in claimed and len(unique_dates) >= 1:
        if st.button("Claim Rookie Reward"):
            update_github_file(full_text + "\nCLAIMED: first")
            st.rerun()
    elif "first" in claimed:
        st.write("🏆 Rookie of the Year")
