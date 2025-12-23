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

# Extract Purchases and Claims
purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))

# Extract Lyrics using Regex (Robust to varying dash counts)
entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE: (\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr = b.split("LYRICS:")[-1].strip() if "LYRICS:" in b else ""
            if lyr: entry_map[d_str] = lyr

# Filter for Start Date (19/12/2025)
valid_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys() if datetime.strptime(d, '%d/%m/%Y').date() >= START_DATE], reverse=True)

# --- 4. STATS & ECONOMY ---
current_streak = 0
if valid_dates:
    if (be_now.date() - valid_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(valid_dates)-1):
            if (valid_dates[i] - valid_dates[i+1]).days == 1: current_streak += 1
            else: break

total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
shop_prices = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}

# Rewards Logic
achievements = [
    {"id": "first", "name": "Rookie of the Year", "desc": "Drop 1st bars", "req": len(valid_dates) >= 1, "rc": 50, "item": "Rookie Cap 🧢"},
    {"id": "week", "name": "Weekly Grind", "desc": "7-day streak", "req": current_streak >= 7, "rc": 250, "item": "Silver Chain ⛓️"},
    {"id": "month", "name": "Legendary Status", "desc": "30-day streak", "req": current_streak >= 30, "rc": 500, "item": "Platinum Plaque 💿"}
]

user_points = (len(valid_dates) * 10) + ((total_words // 10) * 5)
user_points += sum([a['rc'] for a in achievements if a['id'] in claimed])
user_points -= sum([shop_prices.get(p, 0) for p in purchases])

inventory = purchases + [a['item'] for a in achievements if a['id'] in claimed]

# --- 5. CLEAN REBUILD FUNCTION ---
def rebuild_and_save(new_entry_map, new_purchases, new_claims):
    # Meta data at top
    new_content = ""
    for p in sorted(list(set(new_purchases))): new_content += f"PURCHASE: {p}\n"
    for c in sorted(list(set(new_claims))): new_content += f"CLAIMED: {c}\n"
    
    # Sessions below
    for d in sorted(new_entry_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        new_content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{new_entry_map[d]}\n------------------------------"
    update_github_file(new_content)

# --- 6. UI ---
st.set_page_config(page_title="Studio Journal", layout="wide")
st.markdown("<style>.float { animation: floating 3s ease-in-out infinite; display: inline-block; } @keyframes floating { 0% {transform:translateY(0px);} 50% {transform:translateY(-10px);} 100% {transform:translateY(0px);} }</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"{current_streak} Days")
    st.divider()
    show_items = {item: st.checkbox(f"Show {item}", value=True) for item in inventory}
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# Mannequin Visual
v1, v2, v3, v4, v5 = st.columns(5)
with v3:
    cap = "🧢" if show_items.get("Rookie Cap 🧢") else ""
    st.markdown(f'<div style="background: rgba(255,255,255,0.05); border-radius: 15px; padding: 20px; text-align: center; position: relative;"><div style="font-size: 80px;">👤</div><div class="float" style="position: absolute; top: 10px; left: 0; right: 0; font-size: 40px;">{cap}</div></div>', unsafe_allow_html=True)

# TABS
t1, t2, t3, t4 = st.tabs(["✍️ New Session", "📂 The Vault", "🏪 Shop", "🏆 Career"])

with t1:
    target_date = st.date_input("Session Date", value=be_now.date(), min_value=START_DATE)
    d_str = target_date.strftime('%d/%m/%Y')
    if d_str in entry_map:
        st.info("Already recorded. Go to Vault to edit.")
    else:
        new_lyr = st.text_area("Drop bars...", height=250)
        if st.button("🚀 Record Session"):
            entry_map[d_str] = new_lyr
            rebuild_and_save(entry_map, purchases, claimed)
            st.rerun()

with t2:
    st.header("The Vault")
    delta = (be_now.date() - START_DATE).days
    for i in range(delta + 1):
        day = (be_now.date() - timedelta(days=i)).strftime('%d/%m/%Y')
        with st.expander(f"{'✅' if day in entry_map else '⚪'} {day}"):
            if day in entry_map:
                edited = st.text_area("Edit", value=entry_map[day], height=200, key=f"v_{day}")
                if st.button("💾 Save", key=f"b_{day}"):
                    entry_map[day] = edited
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()
            else: st.write("Empty")

with t3:
    st.header("Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_prices.items()):
        with cols[i%2]:
            if item in purchases: st.success(f"OWNED: {item}")
            elif st.button(f"Buy {item} ({price}RC)"):
                if user_points >= price:
                    purchases.append(item)
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()

with t4:
    st.header("🏆 Career Achievements")
    for a in achievements:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.write(f"**{a['name']}**")
            st.caption(f"{a['desc']} | Reward: {a['rc']} RC + {a['item']}")
        with c2:
            if a['id'] in claimed: st.success("Completed")
            elif a['req']:
                if st.button("Claim", key=f"claim_{a['id']}"):
                    claimed.append(a['id'])
                    rebuild_and_save(entry_map, purchases, claimed)
                    st.rerun()
            else: st.write("🔒 Locked")
