import csv
from typing import Dict, List, Any, Optional
import pandas as pd
from code.config import (
    FINANCIAL_PROFILES_PATH,
    FINANCIAL_EVENTS_PATH,
    EXCHANGE_RATES_PATH,
    REQUESTS_PATH,
    SAMPLE_REQUESTS_PATH,
    REQUEST_PAYMENT_OPTIONS_PATH,
    MESSAGES_PATH,
    IMAGES_PATH,
)

def parse_pipe_list(value: Any) -> List[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split("|") if item.strip()]

def load_financial_profiles() -> Dict[str, Dict[str, Any]]:
    df = pd.read_csv(FINANCIAL_PROFILES_PATH)
    profiles = {}
    for _, row in df.iterrows():
        user_id = str(row['user_id']).strip()
        max_inst = None
        if not pd.isna(row.get('max_installment_months')) and str(row.get('max_installment_months')).strip():
            try:
                max_inst = int(float(row['max_installment_months']))
            except (ValueError, TypeError):
                max_inst = None

        profiles[user_id] = {
            'user_id': user_id,
            'home_currency': str(row['home_currency']).strip(),
            'current_available_balance': float(row['current_available_balance']),
            'minimum_balance_to_keep': float(row['minimum_balance_to_keep']),
            'financial_priorities': parse_pipe_list(row.get('financial_priorities')),
            'expense_categories_to_protect': parse_pipe_list(row.get('expense_categories_to_protect')),
            'expense_categories_user_is_willing_to_reduce': parse_pipe_list(row.get('expense_categories_user_is_willing_to_reduce')),
            'expense_categories_user_is_willing_to_stop': parse_pipe_list(row.get('expense_categories_user_is_willing_to_stop')),
            'payment_methods_user_will_consider': parse_pipe_list(row.get('payment_methods_user_will_consider')),
            'max_installment_months': max_inst,
        }
    return profiles

def load_financial_events() -> List[Dict[str, Any]]:
    df = pd.read_csv(FINANCIAL_EVENTS_PATH)
    events = []
    for _, row in df.iterrows():
        amt = None
        if not pd.isna(row.get('amount')) and str(row.get('amount')).strip() != '':
            try:
                amt = float(row['amount'])
            except (ValueError, TypeError):
                amt = None

        min_amt = None
        if not pd.isna(row.get('minimum_allowed_amount')) and str(row.get('minimum_allowed_amount')).strip() != '':
            try:
                min_amt = float(row['minimum_allowed_amount'])
            except (ValueError, TypeError):
                min_amt = None

        events.append({
            'event_id': str(row['event_id']).strip(),
            'user_id': str(row['user_id']).strip(),
            'event_type': str(row['event_type']).strip(),
            'description': str(row['description']).strip() if not pd.isna(row.get('description')) else '',
            'category': str(row['category']).strip() if not pd.isna(row.get('category')) else '',
            'direction': str(row['direction']).strip() if not pd.isna(row.get('direction')) else '',
            'amount': amt,
            'currency': str(row['currency']).strip() if not pd.isna(row.get('currency')) else '',
            'event_date': str(row['event_date']).strip() if not pd.isna(row.get('event_date')) else '',
            'settlement_date': str(row['settlement_date']).strip() if not pd.isna(row.get('settlement_date')) else '',
            'status': str(row['status']).strip() if not pd.isna(row.get('status')) else '',
            'linked_event_id': str(row['linked_event_id']).strip() if not pd.isna(row.get('linked_event_id')) else '',
            'flexibility': str(row['flexibility']).strip() if not pd.isna(row.get('flexibility')) else 'fixed',
            'minimum_allowed_amount': min_amt,
        })
    return events

def load_exchange_rates() -> List[Dict[str, Any]]:
    df = pd.read_csv(EXCHANGE_RATES_PATH)
    rates = []
    for _, row in df.iterrows():
        rates.append({
            'rate_date': str(row['rate_date']).strip(),
            'from_currency': str(row['from_currency']).strip(),
            'to_currency': str(row['to_currency']).strip(),
            'rate': float(row['rate']),
        })
    return rates

def load_requests(is_sample: bool = False) -> List[Dict[str, Any]]:
    path = SAMPLE_REQUESTS_PATH if is_sample else REQUESTS_PATH
    df = pd.read_csv(path)
    reqs = []
    for _, row in df.iterrows():
        req = {
            'request_id': str(row['request_id']).strip(),
            'user_id': str(row['user_id']).strip(),
            'request_date': str(row['request_date']).strip(),
            'request_type': str(row['request_type']).strip(),
            'requested_amount': float(row['requested_amount']),
            'desired_completion_date': str(row['desired_completion_date']).strip(),
            'allows_partial_payment': str(row['allows_partial_payment']).strip().lower() in ['true', '1', 'yes'],
            'request_text': str(row.get('request_text', '')).strip(),
        }
        if is_sample:
            amt_safe = None
            if not pd.isna(row.get('amount_safe_to_pay')) and str(row.get('amount_safe_to_pay')).strip() != '':
                amt_safe = float(row['amount_safe_to_pay'])
            req.update({
                'amount_safe_to_pay': amt_safe,
                'affordability_status': str(row.get('affordability_status', '')).strip(),
                'recommended_payment_method': str(row.get('recommended_payment_method', '')).strip(),
                'payment_plan': str(row.get('payment_plan', '')).strip(),
                'earliest_date_for_full_payment': str(row.get('earliest_date_for_full_payment', '')).strip() if not pd.isna(row.get('earliest_date_for_full_payment')) else '',
                'spending_changes_needed': str(row.get('spending_changes_needed', '')).strip(),
                'decision_explanation': str(row.get('decision_explanation', '')).strip(),
            })
        reqs.append(req)
    return reqs

def load_request_payment_options() -> Dict[str, List[Dict[str, Any]]]:
    df = pd.read_csv(REQUEST_PAYMENT_OPTIONS_PATH)
    options_by_req = {}
    for _, row in df.iterrows():
        req_id = str(row['request_id']).strip()
        num_pmts = int(float(row['number_of_payments'])) if not pd.isna(row.get('number_of_payments')) else 1
        freq_days = int(float(row['payment_frequency_days'])) if not pd.isna(row.get('payment_frequency_days')) and str(row.get('payment_frequency_days')).strip() != '' else 0
        fee = float(row['financing_fee']) if not pd.isna(row.get('financing_fee')) else 0.0
        tot_payable = float(row['total_payable_amount']) if not pd.isna(row.get('total_payable_amount')) else float(row['payment_amount']) * num_pmts
        
        opt = {
            'payment_option_id': str(row['payment_option_id']).strip(),
            'request_id': req_id,
            'payment_method': str(row['payment_method']).strip(),
            'payment_amount': float(row['payment_amount']),
            'number_of_payments': num_pmts,
            'first_payment_date': str(row['first_payment_date']).strip() if not pd.isna(row.get('first_payment_date')) else '',
            'payment_frequency_days': freq_days,
            'financing_fee': fee,
            'total_payable_amount': tot_payable,
        }
        if req_id not in options_by_req:
            options_by_req[req_id] = []
        options_by_req[req_id].append(opt)
    return options_by_req

def load_messages() -> List[Dict[str, Any]]:
    df = pd.read_csv(MESSAGES_PATH)
    msgs = []
    for _, row in df.iterrows():
        msgs.append({
            'message_id': str(row['message_id']).strip(),
            'user_id': str(row['user_id']).strip(),
            'request_id': str(row['request_id']).strip() if not pd.isna(row.get('request_id')) and str(row.get('request_id')).strip() != '' else None,
            'related_event_id': str(row['related_event_id']).strip() if not pd.isna(row.get('related_event_id')) and str(row.get('related_event_id')).strip() != '' else None,
            'sent_at': str(row['sent_at']).strip() if not pd.isna(row.get('sent_at')) else '',
            'source_type': str(row.get('source_type', '')).strip(),
            'message_text': str(row.get('message_text', '')).strip(),
        })
    return msgs

def load_images() -> List[Dict[str, Any]]:
    df = pd.read_csv(IMAGES_PATH)
    images = []
    for _, row in df.iterrows():
        images.append({
            'image_id': str(row['image_id']).strip(),
            'user_id': str(row['user_id']).strip(),
            'request_id': str(row['request_id']).strip(),
            'related_event_id': str(row['related_event_id']).strip(),
        })
    return images
