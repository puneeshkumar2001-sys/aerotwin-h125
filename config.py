import os
from datetime import timedelta

class Config:
    # Application settings
    APP_NAME = "AeroTwin H-125"
    APP_VERSION = "1.0.0"
    COMPANY = "Tata Advanced Systems Limited"
    FACILITY = "Vemagal, Karnataka"
    
    # Database
    DATABASE_PATH = "data/production.db"
    
    # Security
    SESSION_TIMEOUT = timedelta(hours=8)
    MAX_LOGIN_ATTEMPTS = 3
    
    # Production targets
    TARGET_MONTHLY_PRODUCTION = 4  # helicopters per month
    TARGET_QUALITY_SCORE = 98.5  # percentage
    TARGET_CYCLE_TIME = 240  # hours per helicopter
    
    # Shift timings
    SHIFTS = {
        1: {"name": "Morning", "start": "06:00", "end": "14:00"},
        2: {"name": "Afternoon", "start": "14:00", "end": "22:00"},
        3: {"name": "Night", "start": "22:00", "end": "06:00"}
    }
    
    # Assembly stations in sequence
    STATIONS = [
        {"id": 1, "name": "Fuselage Assembly", "critical": True, "cycle_time": 48},
        {"id": 2, "name": "Main Rotor Installation", "critical": True, "cycle_time": 36},
        {"id": 3, "name": "Tail Boom Assembly", "critical": False, "cycle_time": 24},
        {"id": 4, "name": "Avionics & Systems", "critical": True, "cycle_time": 40},
        {"id": 5, "name": "Engine Integration", "critical": True, "cycle_time": 56},
        {"id": 6, "name": "Landing Gear", "critical": False, "cycle_time": 32},
        {"id": 7, "name": "Final Assembly", "critical": True, "cycle_time": 48},
        {"id": 8, "name": "Quality Testing", "critical": True, "cycle_time": 72}
    ]
    
    # Quality checkpoints
    QUALITY_CHECKPOINTS = [
        "Visual Inspection",
        "Torque Verification",
        "Electrical Continuity",
        "Hydraulic Pressure",
        "Vibration Analysis",
        "Functional Test",
        "Flight Readiness Review"
    ]
