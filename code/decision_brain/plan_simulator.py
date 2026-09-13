from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import itertools

from code.financial_brain.cashflow_engine import CashflowEngine
from code.decision_brain.safety_checker import SafetyChecker
from code.decision_brain.ranker import StrategyRanker

def format_amt_clean(amt: float) -> str:
    if amt is None:
        return "0"
    if float(amt).is_integer():
        return str(int(amt))
    return f"{amt:.2f}"

class PlanSimulator:
    def __init__(self, engine: CashflowEngine):
        self.engine = engine

    def generate_candidate_plans(
        self,
        request: Dict[str, Any],
        profile: Dict[str, Any],
        commitments: Dict[str, Any],
        payment_options: List[Dict[str, Any]],
        all_user_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        req_id = request['request_id']
        user_id = request['user_id']
        req_date = request['request_date']
        req_amt = request['requested_amount']
        comp_date = request['desired_completion_date']
        allows_partial = request['allows_partial_payment']
        
        home_curr = profile['home_currency']
        min_keep = profile['minimum_balance_to_keep']
        user_methods = profile.get('payment_methods_user_will_consider', [])
        max_inst_months = profile.get('max_installment_months')

        base_safe_to_pay = self.engine.compute_safe_to_pay(commitments, req_date, req_amt)
        earliest_full_date = self.engine.find_earliest_full_payment_date(commitments, req_date, req_amt)

        candidate_plans = []

        # ----------------------------------------------------
        # OPTION A: Full payment (no spending changes)
        # ----------------------------------------------------
        if 'full_payment' in user_methods:
            if base_safe_to_pay >= req_amt - 1e-4:
                amt_str = format_amt_clean(req_amt)
                candidate_plans.append({
                    "affordability_status": "affordable_now",
                    "recommended_payment_method": "full_payment",
                    "payment_plan": f"{req_date}:{amt_str}",
                    "amount_safe_to_pay": req_amt,
                    "earliest_date_for_full_payment": req_date,
                    "spending_changes": [],
                    "spending_changes_needed": "none",
                    "total_payable_amount": req_amt,
                    "first_payment_date": req_date,
                    "completion_date": req_date,
                    "number_of_payments": 1,
                    "payment_option_id": "full_now",
                })

        # ----------------------------------------------------
        # OPTION B: Partial payment (safe_amt today, rest on earliest_full_date)
        # ----------------------------------------------------
        if 'partial_payment' in user_methods and allows_partial:
            if 0 < base_safe_to_pay < req_amt and earliest_full_date and earliest_full_date <= comp_date:
                rem_amt = req_amt - base_safe_to_pay
                schedule = [
                    (req_date, base_safe_to_pay),
                    (earliest_full_date, rem_amt)
                ]
                base_timeline = self.engine.simulate_timeline(commitments, req_date)
                is_safe, min_margin = SafetyChecker.is_plan_safe(
                    base_timeline, schedule, min_keep, comp_date, req_date
                )
                if is_safe:
                    p1_str = format_amt_clean(base_safe_to_pay)
                    p2_str = format_amt_clean(rem_amt)
                    plan_str = f"{req_date}:{p1_str}|{earliest_full_date}:{p2_str}"
                    candidate_plans.append({
                        "affordability_status": "affordable_with_plan",
                        "recommended_payment_method": "partial_payment",
                        "payment_plan": plan_str,
                        "amount_safe_to_pay": base_safe_to_pay,
                        "earliest_date_for_full_payment": earliest_full_date,
                        "spending_changes": [],
                        "spending_changes_needed": "none",
                        "total_payable_amount": req_amt,
                        "first_payment_date": req_date,
                        "completion_date": earliest_full_date,
                        "number_of_payments": 2,
                        "payment_option_id": "partial_plan",
                    })

        # ----------------------------------------------------
        # OPTION C: Installments from request_payment_options
        # ----------------------------------------------------
        if 'installments' in user_methods:
            for opt in payment_options:
                if opt['payment_method'] != 'installments':
                    continue
                
                num_pmts = opt['number_of_payments']
                if max_inst_months is not None and num_pmts > max_inst_months:
                    continue

                pmt_amt = opt['payment_amount']
                first_date = opt['first_payment_date'] or req_date
                freq_days = opt['payment_frequency_days'] or 30
                
                schedule = []
                f_dt = datetime.strptime(first_date, "%Y-%m-%d")
                for p_idx in range(num_pmts):
                    p_dt = f_dt + timedelta(days=p_idx * freq_days)
                    schedule.append((p_dt.strftime("%Y-%m-%d"), pmt_amt))

                last_date = schedule[-1][0]
                if last_date > comp_date:
                    continue

                base_timeline = self.engine.simulate_timeline(commitments, req_date)
                is_safe, min_margin = SafetyChecker.is_plan_safe(
                    base_timeline, schedule, min_keep, comp_date, req_date
                )

                if is_safe:
                    plan_str = "|".join([
                        f"{d}:{format_amt_clean(pmt_amt)}"
                        for d, _ in schedule
                    ])
                    candidate_plans.append({
                        "affordability_status": "affordable_with_plan",
                        "recommended_payment_method": "installments",
                        "payment_plan": plan_str,
                        "amount_safe_to_pay": base_safe_to_pay,
                        "earliest_date_for_full_payment": earliest_full_date if earliest_full_date else "",
                        "spending_changes": [],
                        "spending_changes_needed": "none",
                        "total_payable_amount": opt['total_payable_amount'],
                        "first_payment_date": first_date,
                        "completion_date": last_date,
                        "number_of_payments": num_pmts,
                        "payment_option_id": opt['payment_option_id'],
                        "option_meta": opt,
                    })

        # ----------------------------------------------------
        # OPTION D: Spending Changes (adjust up to 3 flexible expenses)
        # ----------------------------------------------------
        if 'full_payment' in user_methods and base_safe_to_pay < req_amt:
            stop_cats = set([c.lower() for c in profile.get('expense_categories_user_is_willing_to_stop', [])])
            red_cats = set([c.lower() for c in profile.get('expense_categories_user_is_willing_to_reduce', [])])
            protect_cats = set([c.lower() for c in profile.get('expense_categories_to_protect', [])])

            stoppable_events = []
            reducible_events = []
            
            # Find candidate flexible events (stoppable or reducible)
            for e in all_user_events:
                cat = e['category'].lower()
                if cat in protect_cats:
                    continue
                flex = e.get('flexibility', '').lower()
                if flex == 'stoppable' and cat in stop_cats:
                    stoppable_events.append(e)
                elif flex == 'reducible' and cat in red_cats:
                    reducible_events.append(e)

            # Deduplicate by event_id, keep most recent
            stoppable_by_id = {e['event_id']: e for e in stoppable_events}
            reducible_by_id = {e['event_id']: e for e in reducible_events}

            change_candidates = []
            for ev_id, ev in stoppable_by_id.items():
                change_candidates.append([{"type": "stop", "event_id": ev_id, "category": ev['category'], "desc": ev['description'], "amt": ev['amount']}])
            for ev_id, ev in reducible_by_id.items():
                min_amt = ev.get('minimum_allowed_amount') or (ev['amount'] * 0.5)
                change_candidates.append([{"type": "reduce_to", "event_id": ev_id, "category": ev['category'], "desc": ev['description'], "new_amount": min_amt, "amt": ev['amount']}])
            
            for (ev1_id, ev1), (ev2_id, ev2) in itertools.combinations(list(stoppable_by_id.items()) + list(reducible_by_id.items()), 2):
                if ev1_id != ev2_id:
                    c1 = {"type": "stop", "event_id": ev1_id, "category": ev1['category'], "desc": ev1['description'], "amt": ev1['amount']} if ev1_id in stoppable_by_id else {"type": "reduce_to", "event_id": ev1_id, "category": ev1['category'], "desc": ev1['description'], "new_amount": ev1.get('minimum_allowed_amount', ev1['amount']*0.5), "amt": ev1['amount']}
                    c2 = {"type": "stop", "event_id": ev2_id, "category": ev2['category'], "desc": ev2['description'], "amt": ev2['amount']} if ev2_id in stoppable_by_id else {"type": "reduce_to", "event_id": ev2_id, "category": ev2['category'], "desc": ev2['description'], "new_amount": ev2.get('minimum_allowed_amount', ev2['amount']*0.5), "amt": ev2['amount']}
                    change_candidates.append([c1, c2])

            for changes in change_candidates:
                safe_with_changes = self.engine.compute_safe_to_pay(commitments, req_date, req_amt, spending_changes=changes)
                if safe_with_changes >= req_amt - 1e-4:
                    change_parts = []
                    for c in changes:
                        if c['type'] == 'stop':
                            change_parts.append(f"stop:{c['event_id']}")
                        elif c['type'] == 'reduce_to':
                            change_parts.append(f"reduce_to:{c['event_id']}:{format_amt_clean(c['new_amount'])}")
                    
                    changes_str = "|".join(change_parts)
                    candidate_plans.append({
                        "affordability_status": "affordable_with_plan",
                        "recommended_payment_method": "full_payment",
                        "payment_plan": f"{req_date}:{format_amt_clean(req_amt)}",
                        "amount_safe_to_pay": base_safe_to_pay,
                        "earliest_date_for_full_payment": earliest_full_date if earliest_full_date else "",
                        "spending_changes": changes,
                        "spending_changes_needed": changes_str,
                        "total_payable_amount": req_amt,
                        "first_payment_date": req_date,
                        "completion_date": req_date,
                        "number_of_payments": 1,
                        "payment_option_id": "spending_change_plan",
                    })
                    break

        # ----------------------------------------------------
        # OPTION E: Wait (Single full payment on earliest_full_date)
        # ----------------------------------------------------
        if 'full_payment' in user_methods and earliest_full_date and earliest_full_date > req_date and earliest_full_date <= comp_date:
            candidate_plans.append({
                "affordability_status": "affordable_later",
                "recommended_payment_method": "wait",
                "payment_plan": f"{earliest_full_date}:{format_amt_clean(req_amt)}",
                "amount_safe_to_pay": base_safe_to_pay,
                "earliest_date_for_full_payment": earliest_full_date,
                "spending_changes": [],
                "spending_changes_needed": "none",
                "total_payable_amount": req_amt,
                "first_payment_date": earliest_full_date,
                "completion_date": earliest_full_date,
                "number_of_payments": 1,
                "payment_option_id": "wait_plan",
            })

        # Rank all candidate safe plans
        if candidate_plans:
            ranked = StrategyRanker.rank_candidate_plans(candidate_plans, comp_date)
            best_plan = ranked[0]
            return best_plan

        # Fallback: not_recommended
        return {
            "affordability_status": "not_affordable",
            "recommended_payment_method": "not_recommended",
            "payment_plan": "none",
            "amount_safe_to_pay": base_safe_to_pay,
            "earliest_date_for_full_payment": earliest_full_date if earliest_full_date else "",
            "spending_changes": [],
            "spending_changes_needed": "none",
            "total_payable_amount": 0.0,
            "first_payment_date": "",
            "completion_date": "",
            "number_of_payments": 0,
            "payment_option_id": "none",
        }
