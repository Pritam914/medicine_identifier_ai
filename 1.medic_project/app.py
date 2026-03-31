import streamlit as st
import pandas as pd
import os
from core_logic import process_new_medicine, supabase

st.set_page_config(page_title="Medic-Claimer AI Dashboard", layout="wide")

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

# --- Navigation ---
st.sidebar.title(f"👤 {st.session_state.role.upper()}")
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

page = st.sidebar.radio("Navigation", ["Data Ingestion", "Master Inventory (Admin)"])

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
            
            if success: st.success(f"✅ '{name}' stored in Supabase!")
            else: st.warning("⚠️ Duplicate or Error!")

# 2. Master Inventory (Admin Only)
elif page == "Master Inventory (Admin)":
    if st.session_state.role == "admin":
        st.header("🔑 Central Inventory Control")
        
        # Cloud Fetch
        response = supabase.table("inventory").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("🛠️ Manual Feature Engineering")
            selected_id = st.number_input("Enter Record ID to Edit:", min_value=1)
            
            if selected_id in df['id'].values:
                row = df[df['id'] == selected_id].iloc[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    u_name = st.text_input("Edit Name:", row['name'])
                    u_color = st.text_input("Edit Color:", row['color'])
                with col2:
                    u_shape = st.text_input("Edit Shape:", row['shape'])
                    u_imprint = st.text_area("Edit Imprint:", row['imprint'])
                with col3:
                    st.image(row['img_url'], caption="Cloud Resource", width=250)

                if st.button("Update Cloud Record"):
                    supabase.table("inventory").update({
                        "name": u_name, "color": u_color, "shape": u_shape, "imprint": u_imprint
                    }).eq("id", selected_id).execute()
                    st.success("Cloud Data Updated!")
                    st.rerun()
        else:
            st.info("Cloud Database is empty.")
