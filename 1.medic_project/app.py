import streamlit as st
import pandas as pd
import os
import sqlite3
from core_logic import process_new_medicine, supabase

st.set_page_config(page_title="Medic-Claimer Cloud Dashboard", layout="wide")

# --- Session State for Tracking Current Session Uploads ---
if 'session_uploads' not in st.session_state:
    st.session_state.session_uploads = []

# --- Authentication Logic ---
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
    st.title("🛡️ Secure Access Portal")
    role_choice = st.selectbox("Select Role", ["Contributor", "Admin"])
    password = st.text_input("Enter Access Key:", type="password")
    if st.button("Login"):
        if role_choice == "Admin" and password == "Admin@123":
            st.session_state.role = "admin"
            st.rerun()
        elif role_choice == "Contributor" and password == "Medic2026":
            st.session_state.role = "user"
            st.rerun()
    st.stop()

# --- HELPER: Fetch Full DB ---
def fetch_data():
    try:
        response = supabase.table("inventory").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Cloud Fetch Error: {e}")
        return pd.DataFrame()

# --- Navigation ---
st.sidebar.title(f"👤 {st.session_state.role.upper()}")
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.session_state.session_uploads = [] # Clear session on logout
    st.rerun()

# Dynamic Menu Based on Demand
if st.session_state.role == "admin":
    menu = ["Data Ingestion", "Master Inventory (Admin)"]
else:
    menu = ["Data Ingestion", "Verify My Uploads", "Dataset Preview (Read-Only)"]

page = st.sidebar.radio("Navigation", menu)

# 1. Data Ingestion
if page == "Data Ingestion":
    st.header("📤 Medicine Data Ingestion")
    name = st.text_input("Medicine Label:").lower().strip()
    file = st.file_uploader("Upload Image", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Cloud"):
        if file and name:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: f.write(file.getbuffer())
            with st.spinner("Processing to Cloud..."):
                success = process_new_medicine(temp_p, name)
            
            if os.path.exists(temp_p): os.remove(temp_p)
            
            if success: 
                # Add to session tracking so user can edit it later
                st.session_state.session_uploads.append(name) 
                st.success(f"✅ '{name}' stored! Ab tum ise 'Verify My Uploads' me sahi kar sakte ho.")
            else: 
                st.warning("⚠️ Duplicate image hash or Connection Error!")

# 2. Contributor: Verify & Edit My Session Data
elif page == "Verify My Uploads":
    st.header("📝 Edit Your Current Session Data")
    df = fetch_data()
    
    if not df.empty:
        # Filter: Sirf wahi rows jo is session me upload hui hain
        my_df = df[df['name'].isin(st.session_state.session_uploads)]
        
        if not my_df.empty:
            st.write("Tumne abhi ye data add kiya hai. Agar AI ne features galat detect kiye hain toh sahi kar do:")
            st.dataframe(my_df, use_container_width=True)
            
            edit_id = st.selectbox("Select ID to Correct:", my_df['id'].tolist())
            row = my_df[my_df['id'] == edit_id].iloc[0]
            
            # Form for editing
            with st.form("edit_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    u_color = st.text_input("Correct Color:", row['color'])
                    u_shape = st.text_input("Correct Shape:", row['shape'])
                with col2:
                    u_imprint = st.text_area("Correct Imprint:", row['imprint'])
                with col3:
                    st.image(row['img_url'], caption="Your Upload", width=200)
                
                if st.form_submit_button("Update My Record"):
                    supabase.table("inventory").update({
                        "color": u_color, "shape": u_shape, "imprint": u_imprint
                    }).eq("id", edit_id).execute()
                    st.success("Record Updated!")
                    st.rerun()
        else:
            st.info("Tumne is session me abhi tak koi data commit nahi kiya hai.")

# 3. Contributor: Read-Only Dataset Preview (Full Data)
elif page == "Dataset Preview (Read-Only)":
    st.header("🔍 Global Dataset Preview")
    st.info("Pura dataset yahan dekh sakte ho. Modification ke liye Admin access chahiye.")
    df = fetch_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Database khali hai.")

# 4. Admin: Master Control
elif page == "Master Inventory (Admin)":
    st.header("🔑 Central Inventory Control")
    df = fetch_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        st.subheader("🛠️ Master Edit (Admin Only)")
        selected_id = st.number_input("Enter Record ID to Edit:", min_value=1)
        
        if selected_id in df['id'].values:
            row = df[df['id'] == selected_id].iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                u_name = st.text_input("Edit Name:", row['name'])
                u_color = st.text_input("Edit Color:", row['color'])
            with c2:
                u_shape = st.text_input("Edit Shape:", row['shape'])
                u_imprint = st.text_area("Edit Imprint:", row['imprint'])
            with c3:
                st.image(row['img_url'], caption="Cloud Resource", width=250)
            
            if st.button("Update Master Cloud Record"):
                supabase.table("inventory").update({
                    "name": u_name, "color": u_color, "shape": u_shape, "imprint": u_imprint
                }).eq("id", selected_id).execute()
                st.success("Master Record Updated in Cloud!")
                st.rerun()
