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
entries_raw = [b for b in all_blocks if "DATE:" in b and "LYRICS:" in b]
purchases = [p.strip() for p in re.findall(r'PURCHASE: (.*)', full_text)]
claimed = [c.strip() for c in re.findall(r'CLAIMED: (.*)', full_text)]

entry_map = {re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e).group(1): e for e in entries_raw if re.search(r'DATE: (\d{2}/\d{2}/\d{4})', e)}
unique_dates = sorted([datetime.strptime(d, '%d/%m/%Y').date() for d in entry_map.keys() if datetime.strptime(d, '%d/%m/%Y').date() <= today_date], reverse=True)

# STREAK CALCULATION
current_streak = 0
if unique_dates:
    if (today_date - unique_dates[0]).days <= 1:
        current_streak = 1
        for i in range(len(unique_dates)-1):
            if (unique_dates[i] - unique_dates[i+1]).days == 1: current_streak += 1
            else: break

# --- DEFINITIONS: SHOP VS GOALS ---
shop_items = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 300, "Neon Sign 🏮": 400, "Subwoofer 🔊": 800, "Golden Mic 🎤": 1000}

achievements = [
    {
        "id": "first", "name": "Rookie of the Year", "how": "Submit your very first entry in the journal.",
        "req": len(unique_dates) >= 1, "reward_text": "50 RC + Rookie Cap 🧢", "rc": 50, "item": "Rookie Cap 🧢"
    },
    {
        "id": "week", "name": "Weekly Grind", "how": "Reach a 7-day writing streak (no days missed).",
        "req": current_streak >= 7, "reward_text": "250 RC + Silver Chain ⛓️", "rc": 250, "item": "Silver Chain ⛓️"
    },
    {
        "id": "month", "name": "Legendary Status", "how": "Reach a 30-day writing streak.",
        "req": current_streak >= 30, "reward_text": "Platinum Plaque 💿", "rc": 0, "item": "Platinum Plaque 💿"
    }
]

inventory = purchases + [a['item'] for a in achievements if a['id'] in claimed and 'item' in a]
bonus_points = sum([a['rc'] for a in achievements if a['id'] in claimed])
spent_points = sum([shop_items.get(p, 0) for p in purchases])
user_points = (len(unique_dates) * 10) + bonus_points - spent_points

# --- 4. UI ---
st.set_page_config(page_title="Studio Journal", page_icon="🎤")

# COSMETIC DISPLAY LOGIC (This makes it "Actual")
with st.sidebar:
    # 1. THE CAP: Displayed on your "Profile"
    profile_emoji = "👤"
    if "Rookie Cap 🧢" in inventory: profile_emoji = "🧢"
    if "Silver Chain ⛓️" in inventory: profile_emoji = "💎"
    
    st.title(f"{profile_emoji} Studio Dashboard")
    st.metric("Wallet", f"{user_points} RC")
    st.metric("Streak", f"🔥 {current_streak} Days")
    
    # 2. THE CAT: Appears as a pet in the sidebar if owned
    if "Studio Cat 🐈" in inventory:
        st.divider()
        st.write("🐾 **Your Studio Pet:**")
        st.write("🐈 *Purring on the mixing desk...*")
    
    st.divider()
    st.link_button("🔙 Main App", MAIN_APP_URL, use_container_width=True)

# 3. STUDIO DECORATIONS (Main Screen)
if "Neon Sign 🏮" in inventory:
    st.markdown("---")
    st.markdown("<h3 style='text-align: center; color: pink;'>✨ STUDIO OPEN ✨</h3>", unsafe_content_code=True)

t1, t2, t3, t4 = st.tabs(["🎤 Write", "📜 Vault", "🛒 Shop", "🏆 Goals"])

# (Tab 1, 2, 3 logic remain the same for stability)
with t1:
    st.header("Daily Session")
    if today_str in entry_map: st.success(f"✅ Secure in the vault.")
    else:
        lyrics = st.text_area("Drop your bars:", height=250)
        if st.button("🚀 Submit"):
            update_github_file(f"DATE: {today_str}\nLYRICS:\n{lyrics}\n" + "-"*30 + "\n" + full_text)
            st.rerun()

with t2:
    st.header("Records")
    for i in range(7):
        target_str = (today_date - timedelta(days=i)).strftime('%d/%m/%Y')
        if target_str in entry_map:
            with st.expander(f"📅 {target_str}"):
                st.text(entry_map[target_str])
        else:
            with st.expander(f"❌ {target_str} (Missing)"):
                st.write("Day missed.")

with t3:
    st.header("The Shop")
    cols = st.columns(2)
    for i, (item, price) in enumerate(shop_items.items()):
        with cols[i % 2]:
            if item in purchases: st.write(f"✅ {item} Owned")
            else:
                if st.button(f"Buy {item} ({price} RC)"):
                    if user_points >= price:
                        update_github_file(f"PURCHASE: {item}\n" + full_text)
                        st.rerun()

# --- IMPROVED GOALS TAB (Tells you exactly what to do) ---
with t4:
    st.header("🏆 Career Milestones")
    st.write("Earn items that prove your dedication.")
    
    for a in achievements:
        with st.container():
            c1, c2 = st.columns([3, 1])
            with c1:
                st.subheader(a['name'])
                st.write(f"🎯 **Goal:** {a['how']}")
                st.caption(f"Reward: {a['reward_text']}")
            with c2:
                if a['id'] in claimed:
                    st.success("EARNED")
                elif a['req']:
                    if st.button("CLAIM", key=f"cl_{a['id']}"):
                        update_github_file(f"CLAIMED: {a['id']}\n" + full_text)
                        st.rerun()
                else:
                    st.button("LOCKED", disabled=True, key=f"lk_{a['id']}")
            st.divider()
