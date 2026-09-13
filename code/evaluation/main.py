import sys
import os
from pathlib import Path
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from code.config import SAMPLE_REQUESTS_PATH
from code.utils.data_loader import load_requests
from code.main import run_pipeline

def evaluate_on_samples():
    print("Running evaluation against sample requests dataset...")
    temp_output = Path(__file__).resolve().parent / "sample_predictions.csv"
    
    predictions = run_pipeline(is_sample=True, output_file=temp_output)
    ground_truth = load_requests(is_sample=True)

    gt_by_id = {r['request_id']: r for r in ground_truth}
    
    total = len(predictions)
    status_matches = 0
    method_matches = 0
    date_matches = 0
    plan_matches = 0
    changes_matches = 0

    print(f"\n==================== EVALUATION RESULTS ({total} samples) ====================")
    print(f"{'Req ID':<12} | {'Exp Status':<22} | {'Pred Status':<22} | {'Exp Method':<18} | {'Pred Method':<18} | Match")
    print("-" * 105)

    for pred in predictions:
        req_id = pred['request_id']
        gt = gt_by_id.get(req_id, {})

        status_ok = pred['affordability_status'] == gt.get('affordability_status')
        method_ok = pred['recommended_payment_method'] == gt.get('recommended_payment_method')
        date_ok = str(pred['earliest_date_for_full_payment']).strip() == str(gt.get('earliest_date_for_full_payment', '')).strip()
        changes_ok = str(pred['spending_changes_needed']).strip() == str(gt.get('spending_changes_needed', '')).strip()

        if status_ok:
            status_matches += 1
        if method_ok:
            method_matches += 1
        if date_ok:
            date_matches += 1
        if changes_ok:
            changes_matches += 1

        match_badge = "[PASS]" if (status_ok and method_ok) else "[FAIL]"
        print(f"{req_id:<12} | {str(gt.get('affordability_status')):<22} | {str(pred['affordability_status']):<22} | {str(gt.get('recommended_payment_method')):<18} | {str(pred['recommended_payment_method']):<18} | {match_badge}")

    print("\n-------------------- METRICS SUMMARY --------------------")
    print(f"Affordability Status Accuracy : {status_matches}/{total} ({status_matches/total*100:.1f}%)")
    print(f"Payment Method Accuracy      : {method_matches}/{total} ({method_matches/total*100:.1f}%)")
    print(f"Earliest Date Accuracy       : {date_matches}/{total} ({date_matches/total*100:.1f}%)")
    print(f"Spending Changes Accuracy    : {changes_matches}/{total} ({changes_matches/total*100:.1f}%)")
    print("=========================================================\n")

    if temp_output.exists():
        temp_output.unlink()

if __name__ == "__main__":
    evaluate_on_samples()
