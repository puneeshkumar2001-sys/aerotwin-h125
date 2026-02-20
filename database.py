import sqlite3
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from contextlib import contextmanager
from config import Config

class ProductionDatabase:
    def __init__(self, db_path=Config.DATABASE_PATH):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize all tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    role TEXT NOT NULL,
                    station_id INTEGER,
                    shift_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Helicopter units table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS helicopter_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tail_number TEXT UNIQUE,
                    model TEXT DEFAULT 'H-125',
                    customer TEXT,
                    order_date DATE,
                    start_date DATE,
                    target_completion DATE,
                    actual_completion DATE,
                    status TEXT DEFAULT 'In Production',
                    quality_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Assembly tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assembly_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_id INTEGER,
                    station_id INTEGER,
                    operator_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    cycle_time_hours FLOAT,
                    defects INTEGER DEFAULT 0,
                    rework_hours FLOAT DEFAULT 0,
                    quality_checkpoint TEXT,
                    quality_status TEXT,
                    notes TEXT,
                    FOREIGN KEY (unit_id) REFERENCES helicopter_units (id),
                    FOREIGN KEY (station_id) REFERENCES stations (id),
                    FOREIGN KEY (operator_id) REFERENCES users (id)
                )
            ''')
            
            # Stations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    critical BOOLEAN,
                    target_cycle_time FLOAT,
                    current_status TEXT DEFAULT 'Operational',
                    last_maintenance DATE,
                    next_maintenance DATE
                )
            ''')
            
            # Quality measurements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quality_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_id INTEGER,
                    station_id INTEGER,
                    checkpoint TEXT,
                    measurement_time TIMESTAMP,
                    parameter TEXT,
                    value FLOAT,
                    tolerance_min FLOAT,
                    tolerance_max FLOAT,
                    status TEXT,
                    operator_id INTEGER,
                    FOREIGN KEY (unit_id) REFERENCES helicopter_units (id)
                )
            ''')
            
            # Predictive maintenance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id INTEGER,
                    predicted_failure_date DATE,
                    failure_probability FLOAT,
                    recommended_action TEXT,
                    estimated_downtime_hours FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT 0
                )
            ''')
            
            # Sensor data table (for IoT integration)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    station_id INTEGER,
                    sensor_type TEXT,
                    timestamp TIMESTAMP,
                    value FLOAT,
                    unit TEXT,
                    alert_level INTEGER DEFAULT 0
                )
            ''')
            
            # Production logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS production_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    unit_id INTEGER,
                    station_id INTEGER,
                    user_id INTEGER,
                    description TEXT,
                    data TEXT
                )
            ''')
            
            conn.commit()
            
            # Initialize stations if empty
            self.init_stations(conn)
            
            # Create default admin if no users exist
            self.create_default_admin(conn)
    
    def init_stations(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stations")
        if cursor.fetchone()[0] == 0:
            for station in Config.STATIONS:
                cursor.execute('''
                    INSERT INTO stations (id, name, critical, target_cycle_time, current_status, last_maintenance, next_maintenance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    station["id"], 
                    station["name"], 
                    station["critical"],
                    station["cycle_time"],
                    "Operational",
                    datetime.now().date(),
                    (datetime.now() + timedelta(days=30)).date()
                ))
            conn.commit()
    
    def create_default_admin(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # Default password: admin123 (change immediately)
            from auth import hash_password
            cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', hash_password('admin123'), 'System Administrator', 'admin', 1))
            conn.commit()
    
    def log_event(self, event_type, description, unit_id=None, station_id=None, user_id=None, data=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO production_logs (event_type, description, unit_id, station_id, user_id, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (event_type, description, unit_id, station_id, user_id, json.dumps(data) if data else None))
            conn.commit()
    
    def get_production_dashboard_data(self):
        """Get all data needed for main dashboard"""
        with self.get_connection() as conn:
            # Active units
            active_units = pd.read_sql_query('''
                SELECT * FROM helicopter_units 
                WHERE status = 'In Production' 
                ORDER BY start_date
            ''', conn)
            
            # Today's production
            today = datetime.now().date()
            today_production = pd.read_sql_query('''
                SELECT at.*, hu.tail_number, s.name as station_name, u.full_name as operator_name
                FROM assembly_tracking at
                JOIN helicopter_units hu ON at.unit_id = hu.id
                JOIN stations s ON at.station_id = s.id
                LEFT JOIN users u ON at.operator_id = u.id
                WHERE DATE(at.start_time) = ?
                ORDER BY at.start_time DESC
            ''', conn, params=[today.isoformat()])
            
            # Quality metrics
            quality_stats = pd.read_sql_query('''
                SELECT 
                    AVG(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) * 100 as pass_rate,
                    COUNT(*) as total_checks,
                    COUNT(DISTINCT unit_id) as units_tested
                FROM quality_measurements
                WHERE DATE(measurement_time) >= DATE('now', '-7 days')
            ''', conn)
            
            # Station status
            station_status = pd.read_sql_query('''
                SELECT s.*, 
                       COUNT(at.id) as active_jobs,
                       AVG(at.cycle_time_hours) as avg_cycle_time
                FROM stations s
                LEFT JOIN assembly_tracking at ON s.id = at.station_id 
                    AND at.end_time IS NULL
                GROUP BY s.id
            ''', conn)
            
            return {
                'active_units': active_units,
                'today_production': today_production,
                'quality_stats': quality_stats,
                'station_status': station_status
            }
    
    def add_helicopter_unit(self, tail_number, customer=None):
        """Add new helicopter to production"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            start_date = datetime.now().date()
            target_completion = start_date + timedelta(days=30)  # 30 days target
            
            cursor.execute('''
                INSERT INTO helicopter_units (tail_number, customer, start_date, target_completion, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (tail_number, customer, start_date, target_completion, 'In Production'))
            
            unit_id = cursor.lastrowid
            conn.commit()
            
            self.log_event('NEW_UNIT', f'New helicopter {tail_number} added', unit_id=unit_id)
            return unit_id
    
    def record_quality_check(self, unit_id, station_id, checkpoint, parameter, value, tolerance_min, tolerance_max):
        """Record a quality measurement"""
        status = 'PASS' if tolerance_min <= value <= tolerance_max else 'FAIL'
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO quality_measurements 
                (unit_id, station_id, checkpoint, measurement_time, parameter, value, tolerance_min, tolerance_max, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (unit_id, station_id, checkpoint, datetime.now(), parameter, value, tolerance_min, tolerance_max, status))
            
            conn.commit()
            
            if status == 'FAIL':
                self.log_event('QUALITY_FAIL', f'Quality check failed at {checkpoint}: {parameter}', 
                              unit_id=unit_id, station_id=station_id)
            
            return status
    
    def get_predictive_maintenance_alerts(self):
        """Get active maintenance predictions"""
        with self.get_connection() as conn:
            alerts = pd.read_sql_query('''
                SELECT mp.*, s.name as station_name
                FROM maintenance_predictions mp
                JOIN stations s ON mp.station_id = s.id
                WHERE mp.acknowledged = 0 
                AND mp.predicted_failure_date <= DATE('now', '+7 days')
                ORDER BY mp.failure_probability DESC
            ''', conn)
            return alerts

# Initialize global database instance
db = ProductionDatabase()
