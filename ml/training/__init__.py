"""
NeerNetra — ML Training Module
=================================
Model training pipeline for flood prediction.

Primary: Random Forest Classifier
Advanced: XGBoost Classifier

Training process (Section 6.5):
1. Raw Historical Data
2. Synchronise timestamps
3. Match geographic regions
4. Generate rainfall windows
5. Generate terrain features
6. Attach historical flood labels
7. Remove invalid samples
8. Train / Validation / Test split (temporal, Section 6.6)
9. Train model
10. Evaluate
11. Save model
"""
