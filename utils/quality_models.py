import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta

class QualityPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def generate_training_data(self, n_samples=10000):
        """Generate realistic training data based on aerospace manufacturing"""
        np.random.seed(42)
        
        data = pd.DataFrame({
            # Time-based features
            'hour_of_day': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'shift_id': np.random.randint(1, 4, n_samples),
            
            # Operator features
            'operator_experience_months': np.random.randint(1, 120, n_samples),
            'operator_certification_level': np.random.randint(1, 5, n_samples),
            
            # Environmental conditions
            'temperature_c': np.random.normal(23, 3, n_samples),
            'humidity_pct': np.random.normal(45, 10, n_samples),
            'vibration_level': np.random.exponential(0.5, n_samples),
            
            # Station features
            'station_id': np.random.randint(1, 9, n_samples),
            'station_critical': np.random.choice([0, 1], n_samples),
            'days_since_maintenance': np.random.exponential(20, n_samples),
            
            # Component features
            'component_age_days': np.random.exponential(100, n_samples),
            'previous_defects': np.random.poisson(0.2, n_samples),
            
            # Process parameters
            'cycle_time_deviation': np.random.normal(0, 2, n_samples),
            'torque_value': np.random.normal(100, 15, n_samples),
            'pressure_value': np.random.normal(50, 8, n_samples)
        })
        
        # Generate realistic quality score (0-100)
        quality_score = 100
        
        # Subtract based on risk factors
        quality_score -= 5 * (data['operator_experience_months'] < 12).astype(int)
        quality_score -= 3 * (data['operator_certification_level'] < 3).astype(int)
        quality_score -= 2 * ((data['temperature_c'] - 23).abs() > 5).astype(int)
        quality_score -= 2 * ((data['humidity_pct'] - 45).abs() > 15).astype(int)
        quality_score -= 10 * (data['vibration_level'] > 1.5).astype(int)
        quality_score -= 8 * (data['days_since_maintenance'] > 30).astype(int)
        quality_score -= 15 * (data['component_age_days'] > 200).astype(int)
        quality_score -= 5 * data['previous_defects']
        quality_score -= 3 * (data['cycle_time_deviation'].abs() > 3).astype(int)
        
        # Add random noise
        quality_score += np.random.normal(0, 3, n_samples)
        
        # Clip to 0-100 range
        quality_score = np.clip(quality_score, 0, 100)
        
        # Generate defect probability (for classification)
        defect_probability = 1 / (1 + np.exp(-(90 - quality_score) / 10))
        has_defect = np.random.binomial(1, defect_probability)
        
        data['quality_score'] = quality_score
        data['has_defect'] = has_defect
        
        return data
    
    def train(self):
        """Train the quality prediction model"""
        print("Training quality prediction model...")
        
        # Generate training data
        data = self.generate_training_data()
        
        # Prepare features
        feature_columns = [col for col in data.columns if col not in ['quality_score', 'has_defect']]
        X = data[feature_columns]
        y_reg = data['quality_score']
        y_clf = data['has_defect']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train regression model for quality score
        self.reg_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        self.reg_model.fit(X_scaled, y_reg)
        
        # Train classification model for defect prediction
        self.clf_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
        self.clf_model.fit(X_scaled, y_clf)
        
        self.is_trained = True
        self.feature_columns = feature_columns
        
        # Save models
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.reg_model, 'models/quality_regressor.pkl')
        joblib.dump(self.clf_model, 'models/quality_classifier.pkl')
        joblib.dump(self.scaler, 'models/scaler.pkl')
        joblib.dump(self.feature_columns, 'models/feature_columns.pkl')
        
        print("Model training complete!")
        
        # Calculate training accuracy
        train_pred = self.reg_model.predict(X_scaled)
        train_accuracy = np.mean(np.abs(train_pred - y_reg) < 5)  # within 5 points
        print(f"Training accuracy (within ±5): {train_accuracy:.2%}")
        
        return {
            'regression_score': self.reg_model.score(X_scaled, y_reg),
            'feature_importance': dict(zip(feature_columns, self.reg_model.feature_importances_))
        }
    
    def load_models(self):
        """Load pre-trained models"""
        try:
            self.reg_model = joblib.load('models/quality_regressor.pkl')
            self.clf_model = joblib.load('models/quality_classifier.pkl')
            self.scaler = joblib.load('models/scaler.pkl')
            self.feature_columns = joblib.load('models/feature_columns.pkl')
            self.is_trained = True
            return True
        except:
            return False
    
    def predict_quality(self, features):
        """Predict quality score for current conditions"""
        if not self.is_trained:
            if not self.load_models():
                self.train()
        
        # Ensure all required features are present
        input_df = pd.DataFrame([features])
        
        # Add missing features with default values
        for col in self.feature_columns:
            if col not in input_df.columns:
                input_df[col] = 0
        
        # Ensure correct column order
        input_df = input_df[self.feature_columns]
        
        # Scale features
        X_scaled = self.scaler.transform(input_df)
        
        # Predict
        quality_score = self.reg_model.predict(X_scaled)[0]
        defect_probability = self.clf_model.predict_proba(X_scaled)[0, 1]
        
        return {
            'quality_score': round(quality_score, 2),
            'defect_probability': round(defect_probability, 3),
            'risk_level': 'HIGH' if defect_probability > 0.3 else 'MEDIUM' if defect_probability > 0.1 else 'LOW'
        }

# Initialize predictor
predictor = QualityPredictor()
