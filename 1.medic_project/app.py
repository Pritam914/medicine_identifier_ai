# ... inside Page 1: Data Ingestion ...
if page == "Data Ingestion":
    st.header("📤 Advanced Medicine Data Ingestion")
    
    name = st.text_input("Medicine Name:").lower().strip()
    # NEW: Manual Entry for Usage
    medicine_use = st.text_input("Used For (e.g., Headache, Infection):").lower().strip()
    
    file = st.file_uploader("Upload Image Resource", type=['jpg', 'jpeg', 'png'])
    
    if st.button("Commit to Cloud Storage"):
        if file and name and medicine_use:
            temp_p = f"temp_{file.name}"
            with open(temp_p, "wb") as f: 
                f.write(file.getbuffer())
                
            with st.spinner("Executing Pro Analysis..."):
                success = process_new_medicine(temp_p, name, medicine_use) # Passing usage
            
            if os.path.exists(temp_p): os.remove(temp_p)
            
            if success: 
                st.session_state.session_uploads.append(name) 
                st.success(f"✅ Record for '{name}' successfully committed.")
            else: 
                st.warning("⚠️ Submission Rejected: Duplicate record or connection error.")
        else:
            st.error("Please fill all mandatory fields (Name, Usage, and Image).")

# ... inside Admin Page edit section ...
if selected_id in df['id'].values:
    row = df[df['id'] == selected_id].iloc[0]
    c1, c2, c3 = st.columns(3)
    with c1:
        u_name = st.text_input("Edit Name:", row['name'])
        u_use = st.text_input("Edit Usage:", row.get('medicine_use', 'N/A')) # NEW
        u_color = st.text_input("Edit Color:", row['color'])
    with c2:
        u_shape = st.text_input("Edit Shape:", row['shape'])
        u_imprint = st.text_area("Edit Imprint:", row['imprint'])
    # ... update button update ...
    if st.button("Apply Administrative Update"):
        supabase.table("inventory").update({
            "name": u_name, "medicine_use": u_use, "color": u_color, "shape": u_shape, "imprint": u_imprint
        }).eq("id", selected_id).execute()
        st.success("Master Record Updated.")
        st.rerun()
