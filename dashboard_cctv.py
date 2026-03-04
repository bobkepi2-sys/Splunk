import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================================
# DASHBOARD CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="CCTV Infrastructure Monitoring",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Professional Styling
st.markdown("""
    <style>
    /* Premium styling for metric cards */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        transition: transform 0.2s ease-in-out, border-color 0.2s ease-in-out;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: #4C96FF;
    }
    [data-testid="stMetricLabel"] > div {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: var(--text-color) !important;
        opacity: 0.8;
    }
    [data-testid="stMetricValue"] > div {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: var(--text-color) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# DOWNTIME PARSING LOGIC 
# ==========================================
def get_downtime_category(val):
    """Converts the string downtime into logical grouping categories"""
    val = str(val).strip().lower()
    
    # 1. Check for basic statuses
    if val in ["-", "nan", "none", "", "online"]: 
        return "Online"
    if "baru" in val: 
        return "< 24 Hours"
    if "gagal" in val: 
        return "Calculation Error"
    
    hours = 0
    try:
        # 2. Clean the string (remove 's' from days and remove commas)
        val = val.replace("days", "day").replace(",", "")
        
        # 3. Separate days and time (e.g., "0 day 00:35:03")
        if "day" in val:
            parts = val.split("day")
            days = int(parts[0].strip())
            hours += days * 24
            time_part = parts[1].strip()
        else:
            time_part = val.strip()
            
        # 4. Extract hours from the time format
        if ":" in time_part:
            h_str = time_part.split(":")[0]
            hours += int(h_str)
            
        # 5. Group into 3 main categories
        if hours < 24: return "< 24 Hours"
        elif hours <= 72: return "1 - 3 Days"
        else: return "> 3 Days"
        
    except Exception:
        return "Unknown Format"

# ==========================================
# DATA LOADING & MERGING FUNCTION
# ==========================================
def load_monitoring_data():
    """Reads the main CSV and merges it with Location data"""
    main_file_path = 'Data_Dashboard_CCTV.csv'
    location_file_path = 'Location.csv'  
    
    if not os.path.exists(main_file_path):
        return None
        
    try:
        # 1. Read the Main Ping Data
        df_main = pd.read_csv(main_file_path)
        df_main = df_main.dropna(subset=['IP Adddress']) 
        
        # Data Sanitization for Main File
        df_main['Site Name'] = df_main['Site Name'].fillna('N/A')
        df_main['Device Type'] = df_main['Device Type'].fillna('Unknown Device')

        # NEW: Process Downtime into Categories
        if 'Tempoh_Downtime' in df_main.columns:
            df_main['Downtime_Category'] = df_main['Tempoh_Downtime'].apply(get_downtime_category)
        else:
            df_main['Downtime_Category'] = "Online"
            
        # NEW (Added for Tab 3): Ensure Incident_Count exists and is numeric
        if 'Incident_Count' not in df_main.columns:
            df_main['Incident_Count'] = 0
        df_main['Incident_Count'] = pd.to_numeric(df_main['Incident_Count'], errors='coerce').fillna(0)

        # 2. Check if the Location File Exists and Merge
        if os.path.exists(location_file_path):
            df_loc = pd.read_csv(location_file_path)
            if 'Premise Name' in df_loc.columns:
                df_loc = df_loc.rename(columns={'Premise Name': 'Site Name'})
            
            df_merged = pd.merge(df_main, df_loc, on='Site Name', how='left')
            df_merged = df_merged.fillna('No Data') 
            return df_merged
            
        else:
            return df_main
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# ==========================================
# CONDITIONAL FORMATTING FUNCTION
# ==========================================
def highlight_offline_rows(row):
    """Highlights the entire row red if the CCTV is Offline"""
    if 'Status_Terkini' in row and row['Status_Terkini'] == 'Offline':
        return ['background-color: rgba(255, 75, 75, 0.15)'] * len(row)
    return [''] * len(row)

# ==========================================
# DASHBOARD UI DESIGN
# ==========================================
def main():
    st.title("📹 Live CCTV Infrastructure Monitoring")
    st.write("Real-time operational status and downtime analytics for networked assets.")
    
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()

    raw_data = load_monitoring_data()

    if raw_data is not None and not raw_data.empty:
        
        # --- 1. SIDEBAR & SMART FILTERS ---
        st.sidebar.header("🔍 Filter Analytics")
        status_filter = st.sidebar.radio("Connection Status:", ["All Assets", "🟢 Online Only", "🔴 Offline Only"])

        # SMART FILTER: Downtime Duration Filter
        st.sidebar.markdown("---")
        st.sidebar.markdown("⏳ **Downtime Analysis**")
        downtime_filter = st.sidebar.selectbox(
            "Select Downtime Duration:",
            ["All Durations", "< 24 Hours", "1 - 3 Days", "> 3 Days"]
        )

        st.sidebar.markdown("---")

        # SMART FILTER: State Selection
        if 'State' in raw_data.columns:
            state_list = ["All States"]
            unique_states = sorted(raw_data[raw_data['State'] != 'No Data']['State'].dropna().unique().tolist())
            state_list.extend(unique_states)
            selected_state = st.sidebar.selectbox("📍 Select State:", state_list)
        else:
            selected_state = "All States"

        # SMART FILTER: Site Selection 
        site_list = ["All Operational Sites"]
        if selected_state != "All States" and 'State' in raw_data.columns:
            available_sites = raw_data[raw_data['State'] == selected_state]['Site Name'].dropna().unique().tolist()
        else:
            available_sites = raw_data['Site Name'].dropna().unique().tolist()
            
        unique_sites = sorted(available_sites)
        site_list.extend(unique_sites)
        selected_site = st.sidebar.selectbox("🏢 Select Project Site:", site_list)

        # --- 2. GLOBAL DATA PROCESSING (FULLY INTEGRATED) ---
        filtered_df = raw_data.copy()
        
        # Apply State Filter
        if 'State' in filtered_df.columns and selected_state != "All States":
            filtered_df = filtered_df[filtered_df['State'] == selected_state]

        # Apply Site Filter
        if selected_site != "All Operational Sites":
            filtered_df = filtered_df[filtered_df['Site Name'] == selected_site]
            
        # Apply Status Filter (Now Global)
        if status_filter == "🟢 Online Only":
            filtered_df = filtered_df[filtered_df['Status_Terkini'] == 'Online']
        elif status_filter == "🔴 Offline Only":
            filtered_df = filtered_df[filtered_df['Status_Terkini'] == 'Offline']

        # Apply Downtime Category Filter (Now Global)
        if downtime_filter != "All Durations" and 'Downtime_Category' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Downtime_Category'] == downtime_filter]

        # The table now uses the globally filtered data directly
        table_display_df = filtered_df.copy()

        # Header Info
        last_update = raw_data['Waktu_Semakan_Terakhir'].iloc[0] if 'Waktu_Semakan_Terakhir' in raw_data.columns else "Unknown"
        with col_info:
            view_text = f"{selected_state} > {selected_site}" if selected_state != "All States" else selected_site
            st.info(f"⏱️ **Last System Synchronization:** {last_update} | **Current View:** {view_text}")

        # --- 3. KEY PERFORMANCE INDICATORS (KPI) ---
        # The KPIs now count based on the heavily filtered 'filtered_df'
        total_assets = len(filtered_df)
        online_assets = len(filtered_df[filtered_df['Status_Terkini'] == 'Online'])
        offline_assets = len(filtered_df[filtered_df['Status_Terkini'] == 'Offline'])
        uptime_ratio = (online_assets / total_assets) * 100 if total_assets > 0 else 0
        total_sites = filtered_df['Site Name'].nunique()
        offline_sites = filtered_df[filtered_df['Status_Terkini'] == 'Offline']['Site Name'].nunique()
        
        st.subheader("📈 Executive Summary")
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Total Assets", total_assets)
        
        site_delta = f"- {offline_sites} Site(s) Affected" if offline_sites > 0 else "All Sites Normal"
        site_color = "inverse" if offline_sites > 0 else "normal"
        kpi2.metric("🏢 Operational Sites", total_sites, delta=site_delta, delta_color=site_color)
        
        kpi3.metric("🟢 Online Status", online_assets, delta="Operational", delta_color="normal")
        
        offline_delta = "- Action Required" if offline_assets > 0 else "All Clear"
        offline_color = "normal" if offline_assets > 0 else "off"
        kpi4.metric("🔴 Offline Status", offline_assets, delta=offline_delta, delta_color=offline_color)
        
        kpi5.metric("⚡ Uptime Availability", f"{uptime_ratio:.2f}%")

        st.markdown("---")

        # ==========================================
        # 🆕 TABS & VISUAL CHARTS IMPLEMENTATION
        # ==========================================
        # TAB 3 DITAMBAH DI SINI
        tab1, tab2, tab3 = st.tabs([
            "📊 Analytics Overview (Charts)", 
            "📋 Detailed Inventory (Highlighted)",
            "📉 Stability Analysis (Incident Count)"
        ])

        # ---> CONTENT FOR TAB 1 (CHARTS)
        with tab1:
            st.markdown(f"#### Distribution Analysis")
            group_col1, group_col2 = st.columns(2)

            # Important: If filtered_df is empty, cross-tab will fail. 
            # We add a check to ensure we only draw charts if there is data.
            if total_assets > 0:
                with group_col1:
                    st.markdown("**Device Type Breakdown**")
                    device_cross = pd.crosstab(filtered_df['Device Type'], filtered_df['Status_Terkini'])
                    for status in ['Online', 'Offline']:
                        if status not in device_cross.columns:
                            device_cross[status] = 0
                    
                    device_cross['Total'] = device_cross['Online'] + device_cross['Offline']
                    device_cross = device_cross.sort_values(by='Offline', ascending=False)
                    
                    try:
                        st.bar_chart(device_cross[['Online', 'Offline']], color=["#28a745", "#dc3545"], height=300)
                    except TypeError:
                        st.bar_chart(device_cross[['Online', 'Offline']], height=300)

                    with st.expander("👁️ View Exact Numbers (Device Type)"):
                        st.dataframe(device_cross[['Total', 'Online', 'Offline']], use_container_width=True)

                with group_col2:
                    st.markdown("**Site Performance Summary**")
                    site_cross = pd.crosstab(filtered_df['Site Name'], filtered_df['Status_Terkini'])
                    for status in ['Online', 'Offline']:
                        if status not in site_cross.columns:
                            site_cross[status] = 0
                            
                    site_cross['Total'] = site_cross['Online'] + site_cross['Offline']
                    site_cross = site_cross.sort_values(by='Offline', ascending=False)
                    
                    try:
                        st.bar_chart(site_cross[['Online', 'Offline']], color=["#28a745", "#dc3545"], height=300)
                    except TypeError:
                        st.bar_chart(site_cross[['Online', 'Offline']], height=300)

                    with st.expander("👁️ View Exact Numbers (Site Name)"):
                        st.dataframe(site_cross[['Total', 'Online', 'Offline']], use_container_width=True)
            else:
                st.warning("No data available for the selected filters. Please adjust your criteria.")

        # ---> CONTENT FOR TAB 2 (CONDITIONAL FORMATTING)
        with tab2:
            st.markdown("#### Complete Asset Status Table")
            
            if total_assets > 0:
                # Export Option
                csv_data = table_display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Filtered Data to CSV",
                    data=csv_data,
                    file_name=f"CCTV_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv',
                )
                
                # Apply Conditional Formatting (Highlight Offline rows in Red)
                styled_dataframe = table_display_df.style.apply(highlight_offline_rows, axis=1)
                
                # Render the styled dataframe
                st.dataframe(styled_dataframe, use_container_width=True, hide_index=True)
            else:
                st.info("The table is empty because no CCTV assets match your current filter settings.")

        # ---> CONTENT FOR TAB 3 (STABILITY ANALYSIS / INCIDENT COUNT)
        with tab3:
            st.markdown("#### 📉 Unstable Device Analysis (High Failure Rate)")
            st.markdown("This tab displays devices that frequently disconnect and reconnect (flapping).")
            
            if total_assets > 0:
                # Filter for devices with incidents (Incident_Count > 0)
                df_faulty = table_display_df[table_display_df['Incident_Count'] > 0].sort_values(by='Incident_Count', ascending=False)
                
                if not df_faulty.empty:
                    top_faulty = df_faulty.head(10) # Ambil top 10 sahaja
                    
                    col_chart, col_data = st.columns([2, 1])
                    with col_chart:
                        st.markdown("**Top 10 Devices by Incident Count**")
                        # Sediakan data untuk st.bar_chart
                        chart_data = top_faulty.set_index('Device Name')[['Incident_Count']]
                        st.bar_chart(chart_data, color="#ff4b4b", height=350)
                        
                    with col_data:
                        st.markdown("**Faulty Devices Data**")
                        st.dataframe(
                            top_faulty[['Device Name', 'IP Adddress', 'Incident_Count']], 
                            hide_index=True,
                            use_container_width=True
                        )
                        
                    st.info("💡 **Tip:** Devices with high 'Incident Count' but short 'Downtime' usually indicate unstable physical connections, faulty cables, or PoE power issues.")
                else:
                    st.success("✅ Excellent! No devices have repetitive failures (Incident Count = 0) based on current filters.")
            else:
                st.warning("No data available for the selected filters.")

    else:
        st.error("⚠️ Data Source Unavailable. Please ensure the Ping Engine is running and 'Data_Dashboard_CCTV.csv' is accessible.")

if __name__ == "__main__":
    main()