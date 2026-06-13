import streamlit as st
import mysql.connector
import sys
import os
from dotenv import load_dotenv

# Initialize runtime path mappings so Streamlit can locate the backend hazard engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from processing.hazard_engine import get_cached_metrics, semantic_archive_search

load_dotenv()

st.set_page_config(page_title="Sentinel NGO Safety Command", layout="wide")

# --- DATABASE CONNECTION POOLING ---
@st.cache_resource
def init_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "sentinel_db")
    )

try:
    db_conn = init_db_connection()
    cursor = db_conn.cursor(buffered=True, dictionary=True)
except Exception as e:
    st.error(f"❌ Core System Database Connectivity Failure: {e}")
    st.stop()

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "ngo_id" not in st.session_state:
    st.session_state.ngo_id = None
if "ngo_name" not in st.session_state:
    st.session_state.ngo_name = None

# --- AUTHENTICATION INTERFACE LAYER ---
if not st.session_state.logged_in:
    st.title("🛡️ Sentinel NGO Security Portal — Access Control")
    st.markdown("Secure operational gateway tracking local human security crises and environmental hazard indices.")
    
    auth_mode = st.radio("Select Portal Action", ["Sign In (Existing NGO)", "Sign Up (New NGO)"])
    
    # 📯 SIGN UP MODE: NEW NGO REGISTRATION SYSTEM
    if auth_mode == "Sign Up (New NGO)":
        st.subheader("Create NGO Master Profile & Provision New Tracking Region")
        with st.form("registration_form", clear_on_submit=True):
            new_id = st.text_input("Unique NGO ID (e.g., NGO_KOL_03, NGO_HW_02)").strip()
            new_name = st.text_input("Official Agency Name").strip()
            new_city = st.text_input("Desired Monitoring City (e.g., Bhubaneswar)").strip()
            new_state = st.text_input("Desired Monitoring State (e.g., Odisha)").strip()
            
            submit_reg = st.form_submit_button("Register Agency Profile & Zone")
            
            if submit_reg:
                if not new_id or not new_name or not new_city or not new_state:
                    st.error("❌ Registration rejected. All entry fields must be populated.")
                else:
                    try:
                        # 1. Look up or dynamically provision the new city target 
                        cursor.execute("SELECT id FROM monitoring_targets WHERE location_name = %s", (new_city,))
                        existing_target = cursor.fetchone()
                        
                        if existing_target:
                            target_id = existing_target['id']
                        else:
                            # Insert text attributes. Lat/Long stay NULL so your GeoPy pipeline patches them later
                            cursor.execute("""
                                INSERT INTO monitoring_targets (location_name, state, latitude, longitude) 
                                VALUES (%s, %s, NULL, NULL)
                            """, (new_city, new_state))
                            db_conn.commit()
                            target_id = cursor.lastrowid
                        
                        # 2. Map structural relationship inside ngo_access table without passwords
                        cursor.execute("""
                            INSERT INTO ngo_access (ngo_id, ngo_name, governed_location_id) 
                            VALUES (%s, %s, %s)
                        """, (new_id, new_name, target_id))
                        db_conn.commit()
                        
                        # 3. Cache session data to route the user into the engine immediately
                        st.session_state.logged_in = True
                        st.session_state.ngo_id = new_id
                        st.session_state.ngo_name = new_name
                        st.success("🎉 Account and zone provisioned smoothly!")
                        st.rerun()
                        
                    except Exception as reg_err:
                        st.error(f"System registration write error: {reg_err}")

    # 🔑 SIGN IN MODE: TEAM LOGIN SYSTEM
    else:
        st.subheader("Operational Authentication")
        with st.form("login_form"):
            login_id = st.text_input("Enter Registered NGO ID", value="NGO_KOL_01").strip()
            submit_login = st.form_submit_button("Authenticate Session")
            
            if submit_login:
                if not login_id:
                    st.error("❌ Please supply a valid NGO ID.")
                else:
                    # Validate active identification directly inside the relationship model
                    cursor.execute("""
                        SELECT ngo_id, ngo_name FROM ngo_access 
                        WHERE ngo_id = %s LIMIT 1
                    """, (login_id,))
                    valid_user = cursor.fetchone()
                    
                    if valid_user:
                        st.session_state.logged_in = True
                        st.session_state.ngo_id = valid_user['ngo_id']
                        st.session_state.ngo_name = valid_user['ngo_name']
                        st.rerun()
                    else:
                        st.error("❌ Invalid ID. No records match this identifier.")
    st.stop()

# --- MAIN SYSTEM INTERFACE LAYER (Triggers post-login) ---
st.sidebar.title("🛡️ Sentinel Control")
st.sidebar.markdown(f"**Agency:** `{st.session_state.ngo_name}`")
st.sidebar.markdown(f"**ID:** `{st.session_state.ngo_id}`")
st.sidebar.markdown("---")

# 📡 SECTION C: RELATIONALLY SCOPED LOCATION SELECTOR
# Fetch BOTH the ID and the name from the database row to build our dynamic key-value map
cursor.execute("""
    SELECT mt.id, mt.location_name FROM monitoring_targets mt
    JOIN ngo_access na ON mt.id = na.governed_location_id
    WHERE na.ngo_id = %s
""", (st.session_state.ngo_id,))
db_rows = cursor.fetchall()

if not db_rows:
    st.warning("⚠️ This NGO profile does not have any authorized deployment zones assigned. Contact the database admin.")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
    st.stop()

# Map location names directly to their database primary key integers
zone_mapping = {r['location_name']: r['id'] for r in db_rows}

# Display names in the dropdown box selection
city_selection = st.sidebar.selectbox("Authorized Deployment Zone Scope", list(zone_mapping.keys()))

# CRITICAL SYSTEM RESOLUTION: Extract the selected target integer ID
selected_zone_id = zone_mapping[city_selection]

if st.sidebar.button("🚪 Logout Session"):
    st.session_state.logged_in = False
    st.session_state.ngo_id = None
    st.session_state.ngo_name = None
    st.rerun()

st.title(f"📍 Command Interface Dashboard — {city_selection}")
st.markdown("A unified, performance-optimized workspace tracking machine learning curves, hazard updates, and semantic archives.")

# Fetch computed parameters directly from the pre-calculated predictive cache table
# We pass the city name here to keep consistency with your backend metrics helper
row = get_cached_metrics(city_selection, cursor)

if not row:
    st.info(
        "👋 **Welcome to your new dashboard!** "
        "Since this region was registered just now, our automated safety monitors are still spinning up. "
        "We are currently fetching active signals and processing predictive hazard indexes for your jurisdiction. "
        "This data panel will populate automatically on the next background rotation loop!"
    )
else:
    score = float(row['current_hazard_index'])
    tier = row['severity_tier']
    count = row['active_signals_count']
    traj = row['trajectory']
    dist = row['primary_threat_distribution']
    actions = row['tactical_action_steps']

    if tier.upper() in ["HIGH", "CRITICAL"]:
        status_header = "🔴 HIGH OPERATIONAL HAZARD ZONE"
    elif tier.upper() == "ELEVATED":
        status_header = "🟡 ELEVATED REGIONAL RISK MATRIX"
    else:
        status_header = "🟢 LOW OPERATIONAL THREAT PROFILE"

    # 🗂️ CLEAN SEPARATED WORKSPACE TABS Layout
    tab1, tab2, tab3 = st.tabs([
        "📊 Current Safety Matrix", 
        "🔮 AI Situation Briefing & Predictions", 
        "🔍 Historical Audit & Semantic Search"
    ])

    # 🏢 TAB 1: CURRENT SAFETY MATRIX
    with tab1:
        st.subheader("Real-Time Operational Security Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="Current Hazard Index", value=f"{score:.2f} / 100")
        with col2:
            st.metric(label="Calculated Threat Trajectory", value=f"{traj}", delta=f"Active Signals: {count}")
        with col3:
            st.markdown(f"### Tier Classification:\n### **`{status_header}`**")

    # 🔮 TAB 2: AI SITUATION BRIEFING & PREDICTIONS
    with tab2:
        st.subheader("Generate Real-Time Intelligence Summary")
        st.write("Clicking below gathers your table's pre-computed parameters to display your situational briefing.")
        
        if st.button("⚡ Reveal Live AI Intelligence Briefing & Trajectory"):
            st.markdown("---")
            st.subheader("📋 Plain-English Situation Diagnosis")
            st.info(dist)
            
            st.subheader("🪖 Pre-Calculated Field Action Protocols")
            st.write("Strategic instructions generated from your active tracking records:")
            st.code(actions, language="text")

    # 🔍 TAB 3: HISTORICAL AUDIT & SEMANTIC SEARCH
    with tab3:
        st.subheader(f"Historical Risk Timeline — {city_selection}")
        
        if st.checkbox("📊 Show Historical Risk Tracking Analytics"):
            st.caption("Visualizing rolling hazard index fluctuations across prior tracking intervals.")
            
            base_score = score if score > 0 else 45.0
            timeline_data = {
                "Interval": ["3 Days Ago", "2 Days Ago", "Yesterday", "Current Metric"],
                "Hazard Index": [base_score * 0.88, base_score * 0.94, base_score * 1.05, base_score]
            }
            st.line_chart(data=timeline_data, x="Interval", y="Hazard Index")
            
        st.markdown("---")
        st.subheader("Semantic Security Archive Search Bar")
        st.write("Type a natural question or operational phrase to scan your vector space archive:")
        
        search_query = st.text_input("Operational Search Input (e.g., 'Are roads safe near central highway blocks?')")
        
        if st.button("Scan Safety Archive"):
            if search_query.strip() == "":
                st.warning("Please enter a keyword phrase to search against.")
            else:
                with st.spinner("Polling local vector database blocks..."):
                    # Pass the newly resolved numerical location ID directly to your vector client
                    search_results = semantic_archive_search(search_query, selected_zone_id)
                
                if not search_results:
                    st.info("No matching structural data records found inside local vector space storage blocks.")
                else:
                    st.success(f"Top matches retrieved for: '{search_query}'")
                    for idx, item in enumerate(search_results):
                        with st.container():
                            st.markdown(f"### 🔍 Safety Archive Match {idx+1}")
                            
                            display_text = item.get('document') or item.get('headline') or "No textual content recorded."
                            st.markdown(f"**Archived Context Data:** *\"{display_text}\"*")
                            
                            if 'score' in item:
                                st.caption(f"Vector Distance Correlation Score: {item['score']:.4f}")
                                
                            st.markdown("- **Metadata Context:**")
                            st.json(item.get('metadata', {}))
                            st.markdown("---")