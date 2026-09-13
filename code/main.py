import sys
import os
import csv
from pathlib import Path
from typing import List, Dict, Any

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from code.config import (
    OUTPUT_PATH,
    ROOT_OUTPUT_PATH,
    EVALUATION_DIR,
)
from code.utils.data_loader import (
    load_financial_profiles,
    load_financial_events,
    load_exchange_rates,
    load_requests,
    load_request_payment_options,
    load_messages,
    load_images,
)
from code.ai_brain.image_parser import parse_image
from code.ai_brain.message_parser import MessageParser
from code.ai_brain.request_analyzer import RequestAnalyzer
from code.financial_brain.currency import CurrencyConverter
from code.financial_brain.cashflow_engine import CashflowEngine
from code.decision_brain.plan_simulator import PlanSimulator
from code.decision_brain.explanation_generator import ExplanationGenerator
from code.evaluation.usage_tracker import UsageTracker

def run_pipeline(is_sample: bool = False, output_file: Path = OUTPUT_PATH) -> List[Dict[str, Any]]:
    print(f"Loading datasets (sample={is_sample})...")
    profiles = load_financial_profiles()
    events = load_financial_events()
    rates = load_exchange_rates()
    requests = load_requests(is_sample=is_sample)
    options = load_request_payment_options()
    messages = load_messages()
    images = load_images()

    converter = CurrencyConverter(rates)
    engine = CashflowEngine(converter)
    simulator = PlanSimulator(engine)
    tracker = UsageTracker()

    # Pre-patch missing event amounts using image parser
    image_map = {im['related_event_id']: im['image_id'] for im in images}
    for e in events:
        if e['amount'] is None:
            rel_img = image_map.get(e['event_id'])
            if rel_img:
                parsed = parse_image(rel_img)
                e['amount'] = parsed.get('amount')
                e['currency'] = parsed.get('currency', e['currency'])

    # Group events by user_id for fast lookup
    events_by_user = {}
    for e in events:
        u_id = e['user_id']
        if u_id not in events_by_user:
            events_by_user[u_id] = []
        events_by_user[u_id].append(e)

    results = []
    print(f"Processing {len(requests)} requests...")

    for req in requests:
        req_id = req['request_id']
        u_id = req['user_id']
        req_date = req['request_date']
        req_amt = req['requested_amount']
        
        prof = profiles.get(u_id, {
            'user_id': u_id,
            'home_currency': 'USD',
            'current_available_balance': 0.0,
            'minimum_balance_to_keep': 0.0,
            'financial_priorities': [],
            'expense_categories_to_protect': [],
            'expense_categories_user_is_willing_to_reduce': [],
            'expense_categories_user_is_willing_to_stop': [],
            'payment_methods_user_will_consider': ['full_payment'],
            'max_installment_months': None,
        })

        # 1. AI Brain: Parse messages for grounded facts
        msg_facts = MessageParser.parse_messages_for_user(u_id, messages)

        # 2. Financial Brain: Reconstruct unified financial state & commitments
        commitments = engine.reconstruct_user_commitments(u_id, prof, events, msg_facts, req_date)

        # 3. Decision Brain: Simulate plans, check constraints, rank strategies
        user_opts = options.get(req_id, [])
        u_events = events_by_user.get(u_id, [])
        best_plan = simulator.generate_candidate_plans(req, prof, commitments, user_opts, u_events)

        # 4. Generate grounded explanation
        explanation = ExplanationGenerator.generate_explanation(best_plan, req, prof)

        # Format output fields strictly per contract
        amount_safe = best_plan.get('amount_safe_to_pay', 0.0)
        # Format amount_safe cleanly (int if integer, otherwise float)
        amt_safe_formatted = int(amount_safe) if float(amount_safe).is_integer() else round(amount_safe, 2)
        
        out_row = {
            'request_id': req_id,
            'amount_safe_to_pay': amt_safe_formatted,
            'affordability_status': best_plan.get('affordability_status'),
            'recommended_payment_method': best_plan.get('recommended_payment_method'),
            'payment_plan': best_plan.get('payment_plan'),
            'earliest_date_for_full_payment': best_plan.get('earliest_date_for_full_payment', ''),
            'spending_changes_needed': best_plan.get('spending_changes_needed', 'none'),
            'decision_explanation': explanation,
        }
        results.append(out_row)

        # Track usage
        tracker.record_request()

    # Write output.csv
    fieldnames = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    if output_file != ROOT_OUTPUT_PATH and not is_sample:
        # Also mirror to root output.csv
        with open(ROOT_OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)

    # Generate usage report
    tracker.generate_report(EVALUATION_DIR / "usage_report.md")
    print(f"Successfully generated {output_file} ({len(results)} rows).")
    return results

if __name__ == "__main__":
    run_pipeline(is_sample=False)
