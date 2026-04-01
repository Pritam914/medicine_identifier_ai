import streamlit as st
import pandas as pd
import os
from core_logic import process_new_medicine, supabase

# --- 1. Page Configuration ---
st.set_page_config(page_title="Medic-Claimer AI Dashboard", layout="wide")

# --- 2. Session State Management ---
# Ye list current user ke upload kiye hue names ko track karegi (Session-based)
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

# --- 4. Robust Data Fetching ---
def fetch_data():
    try:
        # Latest data fetch kar rahe hain taaki multiple admins ko synced data dikhe
        response = supabase.table("inventory").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Data Retrieval Error: {e}")
        return pd.DataFrame()

# --- 5. Navigation Sidebar ---
st.sidebar.title(f"👤 Account: {st.session_state.role.upper()}")
if st.sidebar.button("Logout"):
    # Resetting everything for next user
    st.session_state.role = None
    st.session_state.session_uploads = []
    st.rerun()

# Role-based menu allocation
if st.session_state.role == "admin":
    menu = ["Data Ingestion", "Master Inventory (Admin)"]
else:
    menu = ["Data Ingestion", "Verify My Uploads", "Dataset Preview (Read-Only)"]

page = st.sidebar.radio("Navigation Menu", menu)

# --- 6. Page Logic ---

if page == "Data Ingestion":
    st.header("📤 Advanced Medicine Data Ingestion")
    st.info("System is active for multiple contributors. Your entries are tracked for this session.")
    
    # Input management
    name = st.text_input("Medicine Name:").lower().strip()
    medicine_use = st.text_input("Used For (e.g., Headache, Infection):").lower().strip()
    file = st.file_uploader("Upload Image Resource", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Cloud Storage"):
        if file and name and medicine_use:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: 
                f.write(file.getbuffer())
                
            with st.spinner("Executing AI Analysis..."):
                success = process_new_medicine(temp_p, name, medicine_use) 
            
            if os.path.exists(temp_p): 
                os.remove(temp_p)
            
            if success: 
                # This ensures the current user can see their own additions in 'Verify' tab
                st.session_state.session_uploads.append(name) 
                st.success(f"✅ Record for '{name}' committed. Go to 'Verify My Uploads' to check.")
            else: 
                st.warning("⚠️ Submission Rejected: This medicine might already exist.")
        else:
            st.error("Missing Fields: Name, Usage, and Image are mandatory.")

elif page == "Verify My Uploads":
    st.header("📝 Review Your Recent Contributions")
    df = fetch_data()
    if not df.empty:
        # FILTER: Sirf wahi dikhao jo IS session mein upload hua hai
        my_df = df[df['name'].isin(st.session_state.session_uploads)]
        if not my_df.empty:
            st.dataframe(my_df, use_container_width=True)
            edit_id = st.selectbox("Select Record ID for Correction:", my_df['id'].tolist())
            row = my_df[my_df['id'] == edit_id].iloc[0]
            
            with st.form("correction_form"):
                c1, c2, c3 = st.columns([1,1,1.5])
                with c1:
                    u_color = st.text_input("Corrected Color:", row['color'])
                    u_shape = st.text_input("Corrected Shape:", row['shape'])
                with c2:
                    u_imprint = st.text_area("Corrected Imprint:", row['imprint'])
                with c3:
                    st.image(row['img_url'], caption="Reference Image", use_container_width=True)
                
                if st.form_submit_button("Update My Record"):
                    supabase.table("inventory").update({
                        "color": u_color, "shape": u_shape, "imprint": u_imprint
                    }).eq("id", edit_id).execute()
                    st.success("Changes saved successfully!")
                    st.rerun()
        else:
            st.info("No records found for this session. Start by adding data in 'Data Ingestion'.")

elif page == "Dataset Preview (Read-Only)":
    st.header("🔍 Global Dataset Preview")
    st.caption("Live feed of all contributions (View Only)")
    df = fetch_data()
    if not df.empty:
        st.write(f"📊 Global Count: {len(df)} medicines collected")
        st.dataframe(df, use_container_width=True)

elif page == "Master Inventory (Admin)":
    # Double Security: Sirf admin hi is page ko access kare
    if st.session_state.role == "admin":
        st.header("🔑 Central Inventory Management")
        df = fetch_data()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.divider()
            
            selected_id = st.number_input("Target Record ID for Admin Action:", min_value=1)
            if selected_id in df['id'].values:
                row = df[df['id'] == selected_id].iloc[0]
                c1, c2, c3 = st.columns([1,1,1.5])
                with c1:
                    u_name = st.text_input("Edit Name:", row['name'])
                    u_use = st.text_input("Edit Usage:", row.get('medicine_use', ''))
                with c2:
                    u_color = st.text_input("Edit Color:", row['color'])
                    u_shape = st.text_input("Edit Shape:", row['shape'])
                    u_imprint = st.text_area("Edit Imprint:", row['imprint'])
                with c3:
                    st.image(row['img_url'], caption="Master Reference", use_container_width=True)
                
                if st.button("Apply Administrative Update"):
                    supabase.table("inventory").update({
                        "name": u_name, "medicine_use": u_use, "color": u_color, 
                        "shape": u_shape, "imprint": u_imprint
                    }).eq("id", selected_id).execute()
                    st.success(f"Record {selected_id} modified globally.")
                    st.rerun()
    else:
        st.error("Access Denied: Admin privileges required.")
