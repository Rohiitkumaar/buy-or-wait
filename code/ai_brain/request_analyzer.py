from typing import Dict, Any, List

class RequestAnalyzer:
    """
    Analyzes user request requirements, intent, and constraints.
    """
    @staticmethod
    def analyze_request(request: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request['request_id']
        user_id = request['user_id']
        req_amt = request['requested_amount']
        req_date = request['request_date']
        comp_date = request['desired_completion_date']
        allows_partial = request['allows_partial_payment']
        
        user_methods = profile.get('payment_methods_user_will_consider', [])
        max_inst_months = profile.get('max_installment_months')
        
        can_consider_full = 'full_payment' in user_methods
        can_consider_partial = 'partial_payment' in user_methods and allows_partial
        can_consider_installments = 'installments' in user_methods and (max_inst_months is None or max_inst_months > 0)
        
        return {
            "request_id": req_id,
            "user_id": user_id,
            "requested_amount": req_amt,
            "request_date": req_date,
            "desired_completion_date": comp_date,
            "allows_partial_payment": allows_partial,
            "can_consider_full": can_consider_full,
            "can_consider_partial": can_consider_partial,
            "can_consider_installments": can_consider_installments,
            "max_installment_months": max_inst_months,
            "home_currency": profile.get('home_currency', 'USD'),
            "minimum_balance_to_keep": profile.get('minimum_balance_to_keep', 0.0),
        }
