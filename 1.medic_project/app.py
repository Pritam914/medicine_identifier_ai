import streamlit as st
import pandas as pd
import sqlite3
import os
from core_logic import process_new_medicine 

st.set_page_config(page_title="Medic-Claimer Dataset Manager", layout="wide")

# --- Authentication Logic ---
if "role" not in st.session_state:
    st.session_state.role = None

if st.session_state.role is None:
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

# --- Database Operations ---
def get_full_db():
    conn = sqlite3.connect('medic_vault.db')
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    return df

def update_record(record_id, name, color, shape, imprint):
    conn = sqlite3.connect('medic_vault.db')
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventory 
        SET name=?, color=?, shape=?, imprint=? 
        WHERE id=?""", (name, color, shape, imprint, record_id))
    conn.commit()
    conn.close()

# --- Navigation ---
st.sidebar.title(f"Access Level: {st.session_state.role.upper()}")
page = st.sidebar.radio("Navigation", ["Data Ingestion", "Record Verification", "Master Inventory (Admin)"])

# 1. Data Ingestion Page
if page == "Data Ingestion":
    st.header("Medicine Data Ingestion")
    name = st.text_input("Medicine Label:").lower().strip()
    file = st.file_uploader("Upload Image Resource")
    
    if st.button("Commit to Database"):
        if file and name:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: f.write(file.getbuffer())
            
            success = process_new_medicine(temp_p, name)
            if success:
                st.success(f"Record for '{name}' successfully committed.")
            else:
                st.warning("Entry rejected: Duplicate image hash detected.")

# 2. Record Verification (For Contributors)
elif page == "Record Verification":
    st.header("Recent Contributions Verification")
    st.info("Verification module for current session uploads.")
    # Implement session-based filtering if required

# 3. Master Inventory & Manual Feature Engineering (Admin Only)
elif page == "Master Inventory (Admin)":
    if st.session_state.role == "admin":
        st.header("Central Inventory Control")
        df = get_full_db()
        
        st.subheader("Database Overview")
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # --- Manual Feature Engineering / Data Correction Section ---
        st.subheader("Manual Feature Engineering")
        selected_id = st.number_input("Enter Record ID to Edit:", min_value=int(df['id'].min()) if not df.empty else 0)
        
        if not df.empty and selected_id in df['id'].values:
            target_row = df[df['id'] == selected_id].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                new_name = st.text_input("Edit Name:", target_row['name'])
                new_color = st.text_input("Edit Color:", target_row['color'])
            with col2:
                new_shape = st.text_input("Edit Shape:", target_row['shape'])
                new_imprint = st.text_area("Edit Imprint Text:", target_row['imprint'])
            with col3:
                # Check karo ki file physically exist karti hai ya nahi
                image_path = target_row['img_path']
                if os.path.exists(image_path):
                     st.image(image_path, caption="Source Image", width=200)
                else:
                    st.error("🚨 Image file not found on disk!")
                    st.info(f"Missing Path: {image_path}")
                 # Option to re-link or delete this broken record
                    if st.button("Delete Broken Record"):
                         conn = sqlite3.connect('medic_vault.db')
                         conn.execute("DELETE FROM inventory WHERE id=?", (selected_id,))
                         conn.commit()
                         conn.close()
                         st.rerun()
            if st.button("Apply Changes"):
                update_record(selected_id, new_name.lower().strip(), new_color, new_shape, new_imprint)
                st.success(f"Record {selected_id} updated successfully.")
                st.rerun()
    else:
        st.error("Privileged Access Required.")