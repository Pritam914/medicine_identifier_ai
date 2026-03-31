import streamlit as st
import pandas as pd
import os
import sqlite3
from core_logic import process_new_medicine, supabase

# --- Page Configuration ---
st.set_page_config(page_title="Medic-Claimer Cloud Dashboard", layout="wide")

# --- Session State Management ---
# Tracks the medicine names uploaded in the current active session
if 'session_uploads' not in st.session_state:
    st.session_state.session_uploads = []

# --- Authentication Logic ---
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.title("🛡️ Secure Access Portal")
    role_choice = st.selectbox("Select Access Level", ["Contributor", "Admin"])
    password = st.text_input("Access Key:", type="password")
    
    if st.button("Authorize"):
        if role_choice == "Admin" and password == "Admin@123":
            st.session_state.role = "admin"
            st.rerun()
        elif role_choice == "Contributor" and password == "Medic2026":
            st.session_state.role = "user"
            st.rerun()
        else:
            st.error("Authentication Failed: Invalid Credentials")
    st.stop()

# --- Database Utility Functions ---
def fetch_data():
    """Fetches the complete inventory dataset from Supabase Cloud."""
    try:
        response = supabase.table("inventory").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Data Retrieval Error: {e}")
        return pd.DataFrame()

# --- Sidebar Navigation ---
st.sidebar.title(f"👤 Account: {st.session_state.role.upper()}")
if st.sidebar.button("Terminals Logout"):
    st.session_state.role = None
    st.session_state.session_uploads = [] # Clear temporary tracking
    st.rerun()

# Defining dynamic menu based on user permissions
if st.session_state.role == "admin":
    menu = ["Data Ingestion", "Master Inventory (Admin)"]
else:
    menu = ["Data Ingestion", "Verify My Uploads", "Dataset Preview (Read-Only)"]

page = st.sidebar.radio("Navigation Menu", menu)

# --- Page 1: Data Ingestion ---
if page == "Data Ingestion":
    st.header("📤 Medicine Data Ingestion")
    st.markdown("Enter medicine details and upload a high-quality image for AI feature extraction.")
    
    name = st.text_input("Medicine Name/Label:").lower().strip()
    file = st.file_uploader("Upload Image Resource", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Cloud Storage"):
        if file and name:
            temp_p = f"temp_{file.name}"
            # Write temporary file for local processing before cloud upload
            with open(temp_p, "wb") as f: 
                f.write(file.getbuffer())
                
            with st.spinner("Executing AI Analysis & Cloud Transfer..."):
                success = process_new_medicine(temp_p, name)
            
            # Cleanup local temporary resources
            if os.path.exists(temp_p): 
                os.remove(temp_p)
            
            if success: 
                st.session_state.session_uploads.append(name) 
                st.success(f"✅ Record for '{name}' successfully committed. You may now review it in 'Verify My Uploads'.")
            else: 
                st.warning("⚠️ Submission Rejected: Duplicate image hash or Network Error detected.")
        else:
            st.error("Incomplete Data: Please ensure both name and image are provided.")

# --- Page 2: Contributor Verification ---
elif page == "Verify My Uploads":
    st.header("📝 Review Current Session Contributions")
    st.markdown("Verify the AI-extracted features for your recent uploads and apply corrections if necessary.")
    
    df = fetch_data()
    
    if not df.empty:
        # Filter data to show only entries submitted during the current session
        my_df = df[df['name'].isin(st.session_state.session_uploads)]
        
        if not my_df.empty:
            st.dataframe(my_df, use_container_width=True)
            
            edit_id = st.selectbox("Select Record ID for Correction:", my_df['id'].tolist())
            row = my_df[my_df['id'] == edit_id].iloc[0]
            
            # Correction Form
            with st.form("correction_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    u_color = st.text_input("Corrected Color:", row['color'])
                    u_shape = st.text_input("Corrected Shape:", row['shape'])
                with col2:
                    u_imprint = st.text_area("Corrected Imprint:", row['imprint'])
                with col3:
                    st.image(row['img_url'], caption="Uploaded Reference", width=200)
                
                if st.form_submit_button("Update Record"):
                    supabase.table("inventory").update({
                        "color": u_color, "shape": u_shape, "imprint": u_imprint
                    }).eq("id", edit_id).execute()
                    st.success(f"Record {edit_id} updated successfully.")
                    st.rerun()
        else:
            st.info("No active session uploads found. Data committed in previous sessions cannot be edited by contributors.")

# --- Page 3: Global Dataset Preview (Read-Only) ---
elif page == "Dataset Preview (Read-Only)":
    st.header("🔍 Global Dataset Preview")
    st.markdown("Comprehensive view of all collected medicine data. Edit permissions are restricted to Admin roles.")
    
    df = fetch_data()
    if not df.empty:
        st.write(f"Total Records Collected: {len(df)}")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Cloud database is currently empty.")

# --- Page 4: Admin Master Control ---
elif page == "Master Inventory (Admin)":
    st.header("🔑 Central Inventory Management")
    st.markdown("Master control panel for full dataset auditing and administrative corrections.")
    
    df = fetch_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        
        st.subheader("🛠️ Administrative Data Overwrite")
        selected_id = st.number_input("Target Record ID:", min_value=1)
        
        if selected_id in df['id'].values:
            row = df[df['id'] == selected_id].iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                u_name = st.text_input("Edit Name Label:", row['name'])
                u_color = st.text_input("Edit Color Property:", row['color'])
            with c2:
                u_shape = st.text_input("Edit Shape Property:", row['shape'])
                u_imprint = st.text_area("Edit Imprint Text:", row['imprint'])
            with c3:
                st.image(row['img_url'], caption="Cloud Master Image", width=250)
            
            if st.button("Apply Administrative Update"):
                supabase.table("inventory").update({
                    "name": u_name, "color": u_color, "shape": u_shape, "imprint": u_imprint
                }).eq("id", selected_id).execute()
                st.success(f"Master Record {selected_id} has been modified.")
                st.rerun()
