from typing import Dict, List, Any, Optional

class StrategyRanker:
    """
    Ranks candidate safe plans using the hackathon's exact 6 priority rules.
    """
    @staticmethod
    def plan_rank_key(plan: Dict[str, Any], desired_completion_date: str) -> tuple:
        # 1. Complete by desired_completion_date (0 if completed on/before deadline, 1 if later)
        last_date = plan.get('completion_date', '9999-99-99')
        meets_deadline = 0 if last_date <= desired_completion_date else 1
        
        # 2. Require no spending changes (0 if no changes, 1 if requires changes)
        num_changes = len(plan.get('spending_changes', []))
        has_changes = 0 if num_changes == 0 else 1
        
        # 3. Minimize total amount paid (including fees)
        total_paid = plan.get('total_payable_amount', float('inf'))
        
        # 4. Start payment earlier (first payment date)
        first_date = plan.get('first_payment_date', '9999-99-99')
        
        # 5. Use fewer payments
        num_payments = plan.get('number_of_payments', 999)
        
        # 6. Final tie-breaker: lowest payment_option_id
        opt_id = plan.get('payment_option_id', 'zzz')
        
        return (meets_deadline, has_changes, total_paid, first_date, num_payments, opt_id)

    @classmethod
    def rank_candidate_plans(cls, candidate_plans: List[Dict[str, Any]], desired_completion_date: str) -> List[Dict[str, Any]]:
        return sorted(candidate_plans, key=lambda p: cls.plan_rank_key(p, desired_completion_date))
