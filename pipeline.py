import pandas as pd
import numpy as np
import json
import uuid
from datetime import datetime, timedelta
import os

# -------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# -------------------------------------------------------------------------
INPUT_FILE = "paysim.csv"
OUTPUT_DIR = "output"
SAMPLE_SIZE = 100000
START_DATE = datetime(2026, 1, 1, 0, 0, 0)
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

CITIES = [
    {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777, "weight_clean": 0.25, "weight_fraud": 0.10},
    {"city": "Delhi", "lat": 28.7041, "lon": 77.1025, "weight_clean": 0.20, "weight_fraud": 0.40},  # Fraud cluster
    {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "weight_clean": 0.15, "weight_fraud": 0.05},
    {"city": "Kolkata", "lat": 22.5726, "lon": 88.3639, "weight_clean": 0.10, "weight_fraud": 0.25}, # Fraud cluster
    {"city": "Chennai", "lat": 13.0827, "lon": 80.2707, "weight_clean": 0.08, "weight_fraud": 0.05},
    {"city": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "weight_clean": 0.08, "weight_fraud": 0.05},
    {"city": "Pune", "lat": 18.5204, "lon": 73.8567, "weight_clean": 0.05, "weight_fraud": 0.02},
    {"city": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "weight_clean": 0.04, "weight_fraud": 0.02},
    {"city": "Jaipur", "lat": 26.9124, "lon": 75.7873, "weight_clean": 0.03, "weight_fraud": 0.03},
    {"city": "Lucknow", "lat": 26.8467, "lon": 80.9462, "weight_clean": 0.02, "weight_fraud": 0.03},
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Please place the Kaggle PaySim CSV in the current directory and name it '{INPUT_FILE}'.")
        return
        
    print("===========================================")
    print("PHASE 1 — INGESTION & CLEANING")
    print("===========================================")
    
    dtypes = {
        'step': 'int32',
        'type': 'category',
        'amount': 'float32',
        'nameOrig': 'string',
        'oldbalanceOrg': 'float32',
        'newbalanceOrig': 'float32',
        'nameDest': 'string',
        'oldbalanceDest': 'float32',
        'newbalanceDest': 'float32',
        'isFraud': 'int8',
        'isFlaggedFraud': 'int8'
    }
    
    print("Loading data...")
    df = pd.read_csv(INPUT_FILE, dtype=dtypes)
    initial_rows = len(df)
    
    print("Validating data...")
    missing_vals = df.isnull().sum()
    neg_amounts = (df['amount'] < 0).sum()
    
    # Flag or drop corrupt rows
    df = df[df['amount'] >= 0].copy()
    
    # Add unique transaction_id
    df['transaction_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
    
    print(f"Loaded {len(df)} valid rows out of {initial_rows}.")

    print("===========================================")
    print("PHASE 2 — TIME ENRICHMENT")
    print("===========================================")
    print("Enriching time...")
    hours_to_add = pd.to_timedelta(df['step'], unit='h')
    df['timestamp'] = START_DATE + hours_to_add
    df['hour_of_day'] = df['timestamp'].dt.hour.astype('int8')
    df['day_of_week'] = df['timestamp'].dt.day_name().astype('category')
    df['day_number'] = df['timestamp'].dt.dayofweek.astype('int8') + 1 # 1 for Monday
    df['is_weekend'] = df['timestamp'].dt.dayofweek.isin([5, 6]).astype('int8')

    print("===========================================")
    print("PHASE 3 — DEVICE / CARD ENRICHMENT")
    print("===========================================")
    print("Assigning devices...")
    unique_users = df['nameOrig'].unique()
    num_users = len(unique_users)
    
    fraud_ring_pool_size = 5000
    fraud_ring_devices = [f"DEV_RING_{i}" for i in range(fraud_ring_pool_size)]
    
    user_df = pd.DataFrame({'nameOrig': unique_users})
    user_df['rand'] = np.random.rand(num_users)
    
    def assign_device(rand_val):
        if rand_val < 0.85:
            return "DEV_SGL_" + str(uuid.uuid4())[:8]
        elif rand_val < 0.95:
            return "DEV_DBL_" + str(uuid.uuid4())[:8] + ",DEV_DBL_" + str(uuid.uuid4())[:8]
        else:
            return np.random.choice(fraud_ring_devices)
            
    user_df['devices'] = user_df['rand'].apply(assign_device)
    user_devices = dict(zip(user_df['nameOrig'], user_df['devices']))
    
    device_mapping = user_df.set_index('nameOrig')['devices'].to_dict()
    df['device_id'] = df['nameOrig'].map(device_mapping)
    
    mask_multiple = df['device_id'].str.contains(',')
    if mask_multiple.any():
        df.loc[mask_multiple, 'device_id'] = df.loc[mask_multiple, 'device_id'].apply(lambda x: np.random.choice(x.split(',')))
        
    fraud_mask = (df['isFraud'] == 1)
    if fraud_mask.any():
        override_mask = fraud_mask & (np.random.rand(len(df)) < 0.5)
        super_ring = fraud_ring_devices[:100] 
        df.loc[override_mask, 'device_id'] = np.random.choice(super_ring, size=override_mask.sum())

    print("Building entity links...")
    entity_counts = df.groupby('device_id')['nameOrig'].nunique()
    shared_devices = entity_counts[entity_counts > 1].index
    entity_links = df[df['device_id'].isin(shared_devices)].groupby('device_id').agg(
        linked_accounts=('nameOrig', lambda x: ','.join(x.unique())),
        transaction_count=('transaction_id', 'count')
    ).reset_index()
    entity_links.to_csv(os.path.join(OUTPUT_DIR, 'entity_links.csv'), index=False)

    print("===========================================")
    print("PHASE 4 — GEOSPATIAL ENRICHMENT")
    print("===========================================")
    print("Assigning locations...")
    
    clean_cities = [c['city'] for c in CITIES]
    clean_weights = [c['weight_clean'] for c in CITIES]
    clean_weights = np.array(clean_weights) / sum(clean_weights)
    
    fraud_weights = [c['weight_fraud'] for c in CITIES]
    fraud_weights = np.array(fraud_weights) / sum(fraud_weights)
    
    df['city'] = np.random.choice(clean_cities, size=len(df), p=clean_weights)
    
    if fraud_mask.any():
        df.loc[fraud_mask, 'city'] = np.random.choice(clean_cities, size=fraud_mask.sum(), p=fraud_weights)
        
    unrec_mask = np.random.rand(len(df)) < 0.04
    df.loc[unrec_mask, 'city'] = 'Unrecognized'
    
    city_to_lat = {c['city']: c['lat'] for c in CITIES}
    city_to_lon = {c['city']: c['lon'] for c in CITIES}
    
    df['latitude'] = df['city'].map(city_to_lat)
    df['longitude'] = df['city'].map(city_to_lon)
    
    geo_ref = pd.DataFrame(CITIES)[['city', 'lat', 'lon']]
    geo_ref.to_csv(os.path.join(OUTPUT_DIR, 'geocoding_reference.csv'), index=False)

    print("===========================================")
    print("PHASE 5 — CUSTOMER BASELINE ENRICHMENT")
    print("===========================================")
    print("Calculating baselines...")
    cust_stats = df.groupby('nameOrig')['amount'].agg(['mean', 'std', 'count']).astype('float32')
    cust_stats.rename(columns={'mean': 'customer_avg_amount', 'std': 'customer_std_amount', 'count': 'customer_txn_count'}, inplace=True)
    
    cust_stats['customer_std_amount'] = cust_stats['customer_std_amount'].fillna(0)
    
    df = df.merge(cust_stats, on='nameOrig', how='left')
    
    df['deviation_score'] = np.where(
        df['customer_std_amount'] > 0,
        (df['amount'] - df['customer_avg_amount']) / df['customer_std_amount'],
        0
    ).astype('float32')

    print("===========================================")
    print("PHASE 6 — RISK SCORE")
    print("===========================================")
    print("Generating risk scores...")
    
    risk = np.random.normal(loc=15, scale=5, size=len(df))
    risk += np.where(df['type'].isin(['TRANSFER', 'CASH_OUT']), 20, 0)
    risk += np.clip(df['deviation_score'], 0, 5) * 5
    
    amount_p95 = df['amount'].quantile(0.95)
    risk += np.where(df['amount'] > amount_p95, 15, 0)
    
    shared_device_set = set(shared_devices)
    risk += df['device_id'].isin(shared_device_set).astype(int) * 25
    
    risk += df['isFraud'] * 30
    df['risk_score'] = np.clip(risk, 0, 100).astype('int8')

    print("===========================================")
    print("PHASE 7 — BUSINESS/COST PARAMETERS")
    print("===========================================")
    cost_params = {
        "cost_per_false_positive_usd": 15,
        "cost_per_missed_fraud_usd": 500,
        "investigation_cost_per_alert_usd": 25,
        "justification": "False positives annoy customers, assumed $15 lifetime value risk. Missed fraud averages $500 hard loss. Investigation costs assume 30 mins analyst time at $50/hr."
    }
    with open(os.path.join(OUTPUT_DIR, 'cost_parameters.json'), 'w') as f:
        json.dump(cost_params, f, indent=4)

    print("===========================================")
    print("PHASE 8 — VALIDATION & QA REPORT")
    print("===========================================")
    qa_report = f"""# Validation & QA Report

## Dataset Shape
- **Final Rows**: {len(df)}
- **Final Columns**: {len(df.columns)}
- **Initial Fraud Rate**: {df['isFraud'].mean()*100:.3f}%

## Distributions
- **Amount**: Mean = {df['amount'].mean():.2f}, Max = {df['amount'].max():.2f}
- **Risk Score**: Mean = {df['risk_score'].mean():.2f}, Max = {df['risk_score'].max():.2f}
- **Deviation Score**: Mean = {df['deviation_score'].mean():.2f}, Max = {df['deviation_score'].max():.2f}

## Fraud Breakdown by Type
{df.groupby('type')['isFraud'].agg(['count', 'mean']).to_string()}

## Geographical Spread
{df['city'].value_counts(normalize=True).mul(100).round(2).to_string()}

## Device Sharing
- **Total Shared Devices**: {len(shared_devices)}
- **Entity Links Built**: {len(entity_links)}

## Notes for Tableau
- Null locations exist by design under city 'Unrecognized' for map error handling.
- `customer_avg_amount` is a global pre-calculation to validate your LOD {{FIXED [nameOrig] : AVG([amount])}}.
"""
    with open(os.path.join(OUTPUT_DIR, 'validation_report.md'), 'w') as f:
        f.write(qa_report)

    print("===========================================")
    print("PHASE 9 — DATA DICTIONARY")
    print("===========================================")
    dictionary = [
        {"column": "transaction_id", "type": "string", "source": "Synthetic", "description": "Unique UUID for the transaction"},
        {"column": "step", "type": "int", "source": "Original", "description": "Simulated time step (1 step = 1 hour)"},
        {"column": "type", "type": "string", "source": "Original", "description": "Transaction type (PAYMENT, TRANSFER, etc.)"},
        {"column": "amount", "type": "float", "source": "Original", "description": "Transaction amount in local currency"},
        {"column": "nameOrig", "type": "string", "source": "Original", "description": "Origin customer ID"},
        {"column": "oldbalanceOrg", "type": "float", "source": "Original", "description": "Origin balance before transaction"},
        {"column": "newbalanceOrig", "type": "float", "source": "Original", "description": "Origin balance after transaction"},
        {"column": "nameDest", "type": "string", "source": "Original", "description": "Destination customer/merchant ID"},
        {"column": "oldbalanceDest", "type": "float", "source": "Original", "description": "Destination balance before transaction"},
        {"column": "newbalanceDest", "type": "float", "source": "Original", "description": "Destination balance after transaction"},
        {"column": "isFraud", "type": "int", "source": "Original", "description": "Actual fraud indicator (1=Fraud, 0=Genuine)"},
        {"column": "isFlaggedFraud", "type": "int", "source": "Original", "description": "Original simplistic heuristic flag"},
        {"column": "timestamp", "type": "datetime", "source": "Synthetic", "description": "Real timestamp mapped from step (Starts 2026-01-01)"},
        {"column": "hour_of_day", "type": "int", "source": "Synthetic", "description": "Extracted hour (0-23) for heatmaps"},
        {"column": "day_of_week", "type": "string", "source": "Synthetic", "description": "Extracted day name (Monday-Sunday)"},
        {"column": "day_number", "type": "int", "source": "Synthetic", "description": "Extracted day of week number (1-7)"},
        {"column": "is_weekend", "type": "int", "source": "Synthetic", "description": "1 if weekend, 0 if weekday"},
        {"column": "device_id", "type": "string", "source": "Synthetic", "description": "Assigned device ID to enable velocity tracking"},
        {"column": "city", "type": "string", "source": "Synthetic", "description": "Assigned Indian city"},
        {"column": "latitude", "type": "float", "source": "Synthetic", "description": "City latitude"},
        {"column": "longitude", "type": "float", "source": "Synthetic", "description": "City longitude"},
        {"column": "customer_avg_amount", "type": "float", "source": "Synthetic", "description": "Overall average txn amount for this customer"},
        {"column": "customer_std_amount", "type": "float", "source": "Synthetic", "description": "Overall std dev of txn amount for this customer"},
        {"column": "customer_txn_count", "type": "int", "source": "Synthetic", "description": "Total lifetime transactions for this customer"},
        {"column": "deviation_score", "type": "float", "source": "Synthetic", "description": "Z-score of current amount vs customer baseline"},
        {"column": "risk_score", "type": "int", "source": "Synthetic", "description": "Composite simulated machine learning risk score (0-100)"},
    ]
    pd.DataFrame(dictionary).to_csv(os.path.join(OUTPUT_DIR, 'data_dictionary.csv'), index=False)

    print("===========================================")
    print("PHASE 10 — FINAL EXPORTS")
    print("===========================================")
    full_export_path = os.path.join(OUTPUT_DIR, 'enriched_paysim.csv')
    print(f"Exporting full dataset to {full_export_path} ...")
    df.to_csv(full_export_path, index=False)
    
    print("Generating stratified sample...")
    if len(df) > SAMPLE_SIZE:
        sample_df = df.groupby('isFraud', group_keys=False).apply(lambda x: x.sample(int(np.rint(SAMPLE_SIZE * len(x)/len(df))), random_state=42))
    else:
        sample_df = df
    
    sample_export_path = os.path.join(OUTPUT_DIR, 'enriched_paysim_sample.csv')
    print(f"Exporting sample dataset to {sample_export_path} ...")
    sample_df.to_csv(sample_export_path, index=False)
    
    print("Done! All deliverables are ready in the 'output' directory.")

if __name__ == "__main__":
    main()
