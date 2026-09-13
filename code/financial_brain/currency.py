from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

class CurrencyConverter:
    """
    Fixed dated exchange rates converter supporting exact and closest date matching,
    inverse rates, and cross rates if necessary.
    """
    def __init__(self, exchange_rates: List[Dict[str, Any]]):
        self.rates_by_pair: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}
        for r in exchange_rates:
            pair = (r['from_currency'], r['to_currency'])
            if pair not in self.rates_by_pair:
                self.rates_by_pair[pair] = []
            self.rates_by_pair[pair].append((r['rate_date'], r['rate']))
            
        # Sort each pair's rates chronologically
        for pair in self.rates_by_pair:
            self.rates_by_pair[pair].sort(key=lambda x: x[0])

    def get_rate(self, from_curr: str, to_curr: str, date_str: str) -> float:
        if from_curr == to_curr:
            return 1.0

        pair = (from_curr, to_curr)
        inv_pair = (to_curr, from_curr)

        # 1. Direct pair match
        if pair in self.rates_by_pair:
            rates = self.rates_by_pair[pair]
            # Exact match
            for r_date, r_val in rates:
                if r_date == date_str:
                    return r_val
            # Closest preceding or nearest date
            best_rate = rates[-1][1]
            for r_date, r_val in reversed(rates):
                if r_date <= date_str:
                    best_rate = r_val
                    break
            return best_rate

        # 2. Inverse pair match
        if inv_pair in self.rates_by_pair:
            inv_rates = self.rates_by_pair[inv_pair]
            for r_date, r_val in inv_rates:
                if r_date == date_str:
                    return 1.0 / r_val if r_val != 0 else 1.0
            best_rate = inv_rates[-1][1]
            for r_date, r_val in reversed(inv_rates):
                if r_date <= date_str:
                    best_rate = r_val
                    break
            return 1.0 / best_rate if best_rate != 0 else 1.0

        # 3. Cross currency via USD / EUR
        for pivot in ['USD', 'EUR']:
            if (from_curr, pivot) in self.rates_by_pair or (pivot, from_curr) in self.rates_by_pair:
                if (pivot, to_curr) in self.rates_by_pair or (to_curr, pivot) in self.rates_by_pair:
                    r1 = self.get_rate(from_curr, pivot, date_str)
                    r2 = self.get_rate(pivot, to_curr, date_str)
                    return r1 * r2

        return 1.0

    def convert(self, amount: float, from_curr: str, to_curr: str, date_str: str) -> float:
        if amount is None:
            return 0.0
        rate = self.get_rate(from_curr, to_curr, date_str)
        return amount * rate
