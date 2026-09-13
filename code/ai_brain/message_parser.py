import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class MessageParser:
    """
    Extracts grounded financial facts and adjustments from messages.
    Supports multi-lingual notifications (English, Indonesian).
    """

    @staticmethod
    def parse_messages_for_user(user_id: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        user_msgs = [m for m in messages if m['user_id'] == user_id]
        # Sort by sent_at if available
        user_msgs.sort(key=lambda m: m.get('sent_at', ''))

        facts = {
            "salary_revisions": [],      # {new_amount, effective_date, currency, is_temporary}
            "salary_date_shifts": [],    # {new_date}
            "contract_ended": False,     # if True, seasonal/contract income ended
            "confirmed_invoices": [],    # {amount, currency, settlement_date}
            "rent_adjustments": [],      # {pct_change, is_increase}
            "unconfirmed_mentions": [],  # tracked to ensure they are NOT counted
        }

        for m in user_msgs:
            text = m['message_text']
            
            # 1. Contract ended / seasonal work stopped
            if re.search(r"contract has ended|no off-season income|employment record has ended", text, re.I):
                facts["contract_ended"] = True
                # Check if there is a remaining salary mentioned
                rem_sal_match = re.search(r"remaining confirmed monthly salary is (?:INR|EUR|USD|ZAR|IDR)?\s*([\d,\.]+)", text, re.I)
                if rem_sal_match:
                    amt = float(rem_sal_match.group(1).replace(",", ""))
                    facts["salary_revisions"].append({
                        "new_amount": amt,
                        "effective_date": None,
                        "description": "Remaining confirmed salary after contract end"
                    })

            # 2. Confirmed salary revision / first salary / temporary pay
            # Examples:
            # - "Gaji bulanan Anda naik menjadi IDR 42750000. Perubahan ini berlaku mulai 2025-08-15."
            # - "Your temporary monthly pay is EUR 1037.52."
            # - "Your first salary will be EUR 1661. The confirmed credit date is 2026-01-15."
            # - "Your monthly salary has increased to USD 2988. The change applies from 2026-07-15."
            # - "Your next salary is reduced to EUR 1422.85."
            sal_match = re.search(r"(?:gaji bulanan anda naik menjadi|gaji pokok yang dikonfirmasi adalah|gaji rutin anda.*?adalah|temporary monthly pay is|monthly salary has increased to|first salary will be|next salary is reduced to|regular salary of)\s*(?:INR|EUR|USD|ZAR|IDR)?\s*([\d,\.]+)", text, re.I)
            if sal_match:
                amt_str = sal_match.group(1).replace(",", "")
                try:
                    amt = float(amt_str)
                    date_match = re.search(r"(?:berlaku mulai|applies from|confirmed credit date is|resumes on|expected on)\s*(\d{4}-\d{2}-\d{2})", text, re.I)
                    eff_date = date_match.group(1) if date_match else None
                    facts["salary_revisions"].append({
                        "new_amount": amt,
                        "effective_date": eff_date,
                        "message_id": m['message_id'],
                        "sent_at": m.get('sent_at')
                    })
                except ValueError:
                    pass

            # 3. Salary payout date shift
            # "Your confirmed salary is now expected on 2024-09-23. This replaces the payroll date shown in the earlier update."
            shift_match = re.search(r"confirmed salary is now expected on (\d{4}-\d{2}-\d{2})", text, re.I)
            if shift_match:
                facts["salary_date_shifts"].append(shift_match.group(1))

            # 4. Confirmed invoice payout
            # "The client approved an invoice payment of INR 196000. Settlement is expected on 2024-12-15"
            inv_match = re.search(r"(?:approved an invoice payment of|menyetujui pembayaran faktur sebesar)\s*(?:INR|EUR|USD|ZAR|IDR)?\s*([\d,\.]+).*?(?:settlement is expected on|penyelesaian diperkirakan pada)\s*(\d{4}-\d{2}-\d{2})", text, re.I)
            if inv_match:
                try:
                    inv_amt = float(inv_match.group(1).replace(",", ""))
                    inv_date = inv_match.group(2)
                    facts["confirmed_invoices"].append({
                        "amount": inv_amt,
                        "settlement_date": inv_date,
                        "message_id": m['message_id']
                    })
                except ValueError:
                    pass

            # 5. Lease / rent percentage adjustment
            # "The renewed lease increases monthly rent by 12%."
            rent_match = re.search(r"increases monthly rent by (\d+(?:\.\d+)?)%", text, re.I)
            if rent_match:
                pct = float(rent_match.group(1))
                facts["rent_adjustments"].append({"pct_change": pct, "is_increase": True})

            # 6. Explicit unconfirmed mentions (bonuses pending, refund pending, prize processing, prize closed)
            if re.search(r"pending|belum disetujui|has not reached your account|still in payment processing|unrealized|market value has increased substantially|no units have been sold|there won't be another payment", text, re.I):
                facts["unconfirmed_mentions"].append({
                    "message_id": m['message_id'],
                    "text": text
                })

        return facts
