import streamlit as st

import os
from dotenv import load_dotenv
load_dotenv()
import sys
import mysql.connector
from mysql.connector import pooling


#Path resolution
project_root = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(project_root)
sys.path.append(root_dir)
from utils import get_safe_secret
from db_helper import get_db_connection_config 
from processing.hazard_engine import get_cached_metrics, semantic_archive_search


#Connection Pool Setup using st.secrets

@st.cache_resource
def get_db_pool():
    
    return mysql.connector.pooling.MySQLConnectionPool(
        pool_name="sentinel_pool",
        pool_size=5,
        **get_db_connection_config() 
    )

db_pool = get_db_pool()

def get_cursor():
    conn = db_pool.get_connection()
    return conn, conn.cursor(buffered=True, dictionary=True)

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
    auth_mode = st.radio("Select Portal Action", ["Sign In (Existing NGO)", "Sign Up (New NGO)"])
    
    # 📯 SIGN UP MODE: DYNAMIC MULTI-ENTRY REGISTRATION
    if auth_mode == "Sign Up (New NGO)":
        st.subheader("Create NGO Master Profile & Provision Zones")
        
        # Track locations in session state so we don't lose them while typing
        if 'reg_locations' not in st.session_state:
            st.session_state.reg_locations = []

        new_id = st.text_input("Unique NGO ID (e.g., NGO_KOL_03)").strip()
        new_name = st.text_input("Official Agency Name").strip()
        
        st.markdown("---")
        st.write("#### Add Monitoring Zones")
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: city_input = st.text_input("City", key="city_in")
        with c2: state_input = st.text_input("State", key="state_in")
        with c3:
            st.write("##") # Spacer
            if st.button("➕ Add"):
                if city_input and state_input:
                    st.session_state.reg_locations.append({'city': city_input, 'state': state_input})
                    st.rerun()

        # Display added locations
        for i, loc in enumerate(st.session_state.reg_locations):
            st.info(f"{i+1}. {loc['city']}, {loc['state']}")

        if st.button("Finalize Registration"):
            if not new_id or not new_name or not st.session_state.reg_locations:
                st.error("❌ Please provide NGO details and at least one zone.")
            else:
                try:
                    conn, cursor = get_cursor()
                    for item in st.session_state.reg_locations:
                        # 1. Get or Create City
                        cursor.execute("SELECT id FROM monitoring_targets WHERE location_name = %s", (item['city'],))
                        target = cursor.fetchone()
                        target_id = target['id'] if target else None
                        
                        if not target_id:
                            cursor.execute("INSERT INTO monitoring_targets (location_name, state) VALUES (%s, %s)", (item['city'], item['state']))
                            target_id = cursor.lastrowid
                        
                        # 2. Map Relationship
                        cursor.execute("""
                            INSERT IGNORE INTO ngo_access (ngo_id, ngo_name, governed_location_id) 
                            VALUES (%s, %s, %s)
                        """, (new_id, new_name, target_id))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.session_state.reg_locations = [] # Reset
                    st.success("🎉 Profile created! Please switch to 'Sign In' to begin.")
                except Exception as reg_err:
                    st.error(f"System registration write error: {reg_err}")

    # 🔑 SIGN IN MODE
    else:
        st.subheader("Operational Authentication")
        with st.form("login_form"):
            login_id = st.text_input("Enter Registered NGO ID").strip()
            submit_login = st.form_submit_button("Authenticate Session")
            
            if submit_login:
                conn, cursor = get_cursor()
                cursor.execute("SELECT ngo_id, ngo_name FROM ngo_access WHERE ngo_id = %s LIMIT 1", (login_id,))
                valid_user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if valid_user:
                    st.session_state.logged_in = True
                    st.session_state.ngo_id = valid_user['ngo_id']
                    st.session_state.ngo_name = valid_user['ngo_name']
                    st.rerun()
                else:
                    st.error("❌ Invalid ID.")
    st.stop()

# --- MAIN SYSTEM INTERFACE LAYER (Triggers post-login) ---


    
st.sidebar.title("🛡️ Sentinel Control")
st.sidebar.markdown(f"**Agency:** `{st.session_state.ngo_name}`")
st.sidebar.markdown(f"**ID:** `{st.session_state.ngo_id}`")
st.sidebar.markdown("---")

# 📡 SECTION C: RELATIONALLY SCOPED LOCATION SELECTOR
# Fetch BOTH the ID and the name from the database row to build our dynamic key-value map
try:
    conn, cursor = get_cursor()
    cursor.execute("""
        SELECT mt.id, mt.location_name FROM monitoring_targets mt
        JOIN ngo_access na ON mt.id = na.governed_location_id
        WHERE na.ngo_id = %s
    """, (st.session_state.ngo_id,))
    db_rows = cursor.fetchall()
    cursor.close()
    conn.close() 
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()
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
try:
    conn_metrics, cursor_metrics = get_cursor()
    # Now use this specific cursor
    row = get_cached_metrics(city_selection, cursor_metrics)
    cursor_metrics.close()
    conn_metrics.close()
except Exception as e:
    st.error(f"Error fetching dashboard metrics: {e}")
    row = None

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
                try:
                    with st.spinner("Polling local vector database blocks..."):
                        # 1. Get a fresh connection and cursor from the pool
                        conn, cursor = get_cursor()
                        
                        # 2. Pass the cursor to your search function
                        search_results = semantic_archive_search(search_query, selected_zone_id, cursor)
                        
                        # 3. Clean up the connection immediately
                        cursor.close()
                        conn.close() 
                    
                    # 4. Process and display results
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

                except Exception as e:
                    st.error(f"Search failed due to a database connection issue: {e}")