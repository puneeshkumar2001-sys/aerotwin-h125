# Add at the VERY TOP of app.py
import os
import sys

__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')


import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
from database import db
from auth import login_required, get_current_user, logout, require_role
from config import Config
from utils.quality_models import predictor

# Page configuration
st.set_page_config(
    page_title="AeroTwin H-125 - Production Intelligence Platform",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #003366 0%, #0066cc 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #0066cc;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .status-operational { background: #d4edda; color: #155724; }
    .status-warning { background: #fff3cd; color: #856404; }
    .status-critical { background: #f8d7da; color: #721c24; }
    .quality-pass { color: #28a745; font-weight: bold; }
    .quality-fail { color: #dc3545; font-weight: bold; }
    .quality-warning { color: #ffc107; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not login_required():
    st.stop()

# Get current user
user = get_current_user()
is_admin = user['role'] == 'admin'
is_supervisor = user['role'] in ['admin', 'supervisor']
is_operator = user['role'] in ['admin', 'supervisor', 'operator']

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/5/58/Tata_Advanced_Systems_Logo.svg/2560px-Tata_Advanced_Systems_Logo.svg.png", 
             width=200)
    
    st.markdown(f"""
    ### 👤 Logged in as
    **{user['full_name']}**  
    *{user['role'].title()}*  
    """)
    
    if user.get('station_id'):
        station_name = next((s['name'] for s in Config.STATIONS if s['id'] == user['station_id']), 'Unknown')
        st.markdown(f"**Station:** {station_name}")
    
    if user.get('shift_id'):
        shift = Config.SHIFTS.get(user['shift_id'], {}).get('name', 'Unknown')
        st.markdown(f"**Shift:** {shift}")
    
    st.markdown("---")
    
    # Navigation
    st.markdown("### 📋 Navigation")
    page = st.radio(
        "",
        ["🏭 Production Dashboard", 
         "📦 Unit Tracking", 
         "🔧 Station View",
         "📊 Quality Control",
         "🔮 Predictive Maintenance",
         "📈 Analytics & Reports",
         "⚙️ Administration"] if is_admin else
        ["🏭 Production Dashboard", 
         "📦 Unit Tracking", 
         "🔧 Station View",
         "📊 Quality Control"]
    )
    
    st.markdown("---")
    
    # Facility info
    st.markdown(f"""
    ### 🏭 Facility
    **{Config.FACILITY}**  
    *Airbus H-125 Final Assembly Line*
    
    **Today:** {datetime.now().strftime('%d %B %Y')}  
    **Shift:** {Config.SHIFTS[pd.Timestamp.now().hour // 8 + 1]['name'] if pd.Timestamp.now().hour < 22 else 'Night'}
    """)
    
    if st.button("🚪 Logout", use_container_width=True):
        logout()

# ============================================================================
# PRODUCTION DASHBOARD
# ============================================================================
if "Production Dashboard" in page:
    st.markdown('<div class="main-header"><h1>🚁 AeroTwin H-125 - Production Dashboard</h1><p>Real-time assembly line intelligence for Vemagal facility</p></div>', 
                unsafe_allow_html=True)
    
    # Get dashboard data
    dashboard_data = db.get_production_dashboard_data()
    
    # Top KPI row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        active_units = len(dashboard_data['active_units'])
        st.metric(
            "Active Helicopters",
            active_units,
            delta="+2 since yesterday",
            delta_color="normal"
        )
    
    with col2:
        today_ops = len(dashboard_data['today_production'])
        st.metric(
            "Today's Operations",
            today_ops,
            delta=f"{today_ops - 45} vs target",
            delta_color="normal"
        )
    
    with col3:
        if not dashboard_data['quality_stats'].empty:
            pass_rate = dashboard_data['quality_stats']['pass_rate'].iloc[0]
            st.metric(
                "Quality Pass Rate (7d)",
                f"{pass_rate:.1f}%",
                delta=f"{pass_rate - 98.5:.1f}% vs target",
                delta_color="inverse" if pass_rate < 98.5 else "normal"
            )
    
    with col4:
        # Calculate OEE
        oee = np.random.normal(78, 3)  # Simulated for demo
        st.metric(
            "Overall OEE",
            f"{oee:.1f}%",
            delta=f"{oee - 75:.1f}% vs benchmark",
            delta_color="normal"
        )
    
    with col5:
        next_delivery = datetime.now() + timedelta(days=random.randint(3, 10))
        st.metric(
            "Next Delivery",
            next_delivery.strftime('%d %b'),
            delta=f"{random.randint(2, 8)} days"
        )
    
    # Live assembly line view
    st.subheader("🏭 Live Assembly Line Status")
    
    # Create Gantt chart for active units
    if not dashboard_data['active_units'].empty:
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set3
        
        for idx, unit in dashboard_data['active_units'].iterrows():
            # Get station progress for this unit
            with db.get_connection() as conn:
                progress = pd.read_sql_query('''
                    SELECT s.name as station, 
                           at.start_time,
                           at.end_time,
                           s.target_cycle_time
                    FROM assembly_tracking at
                    JOIN stations s ON at.station_id = s.id
                    WHERE at.unit_id = ?
                    ORDER BY at.start_time
                ''', conn, params=[unit['id']])
            
            if not progress.empty:
                for i, row in progress.iterrows():
                    start = pd.to_datetime(row['start_time'])
                    if pd.isna(row['end_time']):
                        end = datetime.now()
                        opacity = 0.6
                    else:
                        end = pd.to_datetime(row['end_time'])
                        opacity = 0.3
                    
                    fig.add_trace(go.Bar(
                        name=f"{unit['tail_number']} - {row['station']}",
                        x=[(end - start).total_seconds() / 3600],
                        y=[row['station']],
                        base=[start.strftime('%Y-%m-%d %H:%M')],
                        orientation='h',
                        marker=dict(color=colors[idx % len(colors)], opacity=opacity),
                        text=f"{unit['tail_number']}<br>{row['station']}",
                        textposition='inside',
                        hoverinfo='text'
                    ))
        
        fig.update_layout(
            title="Active Production Timeline",
            xaxis_title="Time",
            yaxis_title="Station",
            barmode='overlay',
            height=500,
            showlegend=False,
            hovermode='y unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active production units")
    
    # Station status cards
    st.subheader("🔧 Station Status")
    
    cols = st.columns(4)
    for idx, station in enumerate(Config.STATIONS):
        with cols[idx % 4]:
            # Get station status from database
            station_status = dashboard_data['station_status']
            status_row = station_status[station_status['id'] == station['id']].iloc[0] if not station_status.empty else None
            
            # Determine status color
            if status_row is not None and status_row['active_jobs'] > 0:
                if status_row['avg_cycle_time'] and status_row['avg_cycle_time'] > station['cycle_time'] * 1.2:
                    status_class = "status-critical"
                    status_text = "⚠️ Delayed"
                else:
                    status_class = "status-operational"
                    status_text = "✅ Operating"
            else:
                status_class = "status-warning"
                status_text = "⏸️ Idle"
            
            st.markdown(f"""
            <div style="background: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h4 style="margin: 0;">{station['name']}</h4>
                <p style="margin: 0.5rem 0; font-size: 0.9rem;">
                    <span class="status-badge {status_class}">{status_text}</span>
                </p>
                <p style="margin: 0.5rem 0; font-size: 1.2rem; font-weight: bold;">
                    {status_row['active_jobs'] if status_row is not None else 0} Active
                </p>
                <p style="margin: 0; color: #666;">
                    Cycle: {status_row['avg_cycle_time']:.1f}/{station['cycle_time']}h
                </p>
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# UNIT TRACKING
# ============================================================================
elif "Unit Tracking" in page:
    st.header("📦 Helicopter Unit Tracking")
    
    # Unit selection
    with db.get_connection() as conn:
        units = pd.read_sql_query('''
            SELECT * FROM helicopter_units ORDER BY start_date DESC
        ''', conn)
    
    if not units.empty:
        selected_unit = st.selectbox(
            "Select Helicopter Unit",
            units.apply(lambda x: f"{x['tail_number']} - {x['customer']} ({x['status']})", axis=1)
        )
        
        unit_id = units.iloc[selected_unit]['id']
        
        # Unit details
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            **Tail Number:** {units.iloc[selected_unit]['tail_number']}  
            **Model:** {units.iloc[selected_unit]['model']}  
            **Customer:** {units.iloc[selected_unit]['customer'] or 'Not Assigned'}
            """)
        
        with col2:
            st.markdown(f"""
            **Start Date:** {units.iloc[selected_unit]['start_date']}  
            **Target Completion:** {units.iloc[selected_unit]['target_completion']}  
            **Status:** {units.iloc[selected_unit]['status']}
            """)
        
        with col3:
            if units.iloc[selected_unit]['quality_score']:
                score = units.iloc[selected_unit]['quality_score']
                color = "green" if score >= 98 else "orange" if score >= 95 else "red"
                st.markdown(f"""
                **Quality Score:** <span style="color: {color}; font-weight: bold; font-size: 1.5rem;">{score:.1f}%</span>
                """, unsafe_allow_html=True)
        
        # Assembly progress
        st.subheader("Assembly Progress")
        
        progress_data = pd.read_sql_query('''
            SELECT s.name as station,
                   at.start_time,
                   at.end_time,
                   at.cycle_time_hours,
                   at.defects,
                   at.quality_status,
                   u.full_name as operator
            FROM assembly_tracking at
            JOIN stations s ON at.station_id = s.id
            LEFT JOIN users u ON at.operator_id = u.id
            WHERE at.unit_id = ?
            ORDER BY at.start_time
        ''', conn, params=[unit_id])
        
        if not progress_data.empty:
            # Progress bar
            completed = progress_data['end_time'].notna().sum()
            total = len(progress_data)
            progress = completed / total
            
            st.progress(progress, text=f"Overall Progress: {completed}/{total} stations completed")
            
            # Timeline
            fig = go.Figure()
            
            for idx, row in progress_data.iterrows():
                start = pd.to_datetime(row['start_time'])
                if pd.isna(row['end_time']):
                    end = datetime.now()
                    color = '#ffc107'
                else:
                    end = pd.to_datetime(row['end_time'])
                    color = '#28a745'
                
                fig.add_trace(go.Bar(
                    name=row['station'],
                    x=[(end - start).total_seconds() / 3600],
                    y=[row['station']],
                    base=[start.strftime('%Y-%m-%d %H:%M')],
                    orientation='h',
                    marker=dict(color=color),
                    text=f"Duration: {row['cycle_time_hours']:.1f}h<br>Operator: {row['operator']}",
                    textposition='inside'
                ))
            
            fig.update_layout(
                title="Assembly Timeline",
                xaxis_title="Time",
                yaxis_title="Station",
                barmode='stack',
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Quality checks for this unit
            quality_checks = pd.read_sql_query('''
                SELECT * FROM quality_measurements 
                WHERE unit_id = ?
                ORDER BY measurement_time DESC
                LIMIT 20
            ''', conn, params=[unit_id])
            
            if not quality_checks.empty:
                st.subheader("Recent Quality Checks")
                st.dataframe(quality_checks, use_container_width=True)
        
        # Add production note
        if is_operator:
            with st.form("add_note"):
                note = st.text_area("Add Production Note")
                if st.form_submit_button("Add Note"):
                    db.log_event('NOTE', note, unit_id=unit_id, user_id=user['id'])
                    st.success("Note added")
                    st.rerun()
    
    else:
        st.info("No helicopter units in system")

# ============================================================================
# QUALITY CONTROL
# ============================================================================
elif "Quality Control" in page:
    st.header("📊 Quality Control & Predictive Analytics")
    
    # Quality overview
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Real-time Quality Prediction")
        
        # Get current conditions
        current_conditions = {
            'hour_of_day': datetime.now().hour,
            'day_of_week': datetime.now().weekday(),
            'shift_id': (datetime.now().hour // 8) + 1,
            'operator_experience_months': np.random.randint(6, 60),
            'operator_certification_level': np.random.randint(1, 5),
            'temperature_c': np.random.normal(23, 2),
            'humidity_pct': np.random.normal(45, 5),
            'vibration_level': np.random.exponential(0.3),
            'station_id': 4,  # Current station
            'station_critical': 1,
            'days_since_maintenance': np.random.randint(1, 20),
            'component_age_days': np.random.randint(10, 150),
            'previous_defects': np.random.poisson(0.1),
            'cycle_time_deviation': np.random.normal(0, 1),
            'torque_value': np.random.normal(100, 5),
            'pressure_value': np.random.normal(50, 3)
        }
        
        # Get prediction
        prediction = predictor.predict_quality(current_conditions)
        
        # Gauge chart
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = prediction['quality_score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Predicted Quality Score"},
            delta = {'reference': 95},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 70], 'color': "lightcoral"},
                    {'range': [70, 90], 'color': "lightyellow"},
                    {'range': [90, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 95
                }
            }
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk assessment
        risk_color = "red" if prediction['risk_level'] == "HIGH" else "orange" if prediction['risk_level'] == "MEDIUM" else "green"
        st.markdown(f"""
        <div style="background: white; padding: 1rem; border-radius: 10px; border-left: 4px solid {risk_color};">
            <h4>Risk Assessment: <span style="color: {risk_color};">{prediction['risk_level']}</span></h4>
            <p>Defect Probability: {prediction['defect_probability']:.1%}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Recent Quality Metrics")
        
        # Get recent quality data
        with db.get_connection() as conn:
            quality_trend = pd.read_sql_query('''
                SELECT DATE(measurement_time) as date,
                       AVG(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100 as pass_rate,
                       COUNT(*) as checks
                FROM quality_measurements
                WHERE measurement_time >= DATE('now', '-30 days')
                GROUP BY DATE(measurement_time)
                ORDER BY date
            ''', conn)
        
        if not quality_trend.empty:
            fig = px.line(quality_trend, x='date', y='pass_rate',
                         title="30-Day Quality Trend",
                         labels={'pass_rate': 'Pass Rate (%)', 'date': 'Date'})
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Quality check form
    if is_operator:
        st.subheader("Record Quality Check")
        
        with st.form("quality_check"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                unit_id = st.selectbox(
                    "Helicopter Unit",
                    pd.read_sql_query("SELECT id, tail_number FROM helicopter_units WHERE status='In Production'", db.get_connection())['tail_number']
                )
                station = st.selectbox("Station", [s['name'] for s in Config.STATIONS])
                checkpoint = st.selectbox("Checkpoint", Config.QUALITY_CHECKPOINTS)
            
            with col2:
                parameter = st.text_input("Parameter", "Torque Value")
                value = st.number_input("Measured Value", value=100.0)
                tolerance_min = st.number_input("Min Tolerance", value=90.0)
            
            with col3:
                tolerance_max = st.number_input("Max Tolerance", value=110.0)
                notes = st.text_area("Notes")
            
            if st.form_submit_button("Submit Quality Check"):
                status = "PASS" if tolerance_min <= value <= tolerance_max else "FAIL"
                st.success(f"Check recorded: {status}")
                
                # Log to database
                db.log_event('QUALITY_CHECK', f'{checkpoint}: {parameter} = {value} ({status})',
                            unit_id=unit_id, station_id=station, user_id=user['id'])

# ============================================================================
# PREDICTIVE MAINTENANCE
# ============================================================================
elif "Predictive Maintenance" in page and is_supervisor:
    st.header("🔮 Predictive Maintenance")
    
    # Get maintenance alerts
    alerts = db.get_predictive_maintenance_alerts()
    
    if not alerts.empty:
        st.subheader("⚠️ Critical Alerts")
        
        for idx, alert in alerts.iterrows():
            with st.expander(f"🔴 {alert['station_name']} - Failure Probability: {alert['failure_probability']:.1%}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    **Predicted Failure:** {alert['predicted_failure_date']}  
                    **Estimated Downtime:** {alert['estimated_downtime_hours']} hours  
                    **Recommended Action:** {alert['recommended_action']}
                    """)
                
                with col2:
                    if st.button(f"Acknowledge Alert", key=f"ack_{idx}"):
                        with db.get_connection() as conn:
                            conn.execute('''
                                UPDATE maintenance_predictions SET acknowledged = 1 
                                WHERE id = ?
                            ''', (alert['id'],))
                            conn.commit()
                        st.success("Alert acknowledged")
                        st.rerun()
    else:
        st.success("✅ No critical maintenance alerts")
    
    # Maintenance schedule
    st.subheader("Maintenance Schedule")
    
    with db.get_connection() as conn:
        schedule = pd.read_sql_query('''
            SELECT s.name as station,
                   s.last_maintenance,
                   s.next_maintenance,
                   s.current_status,
                   (julianday(s.next_maintenance) - julianday('now')) as days_until
            FROM stations s
            ORDER BY days_until
        ''', conn)
    
    if not schedule.empty:
        # Color code based on days until maintenance
        def color_days(val):
            if val < 0:
                return 'background: #f8d7da'
            elif val < 7:
                return 'background: #fff3cd'
            else:
                return 'background: #d4edda'
        
        styled_schedule = schedule.style.applymap(color_days, subset=['days_until'])
        st.dataframe(styled_schedule, use_container_width=True)

# ============================================================================
# ADMINISTRATION
# ============================================================================
elif "Administration" in page and is_admin:
    st.header("⚙️ System Administration")
    
    tab1, tab2, tab3 = st.tabs(["Users", "System Logs", "Database"])
    
    with tab1:
        st.subheader("User Management")
        
        # List users
        with db.get_connection() as conn:
            users = pd.read_sql_query('''
                SELECT id, username, full_name, role, station_id, shift_id, is_active, last_login
                FROM users
            ''', conn)
        
        st.dataframe(users, use_container_width=True)
        
        # Add user form
        with st.expander("Add New User"):
            with st.form("new_user"):
                col1, col2 = st.columns(2)
                
                with col1:
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    full_name = st.text_input("Full Name")
                
                with col2:
                    email = st.text_input("Email")
                    role = st.selectbox("Role", ['admin', 'supervisor', 'operator', 'viewer'])
                    station_id = st.selectbox("Station", [s['id'] for s in Config.STATIONS])
                    shift_id = st.selectbox("Shift", [1, 2, 3])
                
                if st.form_submit_button("Create User"):
                    from auth import hash_password
                    with db.get_connection() as conn:
                        conn.execute('''
                            INSERT INTO users (username, password_hash, full_name, email, role, station_id, shift_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (username, hash_password(password), full_name, email, role, station_id, shift_id))
                        conn.commit()
                    st.success(f"User {username} created")
    
    with tab2:
        st.subheader("System Logs")
        
        with db.get_connection() as conn:
            logs = pd.read_sql_query('''
                SELECT timestamp, event_type, description, user_id
                FROM production_logs
                ORDER BY timestamp DESC
                LIMIT 100
            ''', conn)
        
        st.dataframe(logs, use_container_width=True)
    
    with tab3:
        st.subheader("Database Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export Database", use_container_width=True):
                # Create backup
                import shutil
                from datetime import datetime
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copyfile(Config.DATABASE_PATH, f"data/{backup_name}")
                st.success(f"Database backed up as {backup_name}")
        
        with col2:
            if st.button("Generate Test Data", use_container_width=True):
                # Generate sample data for demonstration
                for i in range(5):
                    unit_id = db.add_helicopter_unit(f"H-125-{100+i}", f"Customer {i}")
                    
                    # Add some assembly tracking
                    for station in Config.STATIONS[:4]:
                        with db.get_connection() as conn:
                            conn.execute('''
                                INSERT INTO assembly_tracking 
                                (unit_id, station_id, start_time, cycle_time_hours, defects)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (unit_id, station['id'], 
                                  datetime.now() - timedelta(days=random.randint(1, 10)),
                                  random.uniform(station['cycle_time'] * 0.9, station['cycle_time'] * 1.2),
                                  random.randint(0, 2)))
                            conn.commit()
                    
                    # Add quality measurements
                    for _ in range(10):
                        db.record_quality_check(
                            unit_id, 
                            random.randint(1, 4),
                            random.choice(Config.QUALITY_CHECKPOINTS),
                            "Torque",
                            random.uniform(95, 105),
                            90, 110
                        )
                
                st.success("Test data generated")

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #666; font-size: 0.875rem;">
    AeroTwin H-125 v{Config.APP_VERSION} | {Config.COMPANY} - {Config.FACILITY}<br>
    © 2026 Tata Advanced Systems Limited. All rights reserved.
</div>
""", unsafe_allow_html=True)
