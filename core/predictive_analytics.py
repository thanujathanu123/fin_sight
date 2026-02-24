import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class PredictiveAnalyticsEngine:
    """Advanced predictive analytics for risk assessment and trend analysis"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.trained = False

    def prepare_time_series_data(self, transactions: List[Dict], days: int = 90) -> pd.DataFrame:
        """Prepare transaction data for time series analysis"""
        if not transactions:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)

        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()

        # Resample to daily frequency
        daily_stats = df.resample('D').agg({
            'id': 'count',  # transaction_count
            'amount': ['sum', 'mean', 'std'],  # amount statistics
            'risk_score': ['mean', 'max', 'std']  # risk statistics
        }).fillna(0)

        # Flatten column names
        daily_stats.columns = ['transaction_count', 'total_amount', 'avg_amount', 'std_amount',
                              'avg_risk', 'max_risk', 'std_risk']

        # Fill missing days with zeros
        date_range = pd.date_range(start=daily_stats.index.min(),
                                 end=daily_stats.index.max(),
                                 freq='D')
        daily_stats = daily_stats.reindex(date_range, fill_value=0)

        return daily_stats

    def train_predictive_models(self, historical_data: pd.DataFrame):
        """Train predictive models on historical data"""
        if historical_data.empty:
            logger.warning("No historical data available for training")
            return

        try:
            # Prepare features for regression models
            features = ['transaction_count', 'total_amount', 'avg_amount', 'std_amount',
                       'avg_risk', 'max_risk', 'std_risk']

            # Create lag features (previous day values)
            for feature in features:
                historical_data[f'{feature}_lag1'] = historical_data[feature].shift(1)
                historical_data[f'{feature}_lag7'] = historical_data[feature].shift(7)

            # Create rolling statistics
            for feature in features:
                historical_data[f'{feature}_rolling_mean_7'] = historical_data[feature].rolling(window=7).mean()
                historical_data[f'{feature}_rolling_std_7'] = historical_data[feature].rolling(window=7).std()

            # Drop rows with NaN values
            historical_data = historical_data.dropna()

            if len(historical_data) < 30:
                logger.warning("Insufficient data for training predictive models")
                return

            # Split features and targets
            feature_cols = [col for col in historical_data.columns if col not in features]
            X = historical_data[feature_cols]
            y_risk = historical_data['avg_risk']
            y_amount = historical_data['total_amount']
            y_count = historical_data['transaction_count']

            # Scale features
            self.scalers['features'] = StandardScaler()
            X_scaled = self.scalers['features'].fit_transform(X)

            # Train risk prediction model
            self.models['risk_predictor'] = RandomForestRegressor(
                n_estimators=100, random_state=42, max_depth=10
            )
            self.models['risk_predictor'].fit(X_scaled, y_risk)

            # Train amount prediction model
            self.models['amount_predictor'] = RandomForestRegressor(
                n_estimators=100, random_state=42, max_depth=10
            )
            self.models['amount_predictor'].fit(X_scaled, y_amount)

            # Train transaction count predictor
            self.models['count_predictor'] = RandomForestRegressor(
                n_estimators=100, random_state=42, max_depth=10
            )
            self.models['count_predictor'].fit(X_scaled, y_count)

            # Train time series models for trend analysis
            self._train_time_series_models(historical_data)

            self.trained = True
            logger.info("Predictive models trained successfully")

        except Exception as e:
            logger.error(f"Error training predictive models: {str(e)}")
            self.trained = False

    def _train_time_series_models(self, data: pd.DataFrame):
        """Train ARIMA models for time series forecasting"""
        try:
            # Risk score time series
            risk_series = data['avg_risk'].dropna()
            if len(risk_series) > 30:
                self.models['risk_arima'] = self._fit_arima_model(risk_series)

            # Transaction count time series
            count_series = data['transaction_count'].dropna()
            if len(count_series) > 30:
                self.models['count_arima'] = self._fit_arima_model(count_series)

            # Amount time series
            amount_series = data['total_amount'].dropna()
            if len(amount_series) > 30:
                self.models['amount_arima'] = self._fit_arima_model(amount_series)

        except Exception as e:
            logger.warning(f"Error training time series models: {str(e)}")

    def _fit_arima_model(self, series: pd.Series) -> ARIMA:
        """Fit ARIMA model with automatic parameter selection"""
        try:
            # Simple ARIMA(1,1,1) for stability
            model = ARIMA(series, order=(1, 1, 1))
            fitted_model = model.fit()
            return fitted_model
        except:
            # Fallback to even simpler model
            try:
                model = ARIMA(series, order=(1, 0, 0))
                fitted_model = model.fit()
                return fitted_model
            except:
                logger.warning("Could not fit ARIMA model")
                return None

    def predict_future_risk(self, current_data: pd.DataFrame, days_ahead: int = 7) -> Dict:
        """Predict future risk scores"""
        if not self.trained:
            return {'error': 'Models not trained'}

        try:
            predictions = {}

            # Use regression model for short-term predictions
            if len(current_data) > 0 and 'risk_predictor' in self.models:
                latest_features = self._prepare_prediction_features(current_data)
                if latest_features is not None:
                    scaled_features = self.scalers['features'].transform(latest_features)
                    risk_pred = self.models['risk_predictor'].predict(scaled_features)[0]
                    predictions['next_day_risk'] = max(0, min(100, risk_pred))

            # Use time series model for trend predictions
            if 'risk_arima' in self.models and self.models['risk_arima'] is not None:
                try:
                    forecast = self.models['risk_arima'].forecast(steps=days_ahead)
                    predictions['risk_trend'] = forecast.tolist()
                except:
                    pass

            return predictions

        except Exception as e:
            logger.error(f"Error predicting future risk: {str(e)}")
            return {'error': str(e)}

    def _prepare_prediction_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """Prepare features for prediction"""
        try:
            if len(data) < 7:
                return None

            latest = data.iloc[-1]
            week_ago = data.iloc[-7] if len(data) >= 7 else data.iloc[0]

            features = []
            base_features = ['transaction_count', 'total_amount', 'avg_amount', 'std_amount',
                           'avg_risk', 'max_risk', 'std_risk']

            # Current values
            for feature in base_features:
                features.append(latest.get(feature, 0))

            # Lag features
            for feature in base_features:
                features.append(week_ago.get(feature, 0))

            # Rolling statistics (simplified)
            for feature in base_features:
                values = data[feature].tail(7)
                features.append(values.mean())
                features.append(values.std())

            return np.array(features).reshape(1, -1)

        except Exception as e:
            logger.error(f"Error preparing prediction features: {str(e)}")
            return None

    def analyze_trends(self, data: pd.DataFrame) -> Dict:
        """Analyze trends and patterns in the data"""
        if data.empty:
            return {'error': 'No data available for trend analysis'}

        try:
            analysis = {}

            # Basic trend analysis
            numeric_cols = ['transaction_count', 'total_amount', 'avg_amount', 'avg_risk', 'max_risk']

            for col in numeric_cols:
                if col in data.columns:
                    series = data[col].dropna()
                    if len(series) > 7:
                        # Calculate trend direction
                        recent = series.tail(7).mean()
                        previous = series.head(len(series) - 7).tail(7).mean() if len(series) > 14 else series.head(len(series) // 2).mean()

                        if previous > 0:
                            change_pct = ((recent - previous) / previous) * 100
                            trend = 'increasing' if change_pct > 5 else 'decreasing' if change_pct < -5 else 'stable'
                            analysis[f'{col}_trend'] = {
                                'direction': trend,
                                'change_percent': round(change_pct, 2),
                                'recent_avg': round(recent, 2),
                                'previous_avg': round(previous, 2)
                            }

            # Seasonal analysis
            if len(data) > 30:
                try:
                    # Analyze daily patterns
                    data['day_of_week'] = data.index.dayofweek
                    data['hour'] = data.index.hour

                    # Risk by day of week
                    risk_by_day = data.groupby('day_of_week')['avg_risk'].mean()
                    analysis['risk_by_day'] = risk_by_day.to_dict()

                    # Transaction volume by day
                    volume_by_day = data.groupby('day_of_week')['transaction_count'].mean()
                    analysis['volume_by_day'] = volume_by_day.to_dict()

                except Exception as e:
                    logger.warning(f"Error in seasonal analysis: {str(e)}")

            # Anomaly detection
            analysis['anomalies'] = self._detect_anomalies(data)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {'error': str(e)}

    def _detect_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """Detect anomalous periods in the data"""
        anomalies = []

        try:
            numeric_cols = ['transaction_count', 'total_amount', 'avg_risk', 'max_risk']

            for col in numeric_cols:
                if col in data.columns:
                    series = data[col].dropna()
                    if len(series) > 14:
                        # Simple anomaly detection using rolling statistics
                        rolling_mean = series.rolling(window=7).mean()
                        rolling_std = series.rolling(window=7).std()

                        # Find values that are 2+ standard deviations from mean
                        threshold = 2.0
                        anomalies_mask = abs(series - rolling_mean) > (threshold * rolling_std)

                        anomalous_dates = series[anomalies_mask].index.tolist()
                        anomalous_values = series[anomalies_mask].values.tolist()

                        for date, value in zip(anomalous_dates, anomalous_values):
                            anomalies.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'metric': col,
                                'value': round(float(value), 2),
                                'expected_range': {
                                    'min': round(float(rolling_mean.loc[date] - threshold * rolling_std.loc[date]), 2),
                                    'max': round(float(rolling_mean.loc[date] + threshold * rolling_std.loc[date]), 2)
                                }
                            })

        except Exception as e:
            logger.warning(f"Error detecting anomalies: {str(e)}")

        return anomalies

    def generate_risk_forecast(self, data: pd.DataFrame, forecast_days: int = 30) -> Dict:
        """Generate comprehensive risk forecast"""
        if not self.trained or data.empty:
            return {'error': 'Insufficient data for forecasting'}

        try:
            forecast = {
                'forecast_period_days': forecast_days,
                'generated_at': datetime.now().isoformat(),
                'predictions': {},
                'confidence_intervals': {},
                'risk_assessment': {}
            }

            # Generate predictions for different time horizons
            for days in [7, 14, 30]:
                if days <= forecast_days:
                    predictions = self.predict_future_risk(data, days)
                    forecast['predictions'][f'{days}_days'] = predictions

            # Risk assessment
            latest_risk = data['avg_risk'].iloc[-1] if not data.empty else 0
            forecast['current_risk_level'] = self._assess_risk_level(latest_risk)

            # Trend analysis
            trends = self.analyze_trends(data)
            forecast['trend_analysis'] = trends

            # Recommendations
            forecast['recommendations'] = self._generate_recommendations(forecast)

            return forecast

        except Exception as e:
            logger.error(f"Error generating risk forecast: {str(e)}")
            return {'error': str(e)}

    def _assess_risk_level(self, risk_score: float) -> Dict:
        """Assess overall risk level"""
        if risk_score >= 70:
            level = 'high'
            description = 'High risk - Immediate attention required'
            color = 'danger'
        elif risk_score >= 40:
            level = 'medium'
            description = 'Medium risk - Monitor closely'
            color = 'warning'
        else:
            level = 'low'
            description = 'Low risk - Normal operations'
            color = 'success'

        return {
            'level': level,
            'description': description,
            'color': color,
            'score': round(risk_score, 1)
        }

    def _generate_recommendations(self, forecast: Dict) -> List[str]:
        """Generate actionable recommendations based on forecast"""
        recommendations = []

        try:
            current_risk = forecast.get('current_risk_level', {})
            trend_analysis = forecast.get('trend_analysis', {})

            if current_risk.get('level') == 'high':
                recommendations.append("High risk level detected - Implement immediate risk mitigation measures")
                recommendations.append("Increase transaction monitoring frequency")
                recommendations.append("Review and update risk thresholds")

            elif current_risk.get('level') == 'medium':
                recommendations.append("Monitor risk trends closely over the next week")
                recommendations.append("Consider adjusting risk parameters if trends continue upward")

            # Check for increasing risk trends
            risk_trend = trend_analysis.get('avg_risk_trend', {})
            if risk_trend.get('direction') == 'increasing':
                recommendations.append(f"Risk scores are trending upward ({risk_trend.get('change_percent', 0):.1f}%) - investigate causes")

            # Check for anomalies
            anomalies = trend_analysis.get('anomalies', [])
            if anomalies:
                recommendations.append(f"Detected {len(anomalies)} anomalous patterns - review recent transactions")

            # Volume trends
            volume_trend = trend_analysis.get('transaction_count_trend', {})
            if volume_trend.get('direction') == 'increasing':
                recommendations.append("Transaction volume is increasing - ensure monitoring capacity is adequate")

            if not recommendations:
                recommendations.append("Risk levels are stable - continue normal monitoring procedures")

        except Exception as e:
            logger.warning(f"Error generating recommendations: {str(e)}")
            recommendations.append("Unable to generate specific recommendations - continue standard monitoring")

        return recommendations


class RiskPredictor:
    """Simplified risk prediction for individual transactions"""

    def __init__(self):
        self.model = None
        self.feature_columns = [
            'amount', 'hour', 'day_of_week', 'transaction_frequency',
            'avg_amount_last_7_days', 'risk_score_last_transaction'
        ]

    def predict_transaction_risk(self, transaction_data: Dict, historical_context: List[Dict]) -> Dict:
        """Predict risk score for a single transaction"""
        try:
            # Extract features from transaction
            features = self._extract_transaction_features(transaction_data, historical_context)

            # Simple rule-based prediction (can be enhanced with ML model)
            risk_score = self._calculate_rule_based_risk(features)

            # Add confidence and explanation
            confidence = self._calculate_confidence(features)
            factors = self._identify_risk_factors(features)

            return {
                'predicted_risk_score': round(risk_score, 1),
                'confidence': round(confidence, 2),
                'risk_factors': factors,
                'risk_level': 'high' if risk_score >= 70 else 'medium' if risk_score >= 40 else 'low'
            }

        except Exception as e:
            logger.error(f"Error predicting transaction risk: {str(e)}")
            return {
                'predicted_risk_score': 50.0,
                'confidence': 0.5,
                'risk_factors': ['Unable to analyze transaction'],
                'risk_level': 'medium'
            }

    def _extract_transaction_features(self, transaction: Dict, historical: List[Dict]) -> Dict:
        """Extract features for risk prediction"""
        features = {}

        # Basic transaction features
        features['amount'] = transaction.get('amount', 0)
        features['hour'] = transaction.get('hour', 12)
        features['day_of_week'] = transaction.get('day_of_week', 0)

        # Historical context
        if historical:
            recent_transactions = historical[-10:]  # Last 10 transactions
            features['transaction_frequency'] = len([t for t in recent_transactions
                                                   if (datetime.now() - datetime.fromisoformat(t['date'])).days <= 1])

            amounts = [t['amount'] for t in recent_transactions]
            features['avg_amount_last_7_days'] = sum(amounts) / len(amounts) if amounts else 0

            risk_scores = [t.get('risk_score', 0) for t in recent_transactions]
            features['risk_score_last_transaction'] = risk_scores[-1] if risk_scores else 0
        else:
            features['transaction_frequency'] = 0
            features['avg_amount_last_7_days'] = 0
            features['risk_score_last_transaction'] = 0

        return features

    def _calculate_rule_based_risk(self, features: Dict) -> float:
        """Calculate risk score using rule-based approach"""
        risk_score = 0

        # Amount-based risk
        amount = features['amount']
        if amount > 10000:
            risk_score += 30
        elif amount > 5000:
            risk_score += 15
        elif amount > 1000:
            risk_score += 5

        # Time-based risk (unusual hours)
        hour = features['hour']
        if hour < 6 or hour > 22:  # Outside business hours
            risk_score += 10

        # Frequency-based risk
        frequency = features['transaction_frequency']
        if frequency > 5:  # High frequency
            risk_score += 15
        elif frequency > 10:  # Very high frequency
            risk_score += 25

        # Historical risk patterns
        last_risk = features['risk_score_last_transaction']
        risk_score += last_risk * 0.3  # 30% weight to previous risk

        # Amount deviation from average
        avg_amount = features['avg_amount_last_7_days']
        if avg_amount > 0:
            deviation = abs(amount - avg_amount) / avg_amount
            if deviation > 1.0:  # More than double average
                risk_score += 20
            elif deviation > 0.5:  # 50% above average
                risk_score += 10

        return min(max(risk_score, 0), 100)

    def _calculate_confidence(self, features: Dict) -> float:
        """Calculate confidence in the prediction"""
        confidence = 0.5  # Base confidence

        # Higher confidence with more historical data
        if features['transaction_frequency'] > 0:
            confidence += 0.2

        # Higher confidence for larger amounts (more significant)
        if features['amount'] > 1000:
            confidence += 0.1

        return min(confidence, 0.95)

    def _identify_risk_factors(self, features: Dict) -> List[str]:
        """Identify specific risk factors"""
        factors = []

        if features['amount'] > 10000:
            factors.append("High transaction amount")
        elif features['amount'] > 5000:
            factors.append("Above-average transaction amount")

        if features['hour'] < 6 or features['hour'] > 22:
            factors.append("Transaction outside business hours")

        if features['transaction_frequency'] > 5:
            factors.append("High transaction frequency")

        avg_amount = features['avg_amount_last_7_days']
        if avg_amount > 0 and abs(features['amount'] - avg_amount) / avg_amount > 0.5:
            factors.append("Significant deviation from average transaction amount")

        if features['risk_score_last_transaction'] > 50:
            factors.append("Previous high-risk transaction pattern")

        return factors if factors else ["No significant risk factors identified"]