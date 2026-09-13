# Buy or Wait? — AI-Powered Financial Decision Agent

Starter codebase and submission package for **HackerRank Orchestrate (September 2026)**.

---

## 1. Setup & Run Instructions

### Prerequisites
- **Python**: Version `3.10` or higher
- **Dependencies**: Standard data processing libraries (`pandas`, `python-dateutil`)

### Installation
Clone or extract the repository and install required packages:
```bash
pip install pandas python-dateutil
```
*(No external API keys or `.env` files are required. The entire engine executes 100% locally and deterministically).*

### Running the Solution
To execute the full financial decision pipeline and generate `output.csv` (mirroring to both `dataset/output.csv` and root `output.csv`):
```bash
python code/main.py
```

### Running Benchmark Evaluation
To validate predictions and accuracy against the 25 public ground-truth examples in `dataset/sample_requests.csv`:
```bash
python code/evaluation/main.py
```

---

## 2. Approach Overview (3-Brain Architecture)

The system reconstructs a user's complete financial trajectory and recommends conservative, safe payment actions using a modular **3-Brain Architecture**:

```text
code/
├── main.py                          # CLI entry point generating output.csv & usage_report.md
├── config.py                        # Dataset paths and forecast constants
├── ai_brain/                        # Brain 1: Multimodal & Text Understanding
│   ├── message_parser.py            # Extracts salary updates, contract cancellations, and lease adjustments
│   ├── image_parser.py              # OCR & receipt parsing for events with missing amounts
│   └── request_analyzer.py          # Validates request parameters & constraints
├── financial_brain/                 # Brain 2: Deterministic Cashflow & Balance Engine
│   ├── state_builder.py             # Reconstructs user profile, priorities, and category rules
│   ├── currency.py                  # Fixed dated currency conversions (exchange_rates.csv)
│   ├── recurring_detector.py        # Identifies recurring cadence (rent, salary, subscriptions)
│   └── cashflow_engine.py           # 90-day daily balance simulation & safe-to-pay calculations
├── decision_brain/                  # Brain 3: Simulation, Safety & Strategy Ranking
│   ├── plan_simulator.py            # Evaluates full payment, installments, partial payment, and spending changes
│   ├── safety_checker.py            # Validates that balance >= minimum_balance_to_keep for all 90 days
│   ├── ranker.py                    # Ranks eligible plans using the hackathon's 6 priority rules
│   └── explanation_generator.py     # Generates concise, grounded explanations
├── evaluation/
│   ├── main.py                      # Evaluation benchmark against sample_requests.csv
│   ├── usage_tracker.py             # Generates compliant token & cost audit report
│   └── usage_report.md              # Required submission report (0 API tokens, $0.00 cost)
└── utils/
    └── data_loader.py               # Robust CSV loaders and typed dictionaries
```

---

### Brain 1: AI & Multimodal Understanding (`code/ai_brain/`)
- **Image Parsing (`image_parser.py`)**: Resolves financial events that have missing transaction amounts by extracting exact net pay/invoice totals from linked images in `dataset/media/images/`.
- **Message Parsing (`message_parser.py`)**: Gathers confirmed revisions (e.g., salary adjustments, effective dates, contract terminations) while strictly filtering out unconfirmed debits, credits, refunds, or speculative income per challenge rules.
- **Request Analysis (`request_analyzer.py`)**: Validates request constraints against user payment preferences and installment limits.

---

### Brain 2: Financial Brain (`code/financial_brain/`)
- **Currency Normalization (`currency.py`)**: Converts foreign currency transactions into the user's `home_currency` using exact settlement-date exchange rates in `exchange_rates.csv`.
- **Cashflow & Balance Simulation (`cashflow_engine.py`)**:
  - Reconstructs a daily financial timeline across a conservative **90-day forecast horizon**.
  - Immediately reserves all **pending debits**.
  - Counts confirmed salary only on scheduled settlement dates.
  - Projects recurring expenses (rent, utilities, loans, active subscriptions) on their historical cadence.
  - Computes `amount_safe_to_pay` and conservative `earliest_date_for_full_payment`.

---

### Brain 3: Decision Brain (`code/decision_brain/`)
- **Candidate Plan Generation (`plan_simulator.py`)**:
  1. `full_payment`: Safe immediately on `request_date` without spending changes, or safe with up to 3 permitted flexible adjustments (`stop:<id>`, `reduce_to:<id>:<amount>`).
  2. `installments`: Evaluates available provider payment options against user installment preferences, checking that all future installment dates preserve the minimum balance.
  3. `partial_payment`: Explores two-step payment schedules (`amount_safe_to_pay` on `request_date` + remaining balance on `earliest_date_for_full_payment`) if permitted by request and completed by `desired_completion_date`.
  4. `wait`: Evaluates full payment at `earliest_date_for_full_payment` if after `request_date`.
  5. `not_recommended`: Conservative fallback when no safe plan satisfies all financial constraints.
- **Safety Enforcement (`safety_checker.py`)**: Ensures the balance never breaches `minimum_balance_to_keep` on any day across the 90-day forecast.
- **Strict 6-Rule Strategy Ranking (`ranker.py`)**:
  1. Complete by `desired_completion_date`.
  2. Require no spending changes.
  3. Minimize total payment cost (principal + financing fees).
  4. Start payment earlier.
  5. Use fewer payments.
  6. Final deterministic tie-breaker (lowest `payment_option_id`).
- **Grounded Explanations (`explanation_generator.py`)**: Generates concise, audit-ready explanations specifying exact dates, amounts, and minimum balance protection.

---

## 3. Submission Outputs

- **`output.csv`**: Contains all 250 evaluation rows with the 8 required columns:
  `request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation`
- **`evaluation/usage_report.md`**: Summarizes model provider, calls, token metrics, and cost ($0.00 for pure deterministic execution).
