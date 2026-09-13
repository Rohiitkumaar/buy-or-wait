from typing import Dict, Any, List
from datetime import datetime

def format_date_natural(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%B')} {dt.year}"
    except Exception:
        return date_str

def format_amount(amount: float, currency: str) -> str:
    if amount is None:
        return f"{currency} 0"
    if currency in ["IDR", "INR"]:
        if amount.is_integer():
            return f"{currency} {int(amount):,}"
        return f"{currency} {amount:,.2f}"
    else:
        if amount.is_integer():
            return f"{currency} {int(amount):,}"
        return f"{currency} {amount:,.2f}"

class ExplanationGenerator:
    @staticmethod
    def generate_explanation(
        plan: Dict[str, Any],
        request: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> str:
        status = plan.get('affordability_status')
        method = plan.get('recommended_payment_method')
        home_curr = profile.get('home_currency', 'USD')
        min_keep = profile.get('minimum_balance_to_keep', 0.0)
        req_amt = request.get('requested_amount', 0.0)
        req_date = request.get('request_date')
        comp_date = request.get('desired_completion_date')
        earliest_date = plan.get('earliest_date_for_full_payment')
        safe_amt = plan.get('amount_safe_to_pay', 0.0)
        spending_changes = plan.get('spending_changes', [])

        req_amt_str = format_amount(req_amt, home_curr)
        min_keep_str = format_amount(min_keep, home_curr)

        # 1. Affordable now
        if status == 'affordable_now':
            return f"Pay {req_amt_str} today. This leaves at least {min_keep_str} available over the next 90 days."

        # 2. Affordable with plan
        if status == 'affordable_with_plan':
            # Spending changes
            if spending_changes:
                actions = []
                for sc in spending_changes:
                    desc = sc.get('desc', 'subscription').lower()
                    if sc['type'] == 'stop':
                        actions.append(f"Stop the {desc}")
                    elif sc['type'] == 'reduce_to':
                        new_amt_str = format_amount(sc['new_amount'], home_curr)
                        actions.append(f"Reduce the {desc} to {new_amt_str}")
                action_text = " and ".join(actions)
                return f"{action_text}, then pay {req_amt_str} today. This leaves at least {min_keep_str} available."

            # Partial payment
            if method == 'partial_payment':
                p1_str = format_amount(safe_amt, home_curr)
                p2_str = format_amount(req_amt - safe_amt, home_curr)
                date2_str = format_date_natural(earliest_date)
                return f"Pay {p1_str} today and the remaining {p2_str} on {date2_str}. This completes the full request and keeps the {min_keep_str} minimum protected."

            # Installments
            if method == 'installments':
                opt_meta = plan.get('option_meta', {})
                num_pmts = plan.get('number_of_payments', opt_meta.get('number_of_payments', 3))
                pmt_amt = opt_meta.get('payment_amount', req_amt / num_pmts)
                pmt_amt_str = format_amount(pmt_amt, home_curr)
                start_date_str = format_date_natural(plan.get('first_payment_date'))
                return f"Use {num_pmts} installments of {pmt_amt_str}, starting {start_date_str}. This leaves at least {min_keep_str} available."

        # 3. Affordable later (wait)
        if status == 'affordable_later' or method == 'wait':
            e_date_str = format_date_natural(earliest_date)
            return f"Pay {req_amt_str} in full on {e_date_str}. Paying earlier would take the balance below the {min_keep_str} minimum."

        # 4. Not affordable
        if status == 'not_affordable' or method == 'not_recommended':
            comp_date_str = format_date_natural(comp_date)
            if safe_amt > 0 and earliest_date == "":
                safe_amt_str = format_amount(safe_amt, home_curr)
                return f"Do not proceed with the {req_amt_str} request. Although {safe_amt_str} is available today, the full amount cannot be completed safely within 90 days."
            return f"Do not make this payment by {comp_date_str}. None of the available options keeps the {min_keep_str} minimum protected."

        return f"Decision pending financial validation for {req_amt_str}."
