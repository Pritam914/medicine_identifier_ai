import streamlit as st
import pandas as pd
import os
from core_logic import process_new_medicine, supabase

# --- 1. Page Configuration ---
st.set_page_config(page_title="Medic-Claimer AI Dashboard", layout="wide")

# --- 2. Session State for Tracking ---
if 'session_uploads' not in st.session_state:
    st.session_state.session_uploads = []

if "role" not in st.session_state:
    st.session_state.role = None

# --- 3. Authentication Logic ---
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

# --- 4. Helper Function ---
def fetch_data():
    try:
        response = supabase.table("inventory").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Data Retrieval Error: {e}")
        return pd.DataFrame()

# --- 5. Navigation Sidebar ---
st.sidebar.title(f"👤 Account: {st.session_state.role.upper()}")
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.session_state.session_uploads = []
    st.rerun()

# Define menu based on role
if st.session_state.role == "admin":
    menu = ["Data Ingestion", "Master Inventory (Admin)"]
else:
    menu = ["Data Ingestion", "Verify My Uploads", "Dataset Preview (Read-Only)"]

# THIS DEFINES THE 'page' VARIABLE
page = st.sidebar.radio("Navigation Menu", menu)

# --- 6. Page Logic ---

if page == "Data Ingestion":
    st.header("📤 Advanced Medicine Data Ingestion")
    st.markdown("Enter medicine details and upload an image for AI feature extraction.")
    
    name = st.text_input("Medicine Name:").lower().strip()
    medicine_use = st.text_input("Used For (e.g., Headache, Infection):").lower().strip()
    file = st.file_uploader("Upload Image Resource", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Cloud Storage"):
        if file and name and medicine_use:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: 
                f.write(file.getbuffer())
                
            with st.spinner("Executing Pro Analysis..."):
                # Ensure core_logic.py is updated to accept 3 arguments
                success = process_new_medicine(temp_p, name, medicine_use) 
            
            if os.path.exists(temp_p): 
                os.remove(temp_p)
            
            if success: 
                st.session_state.session_uploads.append(name) 
                st.success(f"✅ Record for '{name}' successfully committed.")
            else: 
                st.warning("⚠️ Submission Rejected: Duplicate record or connection error.")
        else:
            st.error("Please fill all fields (Name, Usage, and Image).")

elif page == "Verify My Uploads":
    st.header("📝 Review Current Session Contributions")
    df = fetch_data()
    if not df.empty:
        my_df = df[df['name'].isin(st.session_state.session_uploads)]
        if not my_df.empty:
            st.dataframe(my_df, use_container_width=True)
            edit_id = st.selectbox("Select Record ID for Correction:", my_df['id'].tolist())
            row = my_df[my_df['id'] == edit_id].iloc[0]
            
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
                    st.success("Record updated successfully.")
                    st.rerun()
        else:
            st.info("No active session uploads found.")

elif page == "Dataset Preview (Read-Only)":
    st.header("🔍 Global Dataset Preview")
    df = fetch_data()
    if not df.empty:
        st.write(f"Total Records: {len(df)}")
        st.dataframe(df, use_container_width=True)

elif page == "Master Inventory (Admin)":
    st.header("🔑 Central Inventory Management")
    df = fetch_data()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.divider()
        selected_id = st.number_input("Target Record ID:", min_value=1)
        if selected_id in df['id'].values:
            row = df[df['id'] == selected_id].iloc[0]
            c1, c2, c3 = st.columns(3)
            with c1:
                u_name = st.text_input("Edit Name:", row['name'])
                u_use = st.text_input("Edit Usage:", row.get('medicine_use', ''))
                u_color = st.text_input("Edit Color:", row['color'])
            with c2:
                u_shape = st.text_input("Edit Shape:", row['shape'])
                u_imprint = st.text_area("Edit Imprint:", row['imprint'])
            with c3:
                st.image(row['img_url'], caption="Cloud Master Image", width=250)
            
            if st.button("Apply Administrative Update"):
                supabase.table("inventory").update({
                    "name": u_name, "medicine_use": u_use, "color": u_color, 
                    "shape": u_shape, "imprint": u_imprint
                }).eq("id", selected_id).execute()
                st.success("Master Record Modified.")
                st.rerun()
