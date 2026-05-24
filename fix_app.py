import re

with open("eobuwie_app.py", "r") as f:
    content = f.read()

# Fix the Manual Entry Form duplication
content = re.sub(
    r'        w_id = st\.text_input\("Worker ID", help="e\.g\., OT00123"\).*?units = st\.text_input\("Units Processed \(or \'TRAINING\'/\'NB\'\)", help="Number of items processed during the shift\. Enter \'TRAINING\' or \'NB\' for non-standard shifts\."\)',
    '''        w_id = st.text_input("Worker ID (e.g., OT00123)", help="Enter the unique alphanumeric Worker ID (2-15 characters).")
        dept = st.selectbox("Department", ["PICK", "PACK"], help="Select the department. Target: PICK=460, PACK=464.")
        date_val = st.date_input("Date", datetime.date.today(), help="Date of the shift.")
        units = st.text_input("Units Processed (or 'TRAINING'/'NB')", help="Number of items processed during the shift. Enter 'TRAINING' or 'NB' for non-standard shifts.")''',
    content,
    flags=re.DOTALL
)

# Fix the submit_manual logic
content = re.sub(
    r'        submit_manual = st\.form_submit_button\("Add Entry"\).*?            st\.toast\(f"Added \{w_id\} for \{date_val\}", icon="✅"\)',
    '''        submit_manual = st.form_submit_button("Add Entry")
        if submit_manual and w_id:
            if is_valid_worker_id(w_id):
                new_row = pd.DataFrame([{
                    'Worker_ID': w_id.upper(),
                    'Department': dept,
                    'Date': pd.to_datetime(date_val),
                    'Units_per_Shift': units
                }])
                st.session_state.performance_data = pd.concat([st.session_state.performance_data, new_row], ignore_index=True)
                st.toast(f"Added {w_id.upper()} for {date_val}", icon="✅")
            else:
                st.error("Invalid Worker ID format. Use alphanumeric characters (2-15 chars).")''',
    content,
    flags=re.DOTALL
)

# Fix the Danger Zone duplication
content = re.sub(
    r'    with st\.expander\("⚠️ Danger Zone"\):\n        if st\.button\("Clear All Data"\):\n            st\.session_state\.performance_data = pd\.DataFrame\(columns=\[\'Worker_ID\', \'Department\', \'Date\', \'Units_per_Shift\'\]\)\n            st\.toast\("All Data Cleared", icon="🗑️"\)\n            st\.rerun\(\)\n        confirm = st\.checkbox\("I confirm I want to clear all data"\)\n        if st\.button\("Clear All Data", disabled=not confirm\):\n            st\.session_state\.performance_data = pd\.DataFrame\(columns=\[\'Worker_ID\', \'Department\', \'Date\', \'Units_per_Shift\'\]\)\n            st\.toast\("All Data Cleared", icon="🗑️"\)',
    '''    with st.expander("⚠️ Danger Zone"):
        confirm = st.checkbox("I confirm I want to clear all data")
        if st.button("Clear All Data", disabled=not confirm):
            st.session_state.performance_data = pd.DataFrame(columns=['Worker_ID', 'Department', 'Date', 'Units_per_Shift'])
            st.toast("All Data Cleared", icon="🗑️")''',
    content,
    flags=re.DOTALL
)

with open("eobuwie_app.py", "w") as f:
    f.write(content)
