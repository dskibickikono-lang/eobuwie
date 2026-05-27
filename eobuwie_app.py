import streamlit as st
import pandas as pd
import numpy as np
import datetime
import re

# --- CONFIG & CONSTANTS ---
st.set_page_config(page_title="MODIVO Logistics Performance", layout="wide", initial_sidebar_state="expanded")

PICK_TARGET = 460
PACK_TARGET = 464

# --- UI STYLING (Dark Mode & Glassmorphism) ---
st.html("""
    <style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .stDataFrame {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        padding: 10px;
    }
    h1, h2, h3 {
        color: #e2e8f0;
        font-weight: 600;
    }
    </style>
""")

# --- MOCK DATA GENERATOR ---
def generate_mock_data():
    np.random.seed(42)
    workers = [f"OT{str(i).zfill(5)}" for i in range(1, 61)]
    depts = ['PICK'] * 30 + ['PACK'] * 30

    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(21)]

    data = []
    for w_idx, w in enumerate(workers):
        dept = depts[w_idx]
        target = PICK_TARGET if dept == 'PICK' else PACK_TARGET
        base_efficiency = np.random.uniform(0.35, 1.05)

        for d in dates:
            if np.random.random() > 0.8:
                continue
            efficiency = base_efficiency + np.random.uniform(-0.1, 0.1)
            units = int(target * efficiency)
            if np.random.random() > 0.95:
                units = np.random.choice(["TRAINING", "NB", "", None])
            data.append([w, dept, pd.to_datetime(d), units])

    return pd.DataFrame(data, columns=['Worker_ID', 'Department', 'Date', 'Units_per_Shift'])

# --- STATE MANAGEMENT ---
if 'performance_data' not in st.session_state:
    st.session_state.performance_data = generate_mock_data()

# --- SECURITY & VALIDATION ---
def is_valid_worker_id(w_id):
    if not isinstance(w_id, str) or not w_id:
        return False
    w_id_upper = w_id.upper()
    if w_id_upper in ["NAN", "NONE"]:
        return False
    return bool(re.match(r"^[A-Z0-9]{2,15}$", w_id_upper))

# --- DATA CLEANING & AGGREGATION ---
def clean_and_aggregate_data(df):
    df_clean = df.copy()
    df_clean['Units_per_Shift'] = pd.to_numeric(df_clean['Units_per_Shift'], errors='coerce')
    df_clean = df_clean.dropna(subset=['Units_per_Shift', 'Date'])
    df_clean['Date'] = pd.to_datetime(df_clean['Date'])
    df_clean['Week'] = df_clean['Date'].dt.isocalendar().week.apply(lambda x: f"w{x}")
    weekly_avg = df_clean.groupby(['Worker_ID', 'Department', 'Week'])['Units_per_Shift'].mean().reset_index()
    return weekly_avg

# --- BUSINESS LOGIC & FORMATTING ---
def get_color_status(val):
    if pd.isna(val) or isinstance(val, str):
        return ''
    if val >= 0.94:
        return 'background-color: #064e3b; color: #a7f3d0; font-weight: bold;'
    elif val >= 0.80:
        return 'background-color: #059669; color: #ffffff; font-weight: bold;'
    elif val >= 0.50:
        return 'background-color: #b45309; color: #fef3c7; font-weight: bold;'
    else:
        return 'background-color: #7f1d1d; color: #fecaca; font-weight: bold;'

def format_trend(val):
    if pd.isna(val): return '⚪'
    if val >= 0.05: return f'🟢 +{val:.1%}'
    elif val <= -0.05: return f'🔴 {val:.1%}'
    return f'⚪ {val:.1%}'

def process_department_data(df, dept, target):
    df_dept = df[df['Department'] == dept].copy()
    if df_dept.empty:
        return pd.DataFrame(), []

    df_dept['%_of_Target'] = df_dept['Units_per_Shift'] / target
    pivot_pct = df_dept.pivot(index='Worker_ID', columns='Week', values='%_of_Target').reset_index()
    weeks = sorted([col for col in pivot_pct.columns if col != 'Worker_ID'])

    if len(weeks) >= 2:
        pivot_pct['Trend (W-o-W)'] = pivot_pct[weeks[-1]] - pivot_pct[weeks[-2]]
    else:
        pivot_pct['Trend (W-o-W)'] = 0.0

    pivot_pct['Avg Efficiency'] = pivot_pct[weeks].mean(axis=1)

    if weeks:
        pivot_pct = pivot_pct.sort_values(by=weeks[-1], ascending=True).reset_index(drop=True)

    return pivot_pct, weeks

# --- MAIN APP ---
st.title("📦 MODIVO Warehouse Performance Dashboard")
st.markdown("Automated Shift Leader Tracking: **PICK & PACK**")

# Sidebar
with st.sidebar:
    st.header("📥 Data Input")

    # 1. Manual Entry Form
    with st.form("manual_entry_form", clear_on_submit=True):
        st.subheader("Manual Daily Entry")
        w_id = st.text_input("Worker ID (e.g., OT00123)", help="Enter the unique alphanumeric Worker ID (2-15 characters).")
        dept = st.selectbox("Department", ["PICK", "PACK"], help="Select the department. Target: PICK=460, PACK=464.")
        date_val = st.date_input("Date", datetime.date.today(), help="Date of the shift.")
        units = st.text_input("Units Processed (or 'TRAINING'/'NB')", help="Number of items processed during the shift.")

        submit_manual = st.form_submit_button("Add Entry")
        if submit_manual and w_id:
            if is_valid_worker_id(w_id):
                new_row = pd.DataFrame([{
                    'Worker_ID': w_id.upper(),
                    'Department': dept,
                    'Date': pd.to_datetime(date_val),
                    'Units_per_Shift': units
                }])
                st.session_state.performance_data = pd.concat([st.session_state.performance_data, new_row], ignore_index=True)
                st.success(f"Added {w_id.upper()} for {date_val}")
                st.rerun()
            else:
                st.error("Invalid Worker ID format. Use alphanumeric characters (2-15 chars).")

    st.markdown("---")

    # 2. Bulk Upload (Wide Format Parser)
    st.subheader("Bulk Upload (Wide Format)")
    with st.form("upload_form", clear_on_submit=True):
        upload_dept = st.selectbox("Department (if missing in file)", ["PICK", "PACK"])
        uploaded_file = st.file_uploader("Upload Daily Report (CSV/Excel)", type=['csv', 'xlsx'])
        submit_upload = st.form_submit_button("Process File")

        if submit_upload and uploaded_file:
            with st.status("Processing Daily Report...", expanded=True) as status:
                try:
                    if uploaded_file.size > 5 * 1024 * 1024:
                        raise ValueError("File exceeds maximum allowed size of 5MB.")

                    if uploaded_file.name.endswith('.csv'):
                        raw_data = pd.read_csv(uploaded_file)
                    else:
                        raw_data = pd.read_excel(uploaded_file, engine='openpyxl')

                    # Identify Worker ID column
                    id_col = None
                    for col in raw_data.columns:
                        if str(col).strip().lower() in ['login', 'worker_id', 'worker id']:
                            id_col = col
                            break

                    if not id_col:
                        status.update(label="Could not find a worker ID column (e.g., 'login', 'Worker_ID').", state="error", expanded=True)
                    else:
                        converted = pd.to_datetime(pd.Series(raw_data.columns).astype(str), errors='coerce', format='mixed')
                        date_cols = raw_data.columns[converted.notna()].tolist()

                        if not date_cols:
                            status.update(label="Could not identify any date columns in the file header.", state="error", expanded=True)
                        else:
                            dept_col = None
                            for col in raw_data.columns:
                                if str(col).strip().lower() == 'department':
                                    dept_col = col
                                    break

                            id_vars = [id_col]
                            if dept_col:
                                id_vars.append(dept_col)

                            melted_data = pd.melt(
                                raw_data,
                                id_vars=id_vars,
                                value_vars=date_cols,
                                var_name='Date',
                                value_name='Units_per_Shift'
                            )

                            melted_data.rename(columns={id_col: 'Worker_ID'}, inplace=True)
                            if dept_col:
                                melted_data.rename(columns={dept_col: 'Department'}, inplace=True)
                            else:
                                melted_data['Department'] = upload_dept

                            melted_data = melted_data[['Worker_ID', 'Department', 'Date', 'Units_per_Shift']]

                            original_count = len(melted_data)
                            melted_data = melted_data.dropna(subset=['Worker_ID'])
                            melted_data = melted_data[melted_data['Worker_ID'].astype(str).apply(is_valid_worker_id)]
                            dropped_count = original_count - len(melted_data)

                            st.session_state.performance_data = pd.concat([st.session_state.performance_data, melted_data], ignore_index=True)

                            if dropped_count > 0:
                                st.warning(f"File processed, but {dropped_count} rows were dropped due to invalid Worker IDs.")

                            status.update(label="Report successfully parsed!", state="complete", expanded=False)
                            st.rerun()

                except Exception as e:
                    status.update(label=f"Error parsing file: {e}", state="error", expanded=True)

    with st.expander("⚠️ Danger Zone"):
        confirm = st.checkbox("I confirm I want to clear all data")
        if st.button("Clear All Data", disabled=not confirm):
            st.session_state.performance_data = pd.DataFrame(columns=['Worker_ID', 'Department', 'Date', 'Units_per_Shift'])
            st.toast("All Data Cleared", icon="🗑️")
            st.rerun()

    st.markdown("---")
    st.markdown("### KPI Thresholds")
    st.markdown("🟩 **>= 94%**: Target Reached")
    st.markdown("🟨 **80% - 93%**: Stable/Onboarded")
    st.markdown("🟧 **50% - 79%**: In Progress")
    st.markdown("🟥 **< 50%**: Critical / Replace")

# Process Data
aggregated_data = clean_and_aggregate_data(st.session_state.performance_data)
pick_data, pick_weeks = process_department_data(aggregated_data, 'PICK', PICK_TARGET)
pack_data, pack_weeks = process_department_data(aggregated_data, 'PACK', PACK_TARGET)

# Top Level Metrics
col1, col2, col3, col4 = st.columns(4)
latest_week = pick_weeks[-1] if pick_weeks else (pack_weeks[-1] if pack_weeks else "N/A")

with col1:
    st.metric("Total Active Workers", len(aggregated_data['Worker_ID'].unique()))
with col2:
    st.metric("Latest Week", latest_week)
with col3:
    pick_critical = len(pick_data[pick_data[latest_week] < 0.50]) if latest_week in pick_data.columns else 0
    st.metric("PICK Critical (<50%)", pick_critical, delta=f"-{pick_critical} Action Req" if pick_critical > 0 else "0", delta_color="inverse")
with col4:
    pack_critical = len(pack_data[pack_data[latest_week] < 0.50]) if latest_week in pack_data.columns else 0
    st.metric("PACK Critical (<50%)", pack_critical, delta=f"-{pack_critical} Action Req" if pack_critical > 0 else "0", delta_color="inverse")

st.markdown("---")

# Tabs for Departments
tab1, tab2 = st.tabs(["🛒 PICK Department (Target: 460)", "📦 PACK Department (Target: 464)"])

def render_dataframe(data, weeks):
    if data.empty:
        st.info("No data available for this department.")
        return

    styled_df = data.style.map(get_color_status, subset=weeks + ['Avg Efficiency']) \
                          .format({w: "{:.1%}" for w in weeks}) \
                          .format({'Avg Efficiency': "{:.1%}"}) \
                          .format({'Trend (W-o-W)': format_trend})

    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        hide_index=True
    )

with tab1:
    st.subheader(f"PICK Performance Heatmap (Sorted by {latest_week} Action Priority)")
    render_dataframe(pick_data, pick_weeks)

with tab2:
    st.subheader(f"PACK Performance Heatmap (Sorted by {latest_week} Action Priority)")
    render_dataframe(pack_data, pack_weeks)
