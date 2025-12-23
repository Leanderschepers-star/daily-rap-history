import streamlit as st
import datetime, requests, base64, pytz, re, random
from datetime import datetime, timedelta

# --- 1. CONFIG & ENGINES ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("GitHub Token missing.")
    st.stop()

REPO_NAME = "leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"
be_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(be_tz)
today_str = be_now.strftime('%d/%m/%Y')

def get_github_file(repo, path):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(content, msg="Update Studio Data"):
    file_data = get_github_file(REPO_NAME, HISTORY_PATH)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{HISTORY_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

# --- 2. DATA PARSING ---
hist_json = get_github_file(REPO_NAME, HISTORY_PATH)
full_text = base64.b64decode(hist_json['content']).decode('utf-8') if hist_json else ""

purchases = list(set(re.findall(r'PURCHASE: (.*)', full_text)))
claimed = list(set(re.findall(r'CLAIMED: (.*)', full_text)))
tasks_done = list(set(re.findall(r'TASK_DONE: (.*)', full_text)))
active_theme = re.search(r'ACTIVE_THEME: (.*)', full_text).group(1) if "ACTIVE_THEME:" in full_text else "Default Dark"

entry_map = {}
blocks = re.split(r'-{10,}', full_text)
for b in blocks:
    if "DATE:" in b:
        date_match = re.search(r'DATE:\s*(\d{2}/\d{2}/\d{4})', b)
        if date_match:
            d_str = date_match.group(1)
            lyr_match = re.search(r'LYRICS:\s*(.*?)(?=\s*---|$)', b, re.DOTALL)
            lyr_content = lyr_match.group(1).strip() if lyr_match else ""
            if lyr_content: # ONLY add to map if there is actual content
                entry_map[d_str] = lyr_content

# --- 3. REBALANCED ECONOMY ---
total_words = sum([len(lyr.split()) for lyr in entry_map.values()])
today_word_count = len(entry_map.get(today_str, "").split())
word_points = total_words // 2
session_points = len(entry_map) * 10
chest_points = len([x for x in tasks_done if "COMPLETION" in x]) * 200

# Calculate final wallet
shop_prices = {"Coffee Machine ☕": 150, "Studio Cat 🐈": 400, "Neon 'VIBE' Sign 🏮": 800, "Bass Subwoofer 🔊": 1500, "Smoke Machine 💨": 2500, "Golden Mic 🎤": 5000}
user_points = word_points + session_points + chest_points
user_points -= sum([shop_prices.get(p, 0) for p in purchases])

# --- 4. DYNAMIC QUESTS ---
random.seed(today_str)
quest_pool = [
    {"id": "q_rec", "desc": "Record today's session", "req": today_str in entry_map, "rc": 50},
    {"id": "q_words", "desc": "Write 100+ words today", "req": today_word_count >= 100, "rc": 100},
    {"id": "q_vault", "desc": "Review the Vault", "req": "vault_seen" in st.session_state, "rc": 30},
    {"id": "q_shop", "desc": "Browse Studio Shop", "req": "shop_seen" in st.session_state, "rc": 20}
]
daily_tasks = random.sample(quest_pool, 3)

def save_all(theme_to_save=None):
    t = theme_to_save if theme_to_save else active_theme
    content = f"ACTIVE_THEME: {t}\n"
    for p in sorted(purchases): content += f"PURCHASE: {p}\n"
    for c in sorted(claimed): content += f"CLAIMED: {c}\n"
    for t_done in sorted(tasks_done): content += f"TASK_DONE: {t_done}\n"
    # Sort dates to keep history clean
    for d in sorted(entry_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True):
        content += f"\n------------------------------\nDATE: {d}\nLYRICS:\n{entry_map[d]}\n------------------------------"
    update_github_file(content)

# --- 5. UI STYLING & THEMES ---
st.set_page_config(page_title="Leander Studio", layout="wide")
themes = {
    "Default Dark": "background: #0f0f0f;",
    "Underground UI 🧱": "background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url('https://www.transparenttextures.com/patterns/brick-wall.png'); background-color: #1a1a1a;",
    "Classic Studio 🎙️": "background: #1e272e;",
    "Blue Booth UI 🟦": "background: radial-gradient(circle, #001a33 0%, #0f0f0f 100%);"
}

st.markdown(f"""
<style>
    .stApp {{ {themes.get(active_theme, themes['Default Dark'])} color: white; }}
    .stats-card {{ background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); text-align: center; }}
    .quest-item {{ padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 5px solid #444; background: rgba(255,255,255,0.02); }}
    .ready {{ border-left-color: #ffaa00; background: rgba(255, 170, 0, 0.1); }}
    .done {{ border-left-color: #00ff88; background: rgba(0, 255, 136, 0.1); color: #00ff88; }}
</style>
""", unsafe_allow_html=True)

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🕹️ Studio Control")
    st.metric("Wallet Balance", f"{user_points} RC")
    
    st.divider()
    # Theme Selector (Only shows unlocked ones)
    unlocked_themes = ["Default Dark"]
    if "day1" in claimed: unlocked_themes.append("Underground UI 🧱")
    if "words_500" in claimed: unlocked_themes.append("Classic Studio 🎙️")
    if "week" in claimed: unlocked_themes.append("Blue Booth UI 🟦")
    
    selected_theme = st.selectbox("Switch Theme", unlocked_themes, index=unlocked_themes.index(active_theme) if active_theme in unlocked_themes else 0)
    if selected_theme != active_theme:
        save_all(theme_to_save=selected_theme)
        st.rerun()

    st.divider()
    st.subheader("📋 Daily Quests")
    tasks_claimed_today = [t for t in daily_tasks if f"{today_str}_{t['id']}" in tasks_done]
    for t in daily_tasks:
        t_key = f"{today_str}_{t['id']}"
        if t_key in tasks_done:
            st.markdown(f"<div class='quest-item done'>✅ {t['desc']}</div>", unsafe_allow_html=True)
        elif t['req']:
            st.markdown(f"<div class='quest-item ready'>⭐ {t['desc']}</div>", unsafe_allow_html=True)
            if st.button(f"Claim {t['rc']} RC", key=f"btn_{t['id']}"):
                tasks_done.append(t_key)
                save_all()
                st.rerun()
        else:
            st.markdown(f"<div class='quest-item'>⚪ {t['desc']}</div>", unsafe_allow_html=True)
    
    if len(tasks_claimed_today) == 3 and f"{today_str}_COMPLETION" not in tasks_done:
        if st.button("🎁 CLAIM DAILY CHEST (+200 RC)", use_container_width=True, type="primary"):
            tasks_done.append(f"{today_str}_COMPLETION")
            save_all()
            st.rerun()

# --- 7. TABS ---
st.markdown("<h1 style='text-align:center;'>LEANDER STUDIO</h1>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: st.markdown(f'<div class="stats-card"><h3>Streak</h3><h2>{len(entry_map)} Days</h2></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stats-card"><h3>Words Today</h3><h2>{today_word_count}</h2></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stats-card"><h3>Rank</h3><h2>Lv.{len(claimed)+1}</h2></div>', unsafe_allow_html=True)

t_rec, t_vau, t_shop, t_car = st.tabs(["✍️ Record", "📂 Vault", "🏪 Shop", "🏆 Career"])

with t_rec:
    with st.form("booth"):
        d_input = st.date_input("Date", value=be_now.date())
        d_key = d_input.strftime('%d/%m/%Y')
        lyrics = st.text_area("Drop your bars...", value=entry_map.get(d_key, ""), height=300)
        if st.form_submit_button("🚀 SAVE TO VAULT"):
            if lyrics.strip():
                entry_map[d_key] = lyrics
                save_all()
                st.rerun()
            else:
                st.warning("Write something before saving!")

with t_vau:
    st.session_state["vault_seen"] = True
    st.subheader("Your Catalog")
    # ONLY show days that actually have lyrics
    vault_dates = sorted(entry_map.keys(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'), reverse=True)
    if not vault_dates:
        st.info("The vault is empty. Record your first session!")
    else:
        for d in vault_dates:
            with st.expander(f"📅 {d} - ({len(entry_map[d].split())} words)"):
                st.text(entry_map[d])

with t_shop:
    st.session_state["shop_seen"] = True
    st.header("Studio Shop")
    sc1, sc2 = st.columns(2)
    for i, (item, price) in enumerate(shop_prices.items()):
        with (sc1 if i%2==0 else sc2):
            if item in purchases: st.success(f"OWNED: {item}")
            else:
                if st.button(f"Buy {item} ({price} RC)", key=f"shop_{i}"):
                    if user_points >= price:
                        purchases.append(item)
                        save_all()
                        st.rerun()
                    else: st.error("Not enough RC!")

with t_car:
    st.header("Career Milestones")
    achievements = [
        {"id": "day1", "name": "First Day", "target": 1, "curr": len(entry_map), "reward": "Underground UI 🧱"},
        {"id": "words_500", "name": "Wordsmith", "target": 500, "curr": total_words, "reward": "Classic Studio 🎙️"},
        {"id": "week", "name": "Rising Star", "target": 7, "curr": len(entry_map), "reward": "Blue Booth UI 🟦"}
    ]
    for a in achievements:
        prog = min(a['curr'] / a['target'], 1.0)
        st.subheader(a['name'])
        st.write(f"Reward: {a['reward']}")
        st.progress(prog)
        if a['id'] in claimed: st.success("Unlocked & Claimed")
        elif prog >= 1.0:
            if st.button(f"Claim {a['name']}", key=f"clm_{a['id']}"):
                claimed.append(a['id'])
                save_all()
                st.rerun()
        else: st.button("Locked", disabled=True, key=f"lck_{a['id']}")
        st.divider()
