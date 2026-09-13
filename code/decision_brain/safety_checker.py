from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

class SafetyChecker:
    @staticmethod
    def is_plan_safe(
        baseline_timeline: List[Dict[str, Any]],
        payment_schedule: List[Tuple[str, float]],
        min_balance_to_keep: float,
        desired_completion_date: str,
        request_date: str,
    ) -> Tuple[bool, float]:
        """
        Checks whether applying payment_schedule to baseline_timeline keeps balance >= min_balance_to_keep
        for all 90 days, and checks if completed by desired_completion_date.
        Returns (is_safe, min_margin_across_period).
        """
        if not payment_schedule:
            # Plan with no payments (like wait or not_recommended)
            min_margin = min(d['balance'] - min_balance_to_keep for d in baseline_timeline)
            return True, min_margin

        # Map payments by date
        payments_by_date = defaultdict(float)
        for p_date, p_amt in payment_schedule:
            payments_by_date[p_date] += p_amt

        # Check completion date
        last_payment_date = max(p_date for p_date, _ in payment_schedule)
        completes_by_deadline = last_payment_date <= desired_completion_date

        # Simulate deduction
        cum_deduction = 0.0
        min_margin = float('inf')
        
        for entry in baseline_timeline:
            cur_date = entry['date']
            if cur_date in payments_by_date:
                cum_deduction += payments_by_date[cur_date]
            
            projected_bal = entry['balance'] - cum_deduction
            margin = projected_bal - min_balance_to_keep
            if margin < min_margin:
                min_margin = margin
                
            if margin < -1e-4:
                return False, min_margin

        return True, min_margin
