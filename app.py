import streamlit as st
import datetime
import requests
import base64
import pytz
import re
from datetime import datetime, timedelta

# --- 1. CONFIG & SETUP ---
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
APP_1_REPO = "Leanderschepers-star/daily-rap-app" 
APP_1_FILE = "streamlit_app.py" 
REPO_NAME = "Leanderschepers-star/daily-rap-history"
HISTORY_PATH = "history.txt"

belgium_tz = pytz.timezone('Europe/Brussels')
be_now = datetime.now(belgium_tz)
day_of_year = be_now.timetuple().tm_yday

# --- 2. GITHUB & SYNC FUNCTIONS ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else None

def update_github_file(path, content, msg="Update"):
    file_data = get_github_file(path)
    sha = file_data['sha'] if file_data else None
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": msg, "content": encoded, "sha": sha} if sha else {"message": msg, "content": encoded}
    return requests.put(url, json=data, headers=headers)

def get_synced_data():
    url = f"https://api.github.com/repos/{APP_1_REPO}/contents/{APP_1_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = base64.b64decode(r.json()['content']).decode('utf-8')
        w_match = re.search(r"words\s*=\s*(\[.*?\])", content, re.DOTALL)
        s_match = re.search(r"sentences\s*=\s*(\[.*?\])", content, re.DOTALL)
        try:
            import ast # Safer way to convert string to list
            w_list = ast.literal_eval(w_match.group(1)) if w_match else []
            s_list = ast.literal_eval(s_match.group(1)) if s_match else []
            return w_list, s_list
        except: return [], []
    return [], []

# --- 3. LOGIC: POINTS, STREAKS, & PURCHASES ---
def calculate_stats(content):
    if not content: return 0, 0, []
    
    # Streak Logic
    found_dates = set(re.findall(r'DATE: (\d{2}/\d{2}/\d{4})', content))
    date_objs = {datetime.strptime(d, '%d/%m/%Y').date() for d in found_dates}
    today = be_now.date()
    yesterday = today - timedelta(days=1)
    
    streak = 0
    if today in date_objs or yesterday in date_objs:
        curr = today if today in date_objs else yesterday
        while curr in date_objs:
            streak += 1
            curr -= timedelta(days=1)
            
    # Points Logic (Earnings)
    entry_points = content.count("DATE:") * 10
    just_lyrics = re.sub(r'(DATE|WORD|LYRICS|PURCHASE):.*', '', content)
    word_bonus = (len(just_lyrics.split()) // 10) * 2
    streak_bonus = (streak * 5) + (100 if streak >= 7 else 0) + (1000 if streak >= 30 else 0)
    total_earned = entry_points + word_bonus + streak_bonus
    
    # Spending Logic (Deductions)
    purchases = re.findall(r'PURCHASE: (.*)', content)
    prices = {"Studio Cat": 300, "Neon Layout": 150, "Gold Studio": 1000}
    total_spent = sum(prices.get(item, 0) for item in purchases)
    
    return total_earned - total_spent, streak, purchases

# --- 4. NOTIFICATION LOGIC ---
def send_notification(streak, history_text):
    today_str = be_now.strftime('%d/%m/%Y')
    if f"NOTIFIED: {today_str}" not in history_text:
        topic = "rappers_journal_123" 
        url = f"https://ntfy.sh/{topic}"
        msg = f"🔥 Your streak is at {streak} days! Time to write."
        headers = {
            "Title": "🎤 Rap Journal",
            "Click": "https://share.streamlit.io/leanderschepers-star/daily-rap-history/main/app.py",
            "Priority": "high"
        }
        try:
            requests.post(url, data=msg, headers=headers)
            return True
        except: return False
    return False

# --- 4. DATA BANK (ADD YOUR FULL LISTS HERE) ---
if not synced_words:
    words = [
    {"word": "Obsession", "rhymes": "Possession, Progression, Lesson"}, {"word": "Titanium", "rhymes": "Cranium, Uranium, Stadium"},
    {"word": "Mirage", "rhymes": "Garage, Collage, Sabotage"}, {"word": "Renaissance", "rhymes": "Response, Sconce, Nonce"},
    {"word": "Velocity", "rhymes": "Ferocity, Atrocity, Reciprocity"}, {"word": "Atmosphere", "rhymes": "Last year, Frontier, Revere"},
    {"word": "Sanctuary", "rhymes": "January, Cemetery, Visionary"}, {"word": "Calamity", "rhymes": "Humanity, Vanity, Insanity"},
    {"word": "Labyrinth", "rhymes": "Absinthe, Hyacinth, Platinum"}, {"word": "Paradox", "rhymes": "Narrative, Scare of, Pair of"},
    {"word": "Metaphor", "rhymes": "Step war, Better for, Get more"}, {"word": "Frequency", "rhymes": "Recently, Decently, Sequencing"},
    {"word": "Dynasty", "rhymes": "Majesty, Strategy, Tragedy"}, {"word": "Anarchy", "rhymes": "Hierarchy, Panarchy, Monarchally"},
    {"word": "Prophecy", "rhymes": "Policy, Quality, Honestly"}, {"word": "Eclipse", "rhymes": "Scripts, Lips, Chips"},
    {"word": "Blueprint", "rhymes": "Footprint, New hint, True tint"}, {"word": "Havoc", "rhymes": "Savage, Average, Baggage"},
    {"word": "Revenge", "rhymes": "Stonehenge, Unbend, Depend"}, {"word": "Infamous", "rhymes": "Ignorance, Synchronous, Instances"},
    {"word": "Pressure", "rhymes": "Fresher, Treasure, Measure"}, {"word": "Legacy", "rhymes": "Ecstasy, Jealousy, Embassy"},
    {"word": "Concrete", "rhymes": "On beat, Street, Elite"}, {"word": "Sovereign", "rhymes": "Governing, Hovering, Discovering"},
    {"word": "Vandalize", "rhymes": "Scandalize, Analyze, Standardize"}, {"word": "Miracle", "rhymes": "Lyrical, Empirical, Spherical"},
    {"word": "Paranoia", "rhymes": "Destroy ya, Lawyer, Employer"}, {"word": "Vibration", "rhymes": "Location, Nation, Patient"},
    {"word": "Adrenaline", "rhymes": "Medicine, Genuine, Better than"}, {"word": "Ambition", "rhymes": "Ignition, Partition, Competition"},
    {"word": "Anatomy", "rhymes": "Academy, Strategy, Mastery"}, {"word": "Catastrophe", "rhymes": "Philosophy, Atrophy, Apostrophe"},
    {"word": "Chameleon", "rhymes": "Million, Civilian, Pavilion"}, {"word": "Criminal", "rhymes": "Subliminal, Minimal, Original"},
    {"word": "Alchemy", "rhymes": "Strategy, Majesty, Anatomy"}, {"word": "Midnight", "rhymes": "Big fight, Street light, Sit tight"},
    {"word": "Outcast", "rhymes": "Doubt fast, Mouth past, South blast"}, {"word": "Victory", "rhymes": "History, Mystery, Slippery"},
    {"word": "Apocalypse", "rhymes": "Eclipse, Scripts, Lips"}, {"word": "Architect", "rhymes": "Respect, Collect, Direct"},
    {"word": "Aspiration", "rhymes": "Elevation, Generation, Nation"}, {"word": "Authentic", "rhymes": "Septic, Relentless, Eccentric"},
    {"word": "Backlash", "rhymes": "Flash, Cash, Smash"}, {"word": "Banish", "rhymes": "Vanish, Spanish, Famish"},
    {"word": "Barricade", "rhymes": "Escalade, Parade, Blade"}, {"word": "Battlefield", "rhymes": "Shield, Sealed, Yield"},
    {"word": "Betrayal", "rhymes": "Portrayal, Denial, Trial"}, {"word": "Blackout", "rhymes": "Track out, Back out, Pack out"},
    {"word": "Blasphemy", "rhymes": "Strategy, Majesty, Anatomy"}, {"word": "Bloodline", "rhymes": "Sunshine, Frontline, Design"},
    {"word": "Boundary", "rhymes": "Foundry, Soundly, Surround me"}, {"word": "Brutality", "rhymes": "Fatality, Reality, Mentality"},
    {"word": "Burnout", "rhymes": "Turn out, Learn out, Earn out"}, {"word": "Cadence", "rhymes": "Patience, Radiance, Silence"},
    {"word": "Captivate", "rhymes": "Activate, Graduate, Fascinate"}, {"word": "Carnage", "rhymes": "Garbage, Harness, Large age"},
    {"word": "Catalyst", "rhymes": "Analyst, Strategist, Bat a fist"}, {"word": "Censorship", "rhymes": "Mentorship, Friendship, Pen ship"},
    {"word": "Champion", "rhymes": "Grammy on, Pantheon, Carry on"}, {"word": "Chaos", "rhymes": "Play us, Slay us, Pay us"},
    {"word": "Charisma", "rhymes": "Prisma, Enigma, Stigma"}, {"word": "Chronicle", "rhymes": "Iconical, Ironical, Phenomenal"},
    {"word": "Cipher", "rhymes": "Lifer, Hyper, Sniper"}, {"word": "Circumstance", "rhymes": "Work advance, Birth of chance"},
    {"word": "Clarity", "rhymes": "Charity, Rarity, Solidarity"}, {"word": "Classic", "rhymes": "Jurassic, Drastic, Plastic"},
    {"word": "Collision", "rhymes": "Precision, Division, Decision"}, {"word": "Colossal", "rhymes": "Apostle, Fossil, Hostile"},
    {"word": "Commander", "rhymes": "Slander, Meander, Candid"}, {"word": "Complexity", "rhymes": "Reflexity, Perplexity, Hex on me"},
    {"word": "Conscience", "rhymes": "Nonsense, Response, Scents"}, {"word": "Conspiracy", "rhymes": "Lyricist, Theory, Wearily"},
    {"word": "Contradict", "rhymes": "Addict, Predict, Verdict"}, {"word": "Corridor", "rhymes": "War door, More for, Floor board"},
    {"word": "Corruption", "rhymes": "Eruption, Interruption, Destruction"}, {"word": "Counterfeit", "rhymes": "Proud of it, Loud with it, Out for it"},
    {"word": "Covenant", "rhymes": "Government, Loving it, Shoving it"}, {"word": "Crucial", "rhymes": "Unusual, Refusal, Perusal"},
    {"word": "Curfew", "rhymes": "Virtue, Hurt you, Search through"}, {"word": "Cynical", "rhymes": "Pinnacle, Clinical, Original"},
    {"word": "Darkness", "rhymes": "Heartless, Sharpness, Regardless"}, {"word": "Deadline", "rhymes": "Headline, Redline, Bedtime"},
    {"word": "Decade", "rhymes": "Paid, Made, Slayed"}, {"word": "Deception", "rhymes": "Perception, Reception, Exception"},
    {"word": "Defiance", "rhymes": "Alliance, Reliance, Science"}, {"word": "Delirium", "rhymes": "Experience, Period, Serious"},
    {"word": "Democracy", "rhymes": "Policy, Quality, Hypocrisy"}, {"word": "Departure", "rhymes": "Archer, Harder, Martyr"},
    {"word": "Desolation", "rhymes": "Isolation, Creation, Nation"}, {"word": "Destiny", "rhymes": "Testing me, Question me, Messily"},
    {"word": "Devastate", "rhymes": "Elevate, Speculate, Separate"}, {"word": "Diagnosis", "rhymes": "Hypnosis, Neurosis, Dosages"},
    {"word": "Dictator", "rhymes": "Hater, Later, Creator"}, {"word": "Dignity", "rhymes": "Infinity, Trinity, Vicinity"},
    {"word": "Dimension", "rhymes": "Mention, Tension, Attention"}, {"word": "Disaster", "rhymes": "Master, Faster, Pastor"},
    {"word": "Discovery", "rhymes": "Recovery, Hovering, Brotherly"}, {"word": "Disguise", "rhymes": "Lies, Eyes, Rise"},
    {"word": "Distance", "rhymes": "Instance, Resistance, Assistance"}, {"word": "Distortion", "rhymes": "Portion, Caution, Abortion"},
    {"word": "Dominance", "rhymes": "Prominence, Tolerance, Confidence"}, {"word": "Dormant", "rhymes": "Torment, Format, Warrant"},
    {"word": "Doubt", "rhymes": "Out, Shout, Route"}, {"word": "Drama", "rhymes": "Mama, Trauma, Karma"},
    {"word": "Drastic", "rhymes": "Fantastic, Elastic, Plastic"}, {"word": "Dreamer", "rhymes": "Schemer, Steamer, Redeemer"},
    {"word": "Duality", "rhymes": "Reality, Mentality, Fatality"}, {"word": "Durability", "rhymes": "Capability, Agility, Utility"},
    {"word": "Dynamic", "rhymes": "Panic, Titanic, Organic"}, {"word": "Echo", "rhymes": "Let go, Ghetto, Metro"},
    {"word": "Economy", "rhymes": "Autonomy, Anatomy, Policy"}, {"word": "Ego", "rhymes": "We go, See through, Regal"},
    {"word": "Elastic", "rhymes": "Plastic, Drastic, Fantastic"}, {"word": "Electric", "rhymes": "Hectic, Eccentric, Kinetic"},
    {"word": "Elegance", "rhymes": "Intelligence, Relevance, Evidence"}, {"word": "Element", "rhymes": "Relevant, Settlement, Elegant"},
    {"word": "Elevate", "rhymes": "Activate, Captivate, Separate"}, {"word": "Elite", "rhymes": "Street, Complete, Concrete"},
    {"word": "Eloquent", "rhymes": "Moment, Component, Opponent"}, {"word": "Embrace", "rhymes": "Chase, Race, Space"},
    {"word": "Emerge", "rhymes": "Urge, Verge, Surge"}, {"word": "Emotion", "rhymes": "Motion, Devotion, Ocean"},
    {"word": "Empire", "rhymes": "Fire, Higher, Wire"}, {"word": "Empty", "rhymes": "Plenty, Twenty, Entry"},
    {"word": "Endurance", "rhymes": "Assurance, Insurance, Occurrence"}, {"word": "Energy", "rhymes": "Memory, Enemy, Remedy"},
    {"word": "Enigma", "rhymes": "Stigma, Prisma, Charisma"}, {"word": "Enterprise", "rhymes": "Rise, Lies, Prize"},
    {"word": "Entrance", "rhymes": "Dance, Chance, Glance"}, {"word": "Entropy", "rhymes": "Atrophy, Modesty, Honesty"},
    {"word": "Envy", "rhymes": "Any, Many, Penny"}, {"word": "Epic", "rhymes": "Relic, Metric, Hectic"},
    {"word": "Epidemic", "rhymes": "Systemic, Academic, Pandemic"}, {"word": "Equation", "rhymes": "Nation, Foundation, Creation"},
    {"word": "Eradicate", "rhymes": "Advocate, Graduate, Separate"}, {"word": "Erosion", "rhymes": "Explosion, Corrosion, Motion"},
    {"word": "Erratic", "rhymes": "Static, Automatic, Dramatic"}, {"word": "Escape", "rhymes": "Shape, Tape, Cape"},
    {"word": "Essence", "rhymes": "Presence, Lessons, Questions"}, {"word": "Eternal", "rhymes": "Internal, Journal, Infernal"},
    {"word": "Ethical", "rhymes": "Skeptical, Medical, Identical"}, {"word": "Euphoria", "rhymes": "Victoria, Gloria, Story of"},
    {"word": "Evidence", "rhymes": "Confidence, Relevance, Residence"}, {"word": "Evolution", "rhymes": "Revolution, Solution, Pollution"},
    {"word": "Exaggerate", "rhymes": "Calculate, Separate, Graduate"}, {"word": "Excellence", "rhymes": "Elegance, Evidence, Relevance"},
    {"word": "Exception", "rhymes": "Reception, Deception, Perception"}, {"word": "Exchange", "rhymes": "Strange, Range, Change"},
    {"word": "Execute", "rhymes": "Substitute, Absolute, Institute"}, {"word": "Exhaust", "rhymes": "Lost, Cost, Frost"},
    {"word": "Exile", "rhymes": "Style, Mile, While"}, {"word": "Existence", "rhymes": "Resistance, Assistance, Persistence"},
    {"word": "Exodus", "rhymes": "Focus, Lotus, Notice"}, {"word": "Exotic", "rhymes": "Hypnotic, Chaotic, Narcotic"},
    {"word": "Expansion", "rhymes": "Mansion, Action, Passion"}, {"word": "Experience", "rhymes": "Serious, Period, Delirium"},
    {"word": "Experiment", "rhymes": "Sentiment, Element, Settlement"}, {"word": "Expert", "rhymes": "Dirt, Shirt, Hurt"},
    {"word": "Explosion", "rhymes": "Motion, Ocean, Devotion"}, {"word": "Exposure", "rhymes": "Closure, Composure, Over"},
    {"word": "Expression", "rhymes": "Session, Lesson, Question"}, {"word": "Exquisite", "rhymes": "Visit, Business, Witness"},
    {"word": "Extinct", "rhymes": "Distinct, Linked, Sinked"}, {"word": "Extreme", "rhymes": "Dream, Team, Scheme"},
    {"word": "Fabric", "rhymes": "Static, Magic, Classic"}, {"word": "Facade", "rhymes": "Parade, Blade, Shade"},
    {"word": "Facility", "rhymes": "Agility, Ability, Utility"}, {"word": "Factor", "rhymes": "Actor, Master, Raptor"},
    {"word": "Faith", "rhymes": "Wraith, Safe, Place"}, {"word": "Falsehood", "rhymes": "Brotherhood, Neighborhood, Good"},
    {"word": "Fame", "rhymes": "Game, Flame, Name"}, {"word": "Family", "rhymes": "Happily, Strategy, Tragedy"},
    {"word": "Famine", "rhymes": "Examine, Hammering, Damning"}, {"word": "Fanatic", "rhymes": "Dramatic, Static, Erratic"},
    {"word": "Fantasy", "rhymes": "Majesty, Strategy, Tragedy"}, {"word": "Fatality", "rhymes": "Reality, Mentality, Brutality"},
    {"word": "Fearless", "rhymes": "Peerless, Tearless, Hear this"}, {"word": "Feature", "rhymes": "Teacher, Creature, Preacher"},
    {"word": "Federal", "rhymes": "General, Several, Ephemeral"}, {"word": "Feedback", "rhymes": "Need that, Read that, Keep back"},
    {"word": "Felony", "rhymes": "Melody, Remedy, Jealousy"}, {"word": "Ferocious", "rhymes": "Atrocious, Precocity, Notions"},
    {"word": "Fiction", "rhymes": "Addition, Mission, Position"}, {"word": "Fidelity", "rhymes": "Ability, Utility, Facility"},
    {"word": "Fierce", "rhymes": "Pierce, Years, Tears"}, {"word": "Final", "rhymes": "Vinyl, Cycle, Spiral"},
    {"word": "Finance", "rhymes": "Balance, Silence, Guidance"}, {"word": "Firewall", "rhymes": "Higher, Liar, Desire"},
    {"word": "Fixation", "rhymes": "Station, Nation, Creation"}, {"word": "Flame", "rhymes": "Game, Fame, Name"},
    {"word": "Flavor", "rhymes": "Savor, Favor, Behavior"}, {"word": "Flexibility", "rhymes": "Possibility, Ability, Utility"},
    {"word": "Focus", "rhymes": "Notice, Lotus, Bogus"}, {"word": "Force", "rhymes": "Source, Course, Horse"},
    {"word": "Forecast", "rhymes": "Past, Fast, Last"}, {"word": "Forever", "rhymes": "Never, Clever, Together"},
    {"word": "Forgive", "rhymes": "Live, Give, Sieve"}, {"word": "Formula", "rhymes": "Regular, Popular, Modular"},
    {"word": "Fortune", "rhymes": "Soon, Moon, June"}, {"word": "Foundation", "rhymes": "Nation, Creation, Location"},
    {"word": "Fragile", "rhymes": "Agile, Castle, Hassel"}, {"word": "Fragment", "rhymes": "Sentiment, Element, Settlement"},
    {"word": "Franchise", "rhymes": "Rise, Prize, Surprise"}, {"word": "Freedom", "rhymes": "Kingdom, Reason, Season"},
    {"word": "Frenzy", "rhymes": "Any, Many, Penny"}, {"word": "Friction", "rhymes": "Fiction, Addition, Mission"},
    {"word": "Frontier", "rhymes": "Year, Clear, Fear"}, {"word": "Furious", "rhymes": "Serious, Curious, Mysterious"},
    {"word": "Future", "rhymes": "Teacher, Feature, Preacher"}, {"word": "Gallery", "rhymes": "Salary, Battery, Strategy"},
    {"word": "Gamble", "rhymes": "Sample, Example, Trample"}, {"word": "Garbage", "rhymes": "Harness, Carnage, Damage"},
    {"word": "Gateway", "rhymes": "Always, Stay, Play"}, {"word": "Gather", "rhymes": "Rather, Father, Weather"},
    {"word": "General", "rhymes": "Federal, Several, Ephemeral"}, {"word": "Generation", "rhymes": "Nation, Creation, Location"},
    {"word": "Genius", "rhymes": "Serious, Fearless, Peerless"}, {"word": "Geometry", "rhymes": "Policy, Quality, Anatomy"},
    {"word": "Gesture", "rhymes": "Pressure, Treasure, Measure"}, {"word": "Ghetto", "rhymes": "Techno, Metro, Let go"},
    {"word": "Ghost", "rhymes": "Most, Coast, Post"}, {"word": "Giant", "rhymes": "Compliant, Reliant, Defiant"},
    {"word": "Gifted", "rhymes": "Lifted, Shifted, Drifted"}, {"word": "Gladiator", "rhymes": "Hater, Later, Gator"},
    {"word": "Glamour", "rhymes": "Hammer, Grammar, Stammer"}, {"word": "Global", "rhymes": "Noble, Total, Local"},
    {"word": "Glory", "rhymes": "Story, Territory, Victory"}, {"word": "Glow", "rhymes": "Show, Know, Flow"},
    {"word": "Goal", "rhymes": "Soul, Roll, Control"}, {"word": "Gold", "rhymes": "Sold, Told, Cold"},
    {"word": "Gossip", "rhymes": "Toxic, Logic, Profit"}, {"word": "Govern", "rhymes": "Southern, Modern, Pattern"},
    {"word": "Grace", "rhymes": "Face, Place, Space"}, {"word": "Graduate", "rhymes": "Eradicate, Separate, Advocate"},
    {"word": "Grammar", "rhymes": "Hammer, Glamour, Stammer"}, {"word": "Grandeur", "rhymes": "Measure, Treasure, Pleasure"},
    {"word": "Graphic", "rhymes": "Traffic, Static, Magic"}, {"word": "Gratitude", "rhymes": "Attitude, Magnitude, Latitude"},
    {"word": "Gravity", "rhymes": "Strategy, Tragedy, Anatomy"}, {"word": "Greatness", "rhymes": "Witness, Fitness, Sickness"},
    {"word": "Grit", "rhymes": "Hit, Sit, Bit"}, {"word": "Ground", "rhymes": "Sound, Found, Round"},
    {"word": "Growth", "rhymes": "Both, Oath, Cloth"}, {"word": "Guarantee", "rhymes": "Me, See, Free"},
    {"word": "Guard", "rhymes": "Hard, Yard, Card"}, {"word": "Guilt", "rhymes": "Built, Tilt, Spilt"},
    {"word": "Habit", "rhymes": "Rabbit, Grab it, Stab it"}, {"word": "Hallway", "rhymes": "Always, Stay, Play"},
    {"word": "Hammer", "rhymes": "Grammar, Stammer, Glamour"}, {"word": "Handle", "rhymes": "Candle, Scandal, Sample"},
    {"word": "Handsome", "rhymes": "Random, Ransom, Phantom"}, {"word": "Happen", "rhymes": "Rapping, Trapping, Clapping"},
    {"word": "Happiness", "rhymes": "Gladness, Sadness, Madness"}, {"word": "Harbor", "rhymes": "Harder, Farther, Martyr"},
    {"word": "Hardcore", "rhymes": "Floor, Door, War"}, {"word": "Harmony", "rhymes": "Melody, Remedy, Felony"},
    {"word": "Harvest", "rhymes": "Hardest, Smartest, Artist"}, {"word": "Hatred", "rhymes": "Sacred, Naked, Wasted"},
    {"word": "Haunted", "rhymes": "Wanted, Flaunted, Daunted"}, {"word": "Headline", "rhymes": "Deadline, Redline, Bedtime"},
    {"word": "Heartbeat", "rhymes": "Street, Complete, Concrete"}, {"word": "Heaven", "rhymes": "Seven, Eleven, Lesson"},
    {"word": "Heavy", "rhymes": "Ready, Steady, Levy"}, {"word": "Hectic", "rhymes": "Electric, Metric, Hectic"},
    {"word": "Height", "rhymes": "Light, Night, Fight"}, {"word": "Heirloom", "rhymes": "Room, Boom, Gloom"},
    {"word": "Hero", "rhymes": "Zero, Near go, Fear no"}, {"word": "Hesitate", "rhymes": "Devastate, Separate, Graduate"},
    {"word": "Hidden", "rhymes": "Forbidden, Ridden, Written"}, {"word": "Hierarchy", "rhymes": "Anarchy, Panarchy, Monarchally"},
    {"word": "Higher", "rhymes": "Fire, Wire, Desire"}, {"word": "Highway", "rhymes": "Always, Stay, Play"},
    {"word": "Hint", "rhymes": "Tint, Mint, Print"}, {"word": "History", "rhymes": "Victory, Mystery, Slippery"},
    {"word": "Hollow", "rhymes": "Follow, Swallow, Tomorrow"}, {"word": "Honesty", "rhymes": "Modesty, Policy, Strategy"},
    {"word": "Honor", "rhymes": "Owner, Donor, Corner"}, {"word": "Hook", "rhymes": "Book, Look, Took"},
    {"word": "Hope", "rhymes": "Dope, Rope, Scope"}, {"word": "Horizon", "rhymes": "Rising, Sizing, Pricing"},
    {"word": "Horror", "rhymes": "Floor, Door, War"}, {"word": "Hospital", "rhymes": "Capital, Digital, Original"},
    {"word": "Hostage", "rhymes": "Stage, Cage, Page"}, {"word": "Hostile", "rhymes": "Style, Mile, While"},
    {"word": "Hot", "rhymes": "Not, Got, Lot"}, {"word": "House", "rhymes": "Mouse, Spouse, Blouse"},
    {"word": "Hover", "rhymes": "Cover, Brother, Mother"}, {"word": "Huge", "rhymes": "Refuge, Stooge, Deluge"},
    {"word": "Human", "rhymes": "Common, Woman, Summon"}, {"word": "Humble", "rhymes": "Tumble, Rumble, Grumble"},
    {"word": "Hunger", "rhymes": "Younger, Longer, Stronger"}, {"word": "Hurry", "rhymes": "Worry, Story, Glory"},
    {"word": "Hurt", "rhymes": "Dirt, Shirt, Alert"}, {"word": "Hybrid", "rhymes": "Eyelid, High lid, My lid"},
    {"word": "Hypnotic", "rhymes": "Exotic, Chaotic, Narcotic"}, {"word": "Hypocrisy", "rhymes": "Democracy, Policy, Quality"},
    {"word": "Ice", "rhymes": "Price, Nice, Dice"}, {"word": "Icon", "rhymes": "Upon, Python, Titan"},
    {"word": "Idea", "rhymes": "Near, Clear, Fear"}, {"word": "Identity", "rhymes": "Entity, Density, Intensity"},
    {"word": "Ignite", "rhymes": "Light, Night, Fight"}, {"word": "Ignorance", "rhymes": "Instances, Distances, Synchronous"},
    {"word": "Illusion", "rhymes": "Confusion, Inclusion, Conclusion"}, {"word": "Image", "rhymes": "Damage, Baggage, Manage"},
    {"word": "Imagine", "rhymes": "Happen, Clapping, Rapping"}, {"word": "Imitate", "rhymes": "Initiate, Liquidate, Syncopate"},
    {"word": "Immortal", "rhymes": "Portal, Chortle, Mortal"}, {"word": "Impact", "rhymes": "Contract, Fact, Exact"},
    {"word": "Impatience", "rhymes": "Radiance, Cadence, Silence"}, {"word": "Imperial", "rhymes": "Material, Ethereal, Serial"},
    {"word": "Impose", "rhymes": "Close, Those, Rose"}, {"word": "Impossible", "rhymes": "Responsible, Logical (slant)"},
    {"word": "Impression", "rhymes": "Session, Lesson, Question"}, {"word": "Improve", "rhymes": "Move, Groove, Smooth"},
    {"word": "Impulse", "rhymes": "Pulse, Repulse, Convulse"}, {"word": "Incident", "rhymes": "President, Resident, Evident"},
    {"word": "Incision", "rhymes": "Precision, Division, Decision"}, {"word": "Income", "rhymes": "In some, Win some, Been dumb"},
    {"word": "Incredible", "rhymes": "Edible, Legible, Terrible"}, {"word": "Indicate", "rhymes": "Calculate, Separate, Graduate"},
    {"word": "Indigo", "rhymes": "In the flow, Let it go, Win the show"}, {"word": "Indoor", "rhymes": "Floor, Door, More"},
    {"word": "Indulge", "rhymes": "Bulge, Divulge, Result"}, {"word": "Inertia", "rhymes": "Versha, Search ya, Hurt ya"},
    {"word": "Infantry", "rhymes": "Strategy, Tragedy, Majesty"}, {"word": "Infection", "rhymes": "Direction, Protection, Connection"},
    {"word": "Inferno", "rhymes": "Journal, Eternal, Internal"}, {"word": "Infinite", "rhymes": "In it, Minute, Limit"},
    {"word": "Influence", "rhymes": "Fluent, Affluent, Truant"}, {"word": "Inform", "rhymes": "Storm, Form, Warm"},
    {"word": "Ingenious", "rhymes": "Serious, Fearless, Peerless"}, {"word": "Inhale", "rhymes": "Scale, Jail, Sail"},
    {"word": "Inherit", "rhymes": "Merit, Spirit, Ferret"}, {"word": "Initial", "rhymes": "Official, Artificial, Beneficial"},
    {"word": "Injustice", "rhymes": "Trust us, Justice, Adjust this"}, {"word": "Ink", "rhymes": "Think, Link, Drink"},
    {"word": "Innocent", "rhymes": "Continent, Increment, Immanent"}, {"word": "Innovation", "rhymes": "Location, Nation, Patient"},
    {"word": "Input", "rhymes": "Foot, Put, Look"}, {"word": "Inquiry", "rhymes": "Theory, Wearily, Fearily"},
    {"word": "Insane", "rhymes": "Pain, Rain, Lane"}, {"word": "Inscribe", "rhymes": "Tribe, Vibe, Bribe"},
    {"word": "Insight", "rhymes": "Light, Night, Fight"}, {"word": "Insomnia", "rhymes": "California, Warn ya, On ya"},
    {"word": "Inspect", "rhymes": "Respect, Direct, Collect"}, {"word": "Inspire", "rhymes": "Fire, Higher, Wire"},
    {"word": "Instance", "rhymes": "Distance, Resistance, Persistence"}, {"word": "Instinct", "rhymes": "Distinct, Linked, Sinked"},
    {"word": "Institute", "rhymes": "Absolute, Substitute, Execute"}, {"word": "Insult", "rhymes": "Result, Consult, Adult"},
    {"word": "Intact", "rhymes": "Fact, Impact, Exact"}, {"word": "Intense", "rhymes": "Sense, Defense, Expense"},
    {"word": "Intercept", "rhymes": "Except, Kept, Slept"}, {"word": "Interest", "rhymes": "Invest, West, Best"},
    {"word": "Interface", "rhymes": "Space, Chase, Face"}, {"word": "Internal", "rhymes": "Eternal, Journal, Infernal"},
    {"word": "Interpret", "rhymes": "Regret, Set, Debt"}, {"word": "Interrupt", "rhymes": "Erupt, Corrupt, Abrupt"},
    {"word": "Interval", "rhymes": "Survival, Arrival, Rival"}, {"word": "Interview", "rhymes": "View, New, True"},
    {"word": "Intimacy", "rhymes": "Legacy, Fantasy, Strategy"}, {"word": "Intricate", "rhymes": "Indicate, Syndicate, Liquidate"},
    {"word": "Intrigue", "rhymes": "League, Fatigue, Prestige"}, {"word": "Intro", "rhymes": "Go, Show, Flow"},
    {"word": "Intuition", "rhymes": "Mission, Position, Addition"}, {"word": "Invade", "rhymes": "Shade, Blade, Made"},
    {"word": "Invasion", "rhymes": "Occasion, Persuasion, Equation"}, {"word": "Inventory", "rhymes": "Story, Glory, Territory"},
    {"word": "Invest", "rhymes": "West, Best, Test"}, {"word": "Invisible", "rhymes": "Visible, Critical, Clinical"},
    {"word": "Invitation", "rhymes": "Location, Nation, Creation"}, {"word": "Involved", "rhymes": "Solved, Evolved, Resolved"},
    {"word": "Ironic", "rhymes": "Sonic, Tonic, Chronic"}, {"word": "Irrational", "rhymes": "National, Passionate (slant)"},
    {"word": "Island", "rhymes": "Silent, Violent, Highland"}, {"word": "Isolate", "rhymes": "Separate, Elevate, Graduate"},
    {"word": "Issue", "rhymes": "Tissue, Miss you, With you"}, {"word": "Item", "rhymes": "Light 'em, Fight 'em, Write 'em"},
    {"word": "Ivory", "rhymes": "Library, Binary, Diary"}, {"word": "Jackpot", "rhymes": "Backshot, Hot, Lot"},
    {"word": "Jagged", "rhymes": "Ragged, Tagged, Bagged"}, {"word": "Jail", "rhymes": "Scale, Fail, Mail"},
    {"word": "Jargon", "rhymes": "Garden, Pardon, Hardened"}, {"word": "Jealousy", "rhymes": "Legacy, Felony, Melody"},
    {"word": "Jewel", "rhymes": "Fuel, Cruel, Rule"}, {"word": "Journey", "rhymes": "Attorney, Early, Worthy"},
    {"word": "Joy", "rhymes": "Boy, Toy, Destroy"}, {"word": "Judge", "rhymes": "Grudge, Budge, Sludge"},
    {"word": "Junction", "rhymes": "Function, Compunction, Production"}, {"word": "Jungle", "rhymes": "Bundle, Rumble, Tumble"},
    {"word": "Justice", "rhymes": "Trust us, Adjust this, Rustic"}, {"word": "Justify", "rhymes": "Testify, Identify, Magnify"}
]

sentences = [
    "The city was loud, but his thoughts were louder.", "Empty pockets but a head full of blueprints.",
    "The finish line keeps moving every time I get close.", "I'm writing chapters in a book they'll never read.",
    "The static on the radio sounded like a warning.", "I traded my shadow for a chance to stand in the light.",
    "The throne is empty, but the room is full of wolves.", "I found the key, but they changed the lock yesterday.",
    "Concrete flowers growing through the cracks of the curb.", "The ink is heavy when the story is light.",
    "Neon lights flickering like a heartbeat in the rain.", "Silence is the loudest sound in a room full of fakes.",
    "I built a bridge out of the stones they threw at me.", "Buried the past but the ghost keeps digging it up.",
    "The wolves don't bark, they wait for you to sleep.", "The puzzle is finished, but there is one piece missing.",
    "A ghost in the machine, running through the static.", "The mirror doesn't lie, but it hides the scars.",
    "Counting blessings in a room full of curses.", "The horizon is a promise that the sun won't keep.",
    "Tracing constellations on a ceiling made of glass.", "The echo of a heartbeat in an empty hallway.",
    "Walking through the fire just to feel the breeze.", "The weight of the world is lighter than a lie.",
    "Silver linings tarnished by the smoke of the city.", "A compass that only points to where I've been.",
    "The rain writes poetry on the windowpane.", "Trading whispers for a chance to scream.",
    "A symphony of sirens playing in the distance.", "The taste of salt on a dream that's drifting away.",
    "Shadows dancing in the flicker of a dying candle.", "The architecture of a dream built on sand.",
    "Finding gold in the pockets of a tattered coat.", "The rhythm of the rails singing a lonesome song.",
    "A message in a bottle cast into a sea of ink.", "The gravity of the situation is pulling me down.",
    "Painting masterpieces on the walls of a cell.", "The anatomy of a heartbreak laid bare.",
    "A diamond in the rough, polished by the grit.", "The ghost of a smile on a face made of stone.",
    "Tangled in the wires of a world gone haywire.", "The scent of ozone before the storm breaks.",
    "A bridge to nowhere, built with steady hands.", "The clock is ticking, but the time is standing still.",
    "A library of secrets with no one left to read.", "The spark of an idea in a forest of doubt.",
    "Washing away the sins in a river of regret.", "The geometry of a life lived in circles.",
    "A lighthouse beam cutting through the fog of war.", "The texture of a memory fading in the sun.",
    "A kite string snapped, drifting into the blue.", "The roar of the crowd is a lonely sound.",
    "Building castles in the air, grounded by the truth.", "The alchemy of turning pain into power.",
    "A footprint in the dust of a forgotten empire.", "The velvet touch of darkness before the dawn.",
    "A bird with clipped wings dreaming of the sky.", "The vibration of a string played by the wind.",
    "A secret language spoken by the stars.", "The mosaic of a broken heart, put back together.",
    "A trail of breadcrumbs leading back to the start.", "The heat of the moment, frozen in time.",
    "A whisper in a hurricane, heard by no one.", "The anatomy of a lie, dissected and revealed.",
    "A spark in the dark, lighting up the way.", "The echoes of the past, ringing in my ears.",
    "A tapestry of dreams, woven with threads of gold.", "The fragrance of a memory, lingering in the air.",
    "A butterfly's wing, causing a storm far away.", "The stillness of a pond, reflecting the sky.",
    "A mountain peak, hidden in the clouds.", "The whisper of the leaves, telling stories of old.",
    "A hidden path, leading to a secret garden.", "The glow of the moon, illuminating the night.",
    "A shooting star, making a wish come true.", "The rhythm of the tide, washing away the past.",
    "A lighthouse in the storm, guiding ships to safety.", "The warmth of the sun, melting the ice.",
    "A blooming flower, reaching for the light.", "The song of a bird, herald of the morning.",
    "A gentle breeze, carrying the scent of spring.", "The majesty of the ocean, vast and deep.",
    "A field of wildflowers, dancing in the wind.", "The silence of the desert, peaceful and calm.",
    "A rainbow in the sky, after the rain.", "The rustle of the wind, through the tall grass.",
    "A clear blue sky, stretching out forever.", "The twinkle of the stars, like diamonds in the dark.",
    "A warm embrace, feeling safe and secure.", "The sound of laughter, filling the air.",
    "A kind word, brightening someone's day.", "The feeling of peace, deep within the soul.",
    "A sense of wonder, at the beauty of the world.", "The power of love, overcoming all obstacles.",
    "A new beginning, full of hope and promise.", "The journey of a lifetime, starting with one step.",
    "A life well-lived, leaving a legacy behind.", "The ultimate goal, achieving your dreams.",
    "The crown is heavy but I wear it like a habit.", "Watching the skyline bleed into a deep purple.",
    "Steel nerves in a city made of scrap metal.", "The pavement knows my name by the way I walk.",
    "Every scar is a map to a place I survived.", "I talk to the moon because the world won't listen.",
    "A cold wind blowing through the cracks of my ambition.", "I built this house on a foundation of 'no'.",
    "They want the fruit but they won't plant the seed.", "The skyline looks like a barcode for the rich.",
    "A pocket full of dreams and a heart full of hollow.", "The truth is a bitter pill with no water.",
    "I’m a king in a world where everyone is a jester.", "The smoke rises but the fire stays inside.",
    "Writing lines in the dust on a Cadillac hood.", "The rain doesn't wash away the shame, it just hides it.",
    "Broken glass reflecting a thousand different versions of me.", "The map is torn but I still know the way home.",
    "I found peace in the middle of a war zone.", "A whispered prayer in a room full of shouting.",
    "The elevator is broken so I’m taking the stairs to the top.", "Counting stars while they're counting my mistakes.",
    "I’m the author of a story that hasn't been written yet.", "The past is an anchor, the future is a sail.",
    "A wolf in sheep's clothing still has the same teeth.", "The silence after the beat drops is where I live.",
    "Gold chains can't hide a heart made of lead.", "I’m a diamond in a world that prefers coal.",
    "The compass is spinning but my feet are steady.", "A cold cup of coffee and a hot head of steam.",
    "The bridges I burned are lighting up my path.", "I’m a stranger in my own skin tonight.",
    "The clock is a liar, it says I’m running out of time.", "A handwritten letter in a digital world.",
    "The shadows are long but the sun is still rising.", "I’m a nomad in a city of stone walls.",
    "The ink is dry but the wound is still fresh.", "A thousand miles started with a single doubt.",
    "The rhythm is in my blood, the lyrics are in my soul.", "I’m a puzzle with a piece that doesn't exist.",
    "The wind is a thief, it stole my breath away.", "A flicker of hope in a sea of despair.",
    "The mountain is high but the view is worth the climb.", "I’m a phoenix rising from the ashes of my pride.",
    "The tide is turning and I’m ready to swim.", "A secret kept is a burden carried.",
    "The sun is a spotlight on my every mistake.", "I’m a whisper in a world that loves to yell.",
    "The stars are a reminder that I’m not alone.", "A journey of a thousand miles begins with a single bar.",
    "The ink flows like blood from a wounded heart.", "I’m a warrior in a world that wants me to surrender.",
    "The silence is a canvas, and I’m the artist.", "A dream is a vision that the heart won't let go.",
    "The world is a stage, and I’m the lead actor.", "I’m a survivor in a world that's trying to break me.",
    "The fire is burning, and I’m the fuel.", "A story told is a life remembered.",
    "The future is a blank page, and I’m the pen.", "I’m a believer in a world of skeptics.",
    "The truth is a light that shines in the darkness.", "A life lived is a lesson learned.",
    "The heart is a drum, beating out the rhythm of life.", "I’m a seeker in a world of finders.",
    "The soul is a flame that never goes out.", "A dream realized is a victory won.",
    "The world is a playground, and I’m the child.", "I’m a dreamer in a world of realists.",
    "The truth is a shield that protects the heart.", "A life shared is a life doubled.",
    "The heart is a compass, guiding the way home.", "I’m a traveler in a world of locals.",
    "The soul is a mirror, reflecting the truth.", "A dream nurtured is a dream fulfilled.",
    "The world is a classroom, and I’m the student.", "I’m a teacher in a world of learners.",
    "The truth is a weapon that cuts through the lies.", "A life celebrated is a life worth living.",
    "The heart is a garden, where dreams are grown.", "I’m a gardener in a world of weeds.",
    "The soul is a symphony, playing the music of life.", "A dream protected is a dream achieved.",
    "The world is a temple, and I’m the worshiper.", "I’m a creator in a world of destroyers.",
    "The truth is a foundation, built on solid ground.", "A life honored is a life respected.",
    "The heart is a sanctuary, where peace is found.", "I’m a peacemaker in a world of war.",
    "The soul is a masterpiece, painted by the hand of God.", "A dream shared is a dream multiplied.",
    "The world is a canvas, and I’m the paint.", "I’m an artist in a world of critics.",
    "The truth is a journey, not a destination.", "A life loved is a life transformed.",
    "The heart is a fountain, overflowing with love.", "I’m a lover in a world of haters.",
    "The soul is a star, shining bright in the night sky.", "A dream pursued is a dream caught.",
    "The world is a treasure chest, full of wonders.", "I’m a treasure hunter in a world of gold.",
    "The truth is a gift, to be shared with the world.", "A life lived fully is a life well-lived.",
    "The heart is a home, where the soul finds rest.", "I’m a homemaker in a world of nomads.",
    "The soul is a light, that can never be extinguished.", "A dream cherished is a dream come true.",
    "The world is a miracle, happening every day.", "I’m a witness to the beauty of life.",
    "The truth is a blessing, that brings peace to the soul.", "A life of purpose is a life of joy.",
    "The heart is a vessel, carrying the hopes of the world.", "I’m a hope-bringer in a world of despair.",
    "The soul is a song, that will play forever.", "A dream inspired is a dream born.",
    "The world is a gift, to be opened with joy.", "I’m a gift-receiver in a world of givers.",
    "The truth is a miracle, that changes lives.", "A life of meaning is a life of value.",
    "The heart is a treasure, to be guarded with care.", "I’m a treasure-keeper in a world of thieves.",
    "The soul is a journey, that leads to the truth.", "A dream followed is a dream found.",
    "The world is a mystery, waiting to be solved.", "I’m a mystery-solver in a world of clues.",
    "The truth is a treasure, hidden in plain sight.", "A life of service is a life of greatness.",
    "The heart is a spark, that can light up the world.", "I’m a world-changer in a world of followers.",
    "The soul is a light, that guides the way home.", "A dream envisioned is a dream created.",
    "The world is a wonder, to be explored with awe.", "I’m an explorer in a world of discoveries.",
    "The truth is a key, that unlocks the heart.", "A life of integrity is a life of honor.",
    "The heart is a bridge, that connects us all.", "I’m a bridge-builder in a world of walls.",
    "The soul is a flame, that burns with passion.", "A dream ignited is a dream realized.",
    "The world is a stage, and I’m the director.", "I’m a director in a world of actors.",
    "The truth is a power, that can change the world.", "A life of courage is a life of strength.",
    "The heart is a shield, that protects the weak.", "I’m a protector in a world of predators.",
    "The soul is a voice, that speaks the truth.", "A dream spoken is a dream heard.",
    "The world is a garden, to be tended with love.", "I’m a caretaker in a world of neglect.",
    "The truth is a light, that reveals the way.", "A life of wisdom is a life of peace.",
    "The heart is a compass, that points to the truth.", "I’m a truth-seeker in a world of lies.",
    "The soul is a light, that shines on the path.", "A dream walked is a dream lived.",
    "The world is a miracle, to be celebrated with joy.", "I’m a celebrator in a world of mourners.",
    "The truth is a gift, to be received with gratitude.", "A life of grace is a life of beauty.",
    "The heart is a fountain, that never runs dry.", "I’m a giver in a world of takers.",
    "The soul is a light, that guides us through the night.", "A dream realized is a life fulfilled.",
    "The world is a wonder, to be cherished with love.", "I’m a lover of life in a world of beauty.",
    "The truth is a light, that leads to the heart.", "A life lived in truth is a life lived in freedom.",
    "The heart is a spark, that ignites the soul.", "I’m a soul-igniter in a world of fire.",
    "The soul is a light, that shines in every heart.", "A dream for one is a dream for all.",
    "The world is a home, for all of humanity.", "I’m a world-citizen in a world of one.",
    "The truth is a light, that shines for everyone.", "A life of love is a life of light.",
    "The heart is a home, where we all belong.", "I’m a believer in the power of love.",
    "The soul is a light, that shines forevermore.", "A dream of peace is a dream for the world.",
    "The world is a miracle, and so are you.", "I’m a part of the miracle of life.",
    "The truth is a light, and you are the light.", "A life of light is a life of truth.",
    "The heart is a home, and you are home.", "I’m home in the heart of the world.",
    "The soul is a light, and you are the soul.", "A life of soul is a life of light.",
    "The world is a miracle, and we are one.", "I’m one with the miracle of life.",
    "The truth is a light, and we are the light.", "A life of light is a life of one.",
    "The heart is a home, and we are home.", "I’m home in the heart of the one.",
    "The soul is a light, and we are the soul.", "A life of soul is a life of one.",
    "The world is a miracle, and it is now.", "I’m in the miracle of now.",
    "The truth is a light, and it is now.", "A life of light is a life of now.",
    "The heart is a home, and it is now.", "I’m home in the heart of now.",
    "The soul is a light, and it is now.", "A life of soul is a life of now.",
    "The world is a miracle, and all is well.", "I’m in the miracle where all is well.",
    "The truth is a light, and all is well.", "A life of light where all is well.",
    "The heart is a home, and all is well.", "I’m home in the heart where all is well.",
    "The soul is a light, and all is well.", "A life of soul where all is well."
]

motivation = [
    "Amateurs wait for inspiration. Pros get to work.", "Your first draft is allowed to be bad. Just finish it.",
    "Consistency beats talent every single time.", "The booth is your therapist. Be honest with the mic.",
    "A page a day is a book a year. Don't stop.", "Your future self is counting on you right now.",
    "Focus on the output, not the applause.", "Don't stop when you're tired; stop when you're done.",
    "Discipline is choosing between what you want now and what you want most.", "Your potential is a debt you owe to yourself.",
    "The only way out is through.", "Greatness is a lot of small things done well every day.",
    "Don't lower your expectations to meet your reality. Raise your level.", "Success is the best revenge.",
    "Burn the boats. There's no going back.", "The grind doesn't know what day it is.",
    "Obsession will beat talent if talent doesn't work.", "Silence the inner critic with massive action.",
    "Your background is not your blueprint.", "Comfort is the enemy of growth.",
    "Don't tell them your plans. Show them your results.", "The harder the conflict, the more glorious the triumph.",
    "Everything you want is on the other side of fear.", "Be the person you needed when you were younger.",
    "Stay hungry. Stay foolish.", "Average is a failing grade.",
    "The world doesn't give you what you want; it gives you what you work for.", "Don't be afraid to give up the good to go for the great.",
    "Action is the foundational key to all success.", "Your mind is a weapon. Keep it sharp.",
    "Master the basics, then break the rules.", "If you're the smartest person in the room, you're in the wrong room.",
    "The best time to plant a tree was 20 years ago. The second best time is now.", "Make it happen.",
    "Prove them wrong.", "Don't stop until you're proud.", "Believe in yourself.", "Push your limits.",
    "Focus on your goals.", "Never give up.", "Hard work pays off.", "Success is a journey, not a destination.",
    "Be the best version of yourself.", "Dream big, work hard.", "Stay positive, work hard, make it happen.",
    "Your only limit is you.", "Do something today that your future self will thank you for.",
    "Difficult roads often lead to beautiful destinations.", "The secret of getting ahead is getting started.",
    "It always seems impossible until it's done.", "Success is not final, failure is not fatal.",
    "Hardships often prepare ordinary people for an extraordinary destiny.", "Believe you can and you're halfway there.",
    "The only person you are destined to become is the person you decide to be.", "Go confidently in the direction of your dreams.",
    "The future belongs to those who believe in the beauty of their dreams.", "Strength does not come from physical capacity.",
    "The power of imagination makes us infinite.", "You are never too old to set another goal or dream a new dream.",
    "What you get by achieving your goals is not as important as what you become.", "The only way to do great work is to love what you do.",
    "If you haven't found it yet, keep looking. Don't settle.", "Your time is limited, don't waste it living someone else's life.",
    "Have the courage to follow your heart and intuition.", "The people crazy enough to think they can change the world are the ones who do.",
    "Everything is possible if you just believe.", "The sky is the limit.", "Reach for the stars.",
    "Shoot for the moon. Even if you miss, you'll land among the stars.", "The only thing we have to fear is fear itself.",
    "In the end, it's not the years in your life that count. It's the life in your years.", "Life is what happens when you're busy making other plans.",
    "Get busy living or get busy dying.", "You only live once, but if you do it right, once is enough.",
    "In three words I can sum up everything I've learned about life: it goes on.", "To be yourself in a world trying to make you something else is the greatest accomplishment.",
    "Be who you are and say what you feel.", "The most important thing is to enjoy your life - to be happy.",
    "The greatest glory in living lies in rising every time we fall.", "The way to get started is to quit talking and begin doing.",
    "Your work is going to fill a large part of your life.", "As with all matters of the heart, you'll know when you find it.",
    "The best is yet to come.", "Believe in the power of your dreams.", "Every day is a new opportunity.",
    "Make the most of every moment.", "Life is a gift, cherish it.", "Be grateful for what you have.",
    "Help others whenever you can.", "Make the world a better place.", "Leave a positive impact.",
    "Be the change you wish to see in the world.", "The only limit to our realization of tomorrow will be our doubts of today.",
    "We can do anything we set our minds to.", "The power is within you.", "Unleash your potential.",
    "The journey starts now.", "Strive for progress, not perfection.", "Every artist was first an amateur.",
    "Don't wait for the right opportunity: create it.", "Your limitation—it's only your imagination.",
    "Push yourself, because no one else is going to do it for you.", "Sometimes later becomes never. Do it now.",
    "Great things never come from comfort zones.", "Dream it. Wish it. Do it.", "Success doesn’t just find you. You have to go out and get it.",
    "The harder you work for something, the greater you’ll feel when you achieve it.", "Dream bigger. Do bigger.",
    "Don’t stop when you’re tired. Stop when you’re done.", "Wake up with determination. Go to bed with satisfaction.",
    "Do something today that your future self will thank you for.", "Little things make big days.",
    "It’s going to be hard, but hard does not mean impossible.", "Don’t wait for opportunity. Create it.",
    "Sometimes we’re tested not to show our weaknesses, but to discover our strengths.", "The key to success is to focus on goals, not obstacles.",
    "Dream it. Believe it. Build it.", "Work hard in silence, let your success be your noise.",
    "Don’t decrease the goal. Increase the effort.", "When you feel like quitting, think about why you started.",
    "A river cuts through rock not because of its power, but because of its persistence.", "If it's important to you, you'll find a way. If not, you'll find an excuse.",
    "Hard work beats talent when talent doesn’t work hard.", "Motivation is what gets you started. Habit is what keeps you going.",
    "Don’t be afraid to fail. Be afraid not to try.", "Your passion is waiting for your courage to catch up.",
    "Everything you’ve ever wanted is on the other side of fear.", "Don’t wait for inspiration, be the inspiration.",
    "Life is short, live it. Love is rare, grab it. Anger is bad, dump it. Fear is awful, face it.",
    "The only way to reach the top is to keep climbing.", "Believe in the person you are becoming.",
    "The pain you feel today will be the strength you feel tomorrow.", "If you want it, work for it.",
    "You are capable of more than you know.", "Every morning you have two choices: continue to sleep with your dreams, or wake up and chase them.",
    "Success is what happens after you have survived all your mistakes.", "Be so good they can’t ignore you.",
    "A winner is a dreamer who never gives up.", "Focus on being productive instead of busy.",
    "You don’t have to be great to start, but you have to start to be great.", "The expert in anything was once a beginner.",
    "There are no shortcuts to any place worth going.", "The only person you should try to be better than is the person you were yesterday.",
    "Do what you have to do until you can do what you want to do.", "Keep your face always toward the sunshine—and shadows will fall behind you.",
    "Whatever you are, be a good one.", "Failure is the condiment that gives success its flavor.",
    "Doubt kills more dreams than failure ever will.", "You create your own opportunities.",
    "If you want to fly, give up everything that weighs you down.", "The goal is not to be rich. The goal is to be legendary.",
    "It’s not about having time, it’s about making time.", "Don’t count the days, make the days count.",
    "Action is the foundational key to all success.", "Your life does not get better by chance, it gets better by change.",
    "Stop doubting yourself. Work hard and make it happen.", "Stay humble. Work hard. Be kind.",
    "You didn't come this far to only come this far.", "Pressure makes diamonds.", "The best revenge is massive success.",
    "Opportunities don't happen, you create them.", "Work until your idols become your rivals.",
    "Make each day your masterpiece.", "The secret to success is found in your daily routine.",
    "I'm not here to be average, I'm here to be the best.", "If you're tired, learn to rest, not to quit.",
    "The road to success is always under construction.", "Invest in yourself. It pays the best interest.",
    "The only limit to your impact is your imagination and commitment.", "Success is a series of small wins.",
    "Don't wish it were easier, wish you were better.", "Hustle until you no longer have to introduce yourself.",
    "Your speed doesn't matter, forward is forward.", "Don't let yesterday take up too much of today.",
    "Greatness lives within you.", "Small steps in the right direction can turn out to be the biggest steps of your life.",
    "Hard work pays off in the long run.", "Success is built on a foundation of discipline.",
    "Your attitude determines your direction.", "The only way to achieve the impossible is to believe it is possible.",
    "Stay focused and never give up.", "Believe in your dreams and they will come true.",
    "Success is the result of hard work and dedication.", "Don't let anyone tell you that you can't do it.",
    "You are stronger than you think.", "The only thing standing between you and your goal is the story you keep telling yourself.",
    "Success is not about how much money you make, it's about the difference you make in people's lives.",
    "The greatest wealth is health.", "A journey of a thousand miles begins with a single step.",
    "Success is a state of mind.", "The power of positive thinking is real.",
    "You have the power to create the life you want.", "Don't be afraid to take risks.",
    "Learn from your mistakes and keep moving forward.", "Your future is in your hands.",
    "Believe in the power of your imagination.", "The sky is not the limit, it's just the beginning.",
    "Anything is possible if you put your mind to it.", "Hard work is the key to success.",
    "Never give up on your dreams.", "Success is a choice.", "You are the master of your own destiny.",
    "The only person you are competing with is yourself.", "Be proud of how far you've come.",
    "The best is yet to come.", "Stay positive and work hard.", "Your potential is limitless.",
    "Don't let your dreams be dreams.", "You can do anything you set your mind to.",
    "Success is a journey, not a destination.", "Make today count.", "Life is what you make it.",
    "Stay humble and work hard.", "Believe in yourself and all that you are.",
    "The only way to do great work is to love what you do.", "Focus on the good.",
    "Your hard work will pay off.", "Never stop learning.", "Success is a result of preparation and hard work.",
    "The only thing that stands between you and your dream is the will to try and the belief that it is actually possible.",
    "You have within you right now, everything you need to deal with whatever the world can throw at you.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "Don't be pushed by your problems. Be led by your dreams.", "Be the change you wish to see in the world.",
    "The only way to achieve the impossible is to believe it is possible.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "Hardships often prepare ordinary people for an extraordinary destiny.",
    "Believe you can and you're halfway there.", "The only person you are destined to become is the person you decide to be.",
    "Go confidently in the direction of your dreams. Live the life you have imagined.",
    "Strength does not come from physical capacity. It comes from an indomitable will.",
    "The power of imagination makes us infinite.", "You are never too old to set another goal or to dream a new dream.",
    "What you get by achieving your goals is not as important as what you become by achieving your goals.",
    "Your time is limited, so don't waste it living someone else's life.",
    "Have the courage to follow your heart and intuition.", "The people who are crazy enough to think they can change the world are the ones who do.",
    "Everything is possible if you just believe.", "The sky is the limit.", "Reach for the stars.",
    "Shoot for the moon. Even if you miss, you'll land among the stars.",
    "The only thing we have to fear is fear itself.", "In the end, it's not the years in your life that count. It's the life in your years.",
    "Life is what happens when you're busy making other plans.", "Get busy living or get busy dying.",
    "You only live once, but if you do it right, once is enough.",
    "In three words I can sum up everything I've learned about life: it goes on.",
    "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.",
    "Be who you are and say what you feel.", "The most important thing is to enjoy your life - to be happy.",
    "The greatest glory in living lies not in never falling, but in rising every time we fall.",
    "The way to get started is to quit talking and begin doing.",
    "Your work is going to fill a large part of your life, and the only way to be truly satisfied is to do what you believe is great work.",
    "The only way to do great work is to love what you do.", "If you haven't found it yet, keep looking. Don't settle.",
    "As with all matters of the heart, you'll know when you find it.", "The best is yet to come.",
    "Believe in the power of your dreams.", "Every day is a new opportunity.", "Make the most of every moment.",
    "Life is a gift, cherish it.", "Be grateful for what you have.", "Help others whenever you can.",
    "Make the world a better place.", "Leave a positive impact.", "Be the change you wish to see in the world.",
    "The only limit to our realization of tomorrow will be our doubts of today.",
    "We can do anything we set our minds to.", "The power is within you.", "Unleash your potential.",
    "The journey starts now.", "Success is a marathon, not a sprint.", "Keep your eyes on the prize.",
    "Your hard work will never go unnoticed.", "The universe rewards action.", "Be relentless in the pursuit of what sets your soul on fire.",
    "Doubt is a liar.", "Your only competition is the mirror.", "Make your excuses fear your ambitions.",
    "Turn your wounds into wisdom.", "You don't find willpower, you create it.", "Be a voice, not an echo.",
    "The best way to predict the future is to create it.", "Your dream doesn't have an expiration date.",
    "Work until your bank account looks like a phone number.", "Keep going. Everything you need will come to you at the perfect time.",
    "Start where you are. Use what you have. Do what you can.", "A little progress each day adds up to big results.",
    "The struggle you're in today is developing the strength you need for tomorrow.",
    "Everything comes to him who hustles while he waits.", "Don't stop until you're proud.",
    "The difference between who you are and who you want to be is what you do.",
    "Life is 10% what happens to us and 90% how we react to it.", "Keep your head up and your heart strong.",
    "You didn't wake up today to be mediocre.", "Great things take time.", "Be disciplined, not just motivated.",
    "Hustle and heart will set you apart.", "Success is inevitable if you don't quit.",
    "Your vibe attracts your tribe.", "Own your journey.", "Be original, be you.", "Confidence is silent. Insecurities are loud.",
    "Your life is your message to the world. Make it inspiring.", "Rise and grind.", "Make it happen, shock everyone.",
    "Do it for the people who want to see you fail.", "Focus on your goal. Don't look in any direction but ahead.",
    "Life begins at the end of your comfort zone.", "Be the game changer.", "Your only limit is you.",
    "Push yourself. No one is going to do it for you.", "The harder you work, the luckier you get.",
    "Kill them with success and bury them with a smile.", "Work hard, dream big, and never give up.",
    "Don't dream about success, work for it.", "Your dream job doesn't exist, you create it.",
    "Be a legend in the making.", "The world is yours for the taking.", "Stay hungry for success.",
    "Victory belongs to the most persevering.", "The grind is real, but the reward is worth it.",
    "Be the master of your craft.", "Never settle for less than your best.", "Go after what you want like your life depends on it.",
    "Success is earned, not given.", "The path to greatness is paved with hard work.",
    "Be the lion in a world of sheep.", "Your ambition should be greater than your fear.",
    "Work hard, stay humble.", "The best is yet to come, keep pushing.", "Every day is a chance to be better.",
    "Don't look back, you're not going that way.", "The future is bright if you work for it.",
    "Success is a mindset.", "Be the best version of yourself, every single day.",
    "Your potential is waiting for you to tap into it.", "Don't let anyone dim your light.",
    "Believe in the power of your hustle.", "The grind never stops.", "Success is within your reach.",
    "Work hard and stay dedicated.", "Your dreams are worth the effort.", "Keep striving for greatness.",
    "The world is waiting for your unique talent.", "Be the hero of your own story.",
    "Success is a reflection of your hard work.", "Don't be afraid to stand out.",
    "Your journey is unique, embrace it.", "Keep your eyes on the stars and your feet on the ground.",
    "Hard work is the foundation of success.", "The only way to fail is to stop trying.",
    "Believe in the magic of your dreams.", "Success is the ultimate goal, keep working for it.",
    "Your ambition will take you far.", "Never give up on what you truly want.",
    "Success is a result of consistent effort.", "Be the architect of your own future.",
    "The world is full of opportunities, grab them.", "Your potential is infinite.",
    "Stay focused and never lose sight of your goals.", "Success is a journey that starts with a single step.",
    "Work hard and stay true to yourself.", "Your dreams are within your power to achieve.",
    "Keep pushing forward, no matter what.", "Success is the reward for your hard work.",
    "Believe in the power of your own voice.", "Your unique perspective is your greatest strength.",
    "Stay dedicated to your craft.", "Success is a result of your commitment.",
    "Don't let anything stop you from reaching your goals.", "Your journey is just beginning.",
    "Keep striving for excellence.", "The world is your canvas, paint it with your dreams.",
    "Success is the ultimate destination, keep moving towards it.", "Your potential is waiting to be realized.",
    "Believe in the beauty of your own journey.", "Success is a result of your perseverance.",
    "Don't be afraid to take the road less traveled.", "Your dreams are worth every sacrifice.",
    "Keep working hard and stay focused on your vision.", "The world is full of possibilities, explore them.",
    "Success is the fruit of your labor.", "Your ambition is the fuel for your success.",
    "Believe in the power of your own dreams.", "Your hard work will lead you to greatness.",
    "Stay committed to your goals.", "Success is a result of your passion.",
    "Don't let anything hold you back from achieving your dreams.", "Your journey is a testament to your strength.",
    "Keep pushing boundaries.", "The world is yours to conquer.", "Success is the final reward.",
    "Believe in yourself and your ability to succeed.", "Your potential is limitless, keep reaching for the stars.",
    "Hard work is the key to unlocking your dreams.", "The only limit to your success is your own imagination.",
    "Success is a journey of growth and discovery.", "Don't be afraid to dream big.",
    "Your ambition will carry you to new heights.", "Keep working hard and never give up on your dreams.",
    "Success is a reflection of your dedication.", "Believe in the power of your own potential.",
    "Your hard work will pay off in ways you can't even imagine.", "Stay focused on your journey.",
    "Success is the ultimate prize for your perseverance.", "Don't let anything stop you from becoming the person you were meant to be.",
    "Your dreams are within reach, keep reaching.", "Keep striving for the top.",
    "The world is waiting for your unique contribution.", "Success is the result of your relentless pursuit.",
    "Believe in the power of your own ambition.", "Your journey is a masterpiece in progress.",
    "Keep pushing forward with confidence.", "The world is full of wonders, discover them.",
    "Success is the reward for your unwavering commitment.", "Don't be afraid to reach for the stars.",
    "Your potential is waiting for you to unleash it.", "Keep working hard and stay true to your vision.",
    "Success is the final destination on your journey of excellence."
]
# --- 5. INITIALIZE PAGE ---
st.set_page_config(page_title="Rap Journal", page_icon="📝")
words, sentences = get_synced_data()
hist_file = get_github_file(HISTORY_PATH)
full_text = base64.b64decode(hist_file['content']).decode('utf-8') if hist_file else ""

user_points, user_streak, user_inventory = calculate_stats(full_text)

# Send Daily Notification once
if send_notification(user_streak, full_text):
    new_log = f"NOTIFIED: {be_now.strftime('%d/%m/%Y')}\n" + full_text
    update_github_file(HISTORY_PATH, new_log, "Logged Notification Status")

# --- 6. SIDEBAR: SHOP & ACHIEVEMENTS ---
with st.sidebar:
    st.title("🕹️ Studio Dashboard")
    game_mode = st.toggle("Enable Game Mode", value=True)
    
    if game_mode:
        st.subheader(f"💰 Balance: {user_points} RC")
        
        # ACHIEVEMENTS (Automatic Milestone Unlocks)
        st.divider()
        st.markdown("### 🏆 Achievements")
        if user_streak >= 7: st.success("🎖️ Weekly Warrior (7 Day Streak)")
        if user_streak >= 30: st.warning("👑 Rap Legend (30 Day Streak)")
        
        # THE SHOP (Purchase System)
        st.divider()
        st.markdown("### 🛒 Studio Shop")
        
        def render_shop_item(item_name, cost):
            if item_name in user_inventory:
                st.info(f"✅ {item_name} Owned")
                return True
            elif user_points >= cost:
                if st.button(f"Buy {item_name} ({cost} RC)"):
                    new_hist = f"PURCHASE: {item_name}\n" + full_text
                    update_github_file(HISTORY_PATH, new_hist, f"Bought {item_name}")
                    st.toast(f"Purchased {item_name}!")
                    st.rerun()
            else:
                st.button(f"🔒 {item_name} ({cost} RC)", disabled=True)
            return False

        has_cat = render_shop_item("Studio Cat", 300)
        has_neon = render_shop_item("Neon Layout", 150)
        has_gold = render_shop_item("Gold Studio", 1000)

        if has_neon and st.toggle("Activate Neon"):
            st.markdown("<style>.stApp { background-color: #0E1117; color: #00FFA2; }</style>", unsafe_content_html=True)

# --- 7. MAIN INTERFACE ---
unlocked_crown = user_streak >= 30
title_icon = "👑" if unlocked_crown else "🎤"
st.title(f"{title_icon} Smart Rap Journal")

if game_mode and "Studio Cat" in user_inventory:
    st.markdown("### 🐱 Studio Cat: Chillin'")

if "current_date" not in st.session_state:
    st.session_state.current_date = be_now.date()

selected_date = st.date_input("Select Date:", value=st.session_state.current_date)
formatted_date = selected_date.strftime('%d/%m/%Y')

# Display Word for selected day
selected_day_of_year = selected_date.timetuple().tm_yday
if words:
    dw = words[selected_day_of_year % len(words)]
    ds = sentences[selected_day_of_year % len(sentences)]
    st.info(f"**WORD:** {dw['word'].upper()} | **PROMPT:** {ds}")

# Writing & Saving
user_lyrics = st.text_area("Write your lyrics:", height=300)
if st.button("🚀 Save Entry"):
    new_entry = f"DATE: {formatted_date}\nWORD: {dw['word'].upper()}\nLYRICS:\n{user_lyrics}\n"
    update_github_file(HISTORY_PATH, new_entry + "------------------------------\n" + full_text, f"Entry: {formatted_date}")
    st.success("Entry Saved to GitHub!")
    st.rerun()

# --- 8. TIMELINE ---
st.divider()
st.subheader("📜 Your Rap Timeline")
start_date = datetime(2025, 12, 19).date() 
delta = be_now.date() - start_date
for i in range(delta.days + 1):
    current_day = be_now.date() - timedelta(days=i)
    d_str = current_day.strftime('%d/%m/%Y')
    if f"DATE: {d_str}" in full_text:
        with st.expander(f"📅 {d_str}"):
            st.text(full_text.split(f"DATE: {d_str}")[1].split("------------------------------")[0].strip())
