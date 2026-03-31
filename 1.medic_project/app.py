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
        else:
            st.error("Invalid Credentials!")
    st.stop()

# --- Database Operations ---
def get_full_db():
    conn = sqlite3.connect('medic_vault.db')
    try:
        df = pd.read_sql_query("SELECT * FROM inventory", conn)
    except:
        # Table missing check
        df = pd.DataFrame(columns=['id', 'name', 'color', 'shape', 'imprint', 'img_path', 'img_hash'])
    finally:
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

# --- Navigation Sidebar ---
st.sidebar.title(f"👤 {st.session_state.role.upper()}")
if st.sidebar.button("Logout"):
    st.session_state.role = None
    st.rerun()

page = st.sidebar.radio("Navigation", ["Data Ingestion", "Record Verification", "Master Inventory (Admin)"])

# 1. Data Ingestion Page
if page == "Data Ingestion":
    st.header("📤 Medicine Data Ingestion")
    name = st.text_input("Medicine Label (e.g. Dolo 650):").lower().strip()
    file = st.file_uploader("Upload Image Resource", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Database"):
        if file and name:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: 
                f.write(file.getbuffer())
            
            with st.spinner("Analyzing and Hashing..."):
                success = process_new_medicine(temp_p, name)
            
            # Temporary file delete karna zaroori hai
            if os.path.exists(temp_p):
                os.remove(temp_p)
                
            if success:
                st.success(f"✅ Record for '{name}' successfully committed.")
            else:
                st.warning("⚠️ Entry rejected: Duplicate image hash detected.")
        else:
            st.error("Please provide both Name and Image.")

# 2. Record Verification (Contributor View)
elif page == "Record Verification":
    st.header("🔍 Recent Contributions")
    df = get_full_db()
    if not df.empty:
        # Contributor ko sirf latest uploads dikhana
        st.dataframe(df.tail(10), use_container_width=True)
    else:
        st.info("No records found in the database.")

# 3. Master Inventory (Admin Only)
elif page == "Master Inventory (Admin)":
    if st.session_state.role == "admin":
        st.header("🔑 Central Inventory Control")
        df = get_full_db()
        
        st.subheader("Database Overview")
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # --- Manual Feature Engineering Section ---
        st.subheader("🛠️ Manual Feature Engineering")
        if not df.empty:
            selected_id = st.number_input("Enter Record ID to Edit:", 
                                         min_value=int(df['id'].min()), 
                                         max_value=int(df['id'].max()))
            
            if selected_id in df['id'].values:
                target_row = df[df['id'] == selected_id].iloc[0]
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    new_name = st.text_input("Edit Name:", target_row['name'])
                    new_color = st.text_input("Edit Color:", target_row['color'])
                with col2:
                    new_shape = st.text_input("Edit Shape:", target_row['shape'])
                    new_imprint = st.text_area("Edit Imprint Text:", target_row['imprint'])
                with col3:
                    image_path = target_row['img_path']
                    if os.path.exists(image_path):
                        st.image(image_path, caption="Source Image", width=250)
                    else:
                        st.error("🚨 Image file missing!")
                        if st.button("Delete Broken Record"):
                            conn = sqlite3.connect('medic_vault.db')
                            conn.execute("DELETE FROM inventory WHERE id=?", (selected_id,))
                            conn.commit()
                            conn.close()
                            st.rerun()

                if st.button("Apply Changes"):
                    update_record(selected_id, new_name.lower().strip(), new_color, new_shape, new_imprint)
                    st.success(f"Record {selected_id} updated.")
                    st.rerun()
        else:
            st.warning("Inventory is currently empty.")
    else:
        st.error("🚫 Privileged Access Required.")
