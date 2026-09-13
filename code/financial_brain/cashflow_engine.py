from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

from code.financial_brain.currency import CurrencyConverter
from code.config import FORECAST_DAYS

def add_days(date_str: str, days: int) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)
    return dt.strftime("%Y-%m-%d")

def get_day_of_month(date_str: str) -> int:
    return datetime.strptime(date_str, "%Y-%m-%d").day

class CashflowEngine:
    def __init__(self, converter: CurrencyConverter):
        self.converter = converter

    def reconstruct_user_commitments(
        self,
        user_id: str,
        profile: Dict[str, Any],
        events: List[Dict[str, Any]],
        message_facts: Dict[str, Any],
        request_date: str,
    ) -> Dict[str, Any]:
        home_curr = profile['home_currency']
        u_events = [e for e in events if e['user_id'] == user_id]
        protect_cats = set([c.lower() for c in profile.get('expense_categories_to_protect', [])])

        settled_past = []
        pending_future = []
        for e in u_events:
            status = e['status'].lower()
            if status in ['cancelled', 'failed', 'unrealized']:
                continue
            
            s_date = e['settlement_date'] or e['event_date']
            amt = e['amount']
            if amt is None:
                continue

            amt_home = self.converter.convert(amt, e['currency'], home_curr, s_date)
            ev_copy = dict(e)
            ev_copy['amount_home'] = amt_home

            if status == 'pending':
                if e['direction'].lower() == 'debit':
                    pending_future.append(ev_copy)
            elif status == 'scheduled':
                if s_date >= request_date:
                    pending_future.append(ev_copy)
            elif status == 'settled':
                if s_date < request_date:
                    settled_past.append(ev_copy)
                else:
                    pending_future.append(ev_copy)

        # 1. Fixed recurring commitments
        FIXED_COMMITMENTS = {
            'rent', 'salary', 'debt_repayment', 'utilities',
            'music_subscription', 'delivery_membership', 'cloud_storage',
            'streaming', 'gym', 'insurance', 'family_support', 'education',
            'housing', 'subscription'
        }

        streams = defaultdict(list)
        for e in settled_past:
            cat = e['category'].lower()
            ev_type = e['event_type'].lower()
            if cat in FIXED_COMMITMENTS or ev_type in ['debt_payment', 'subscription', 'income']:
                key = (e['direction'].lower(), cat, e['description'])
                streams[key].append(e)

        recurring_streams = []
        for (direction, category, desc), ev_list in streams.items():
            ev_list.sort(key=lambda x: x['settlement_date'])
            doms = [get_day_of_month(x['settlement_date']) for x in ev_list]
            dom = max(set(doms), key=doms.count)
            
            recent = ev_list[-3:]
            avg_amt = sum(x['amount_home'] for x in recent) / len(recent)
            
            flexibility = ev_list[-1].get('flexibility', 'fixed')
            min_allowed = ev_list[-1].get('minimum_allowed_amount')
            last_event_id = ev_list[-1].get('event_id')

            recurring_streams.append({
                "direction": direction,
                "category": category,
                "description": desc,
                "day_of_month": dom,
                "amount_home": avg_amt,
                "flexibility": flexibility,
                "minimum_allowed_amount": min_allowed,
                "last_event_id": last_event_id,
                "history_count": len(ev_list),
            })

        # 2. Protected variable spending (e.g. groceries, transport)
        VARIABLE_CATS = {'groceries', 'transport', 'dining', 'healthcare', 'shopping'}
        for vcat in VARIABLE_CATS:
            if vcat in protect_cats:
                cat_events = [e for e in settled_past if e['category'].lower() == vcat]
                if cat_events:
                    recent_events = cat_events[-8:]
                    tot_amt = sum(e['amount_home'] for e in recent_events)
                    weekly_amt = tot_amt / max(1, (len(recent_events) / 2.0))
                    for dom in [7, 14, 21, 28]:
                        recurring_streams.append({
                            "direction": "debit",
                            "category": vcat,
                            "description": f"Essential {vcat}",
                            "day_of_month": dom,
                            "amount_home": weekly_amt / 4.0,
                            "flexibility": "fixed",
                            "minimum_allowed_amount": None,
                            "last_event_id": f"essential_{vcat}_{dom}",
                            "history_count": len(cat_events),
                        })

        # Apply message modifications
        if message_facts.get('contract_ended'):
            sal_rev = message_facts.get('salary_revisions')
            if sal_rev:
                for s in recurring_streams:
                    if s['category'] == 'salary':
                        s['amount_home'] = self.converter.convert(sal_rev[-1]['new_amount'], home_curr, home_curr, request_date)
            else:
                recurring_streams = [s for s in recurring_streams if s['category'] != 'salary']
        else:
            for rev in message_facts.get('salary_revisions', []):
                new_amt = rev['new_amount']
                for s in recurring_streams:
                    if s['category'] == 'salary':
                        s['amount_home'] = self.converter.convert(new_amt, home_curr, home_curr, request_date)
                if not any(s['category'] == 'salary' for s in recurring_streams):
                    sal_day = 15
                    if message_facts.get('salary_date_shifts'):
                        sal_day = get_day_of_month(message_facts['salary_date_shifts'][-1])
                    recurring_streams.append({
                        "direction": "credit",
                        "category": "salary",
                        "description": "Confirmed salary",
                        "day_of_month": sal_day,
                        "amount_home": new_amt,
                        "flexibility": "fixed",
                        "minimum_allowed_amount": None,
                        "last_event_id": "msg_salary",
                        "history_count": 1,
                    })

        for rent_adj in message_facts.get('rent_adjustments', []):
            pct = rent_adj['pct_change']
            for s in recurring_streams:
                if s['category'] == 'rent':
                    s['amount_home'] *= (1.0 + pct / 100.0)

        for shift_date in message_facts.get('salary_date_shifts', []):
            shift_dom = get_day_of_month(shift_date)
            for s in recurring_streams:
                if s['category'] == 'salary':
                    s['day_of_month'] = shift_dom

        return {
            "user_id": user_id,
            "home_currency": home_curr,
            "start_balance": profile['current_available_balance'],
            "minimum_balance_to_keep": profile['minimum_balance_to_keep'],
            "recurring_streams": recurring_streams,
            "pending_future_events": pending_future,
            "confirmed_invoices": message_facts.get('confirmed_invoices', []),
        }

    def simulate_timeline(
        self,
        commitments: Dict[str, Any],
        request_date: str,
        spending_changes: Optional[List[Dict[str, Any]]] = None,
        forecast_days: int = FORECAST_DAYS,
    ) -> List[Dict[str, Any]]:
        start_dt = datetime.strptime(request_date, "%Y-%m-%d")
        curr_balance = commitments['start_balance']
        timeline = []

        stopped_events = set()
        stopped_categories = set()
        reduced_events = {}
        if spending_changes:
            for sc in spending_changes:
                if sc['type'] == 'stop':
                    stopped_events.add(sc['event_id'])
                    if 'category' in sc:
                        stopped_categories.add(sc['category'])
                elif sc['type'] == 'reduce_to':
                    reduced_events[sc['event_id']] = sc['new_amount']

        events_by_date = defaultdict(list)
        for e in commitments['pending_future_events']:
            s_date = e.get('settlement_date') or e.get('event_date')
            events_by_date[s_date].append(e)

        for inv in commitments.get('confirmed_invoices', []):
            s_date = inv['settlement_date']
            events_by_date[s_date].append({
                'direction': 'credit',
                'amount_home': self.converter.convert(inv['amount'], commitments['home_currency'], commitments['home_currency'], s_date),
                'category': 'income',
                'description': 'Confirmed invoice payout'
            })

        for d_idx in range(forecast_days + 1):
            cur_dt = start_dt + timedelta(days=d_idx)
            cur_date_str = cur_dt.strftime("%Y-%m-%d")
            dom = cur_dt.day

            if cur_date_str in events_by_date:
                for ev in events_by_date[cur_date_str]:
                    amt = ev['amount_home']
                    if ev['direction'].lower() == 'debit':
                        ev_id = ev.get('event_id')
                        if ev_id in stopped_events:
                            amt = 0.0
                        elif ev_id in reduced_events:
                            amt = min(amt, reduced_events[ev_id])
                        curr_balance -= amt
                    elif ev['direction'].lower() == 'credit':
                        curr_balance += amt

            if d_idx > 0:
                for s in commitments['recurring_streams']:
                    max_days_in_month = calendar.monthrange(cur_dt.year, cur_dt.month)[1]
                    stream_dom = min(s['day_of_month'], max_days_in_month)
                    
                    if dom == stream_dom:
                        amt = s['amount_home']
                        ev_id = s.get('last_event_id')
                        cat = s.get('category')
                        
                        if s['direction'] == 'debit':
                            if ev_id in stopped_events or cat in stopped_categories:
                                amt = 0.0
                            elif ev_id in reduced_events:
                                amt = min(amt, reduced_events[ev_id])
                            curr_balance -= amt
                        elif s['direction'] == 'credit':
                            curr_balance += amt

            timeline.append({
                "day_index": d_idx,
                "date": cur_date_str,
                "balance": curr_balance
            })

        return timeline

    def compute_safe_to_pay(
        self,
        commitments: Dict[str, Any],
        request_date: str,
        requested_amount: float,
        spending_changes: Optional[List[Dict[str, Any]]] = None,
    ) -> float:
        timeline = self.simulate_timeline(commitments, request_date, spending_changes=spending_changes)
        min_keep = commitments['minimum_balance_to_keep']
        min_margin = min(day['balance'] - min_keep for day in timeline)
        amount_safe = max(0.0, min(requested_amount, min_margin))
        return round(amount_safe, 2)

    def find_earliest_full_payment_date(
        self,
        commitments: Dict[str, Any],
        request_date: str,
        requested_amount: float,
        forecast_days: int = FORECAST_DAYS,
    ) -> str:
        timeline = self.simulate_timeline(commitments, request_date, forecast_days=forecast_days)
        min_keep = commitments['minimum_balance_to_keep']
        
        for d_idx, entry in enumerate(timeline):
            is_safe = True
            for future_entry in timeline[d_idx:]:
                if (future_entry['balance'] - requested_amount) < min_keep - 1e-4:
                    is_safe = False
                    break
            if is_safe:
                return entry['date']
        return ""
