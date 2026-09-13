import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
MEDIA_DIR = DATASET_DIR / "media" / "images"
CODE_DIR = BASE_DIR / "code"
EVALUATION_DIR = CODE_DIR / "evaluation"

# Data file paths
FINANCIAL_PROFILES_PATH = DATASET_DIR / "financial_profiles.csv"
FINANCIAL_EVENTS_PATH = DATASET_DIR / "financial_events.csv"
EXCHANGE_RATES_PATH = DATASET_DIR / "exchange_rates.csv"
REQUESTS_PATH = DATASET_DIR / "requests.csv"
SAMPLE_REQUESTS_PATH = DATASET_DIR / "sample_requests.csv"
REQUEST_PAYMENT_OPTIONS_PATH = DATASET_DIR / "request_payment_options.csv"
MESSAGES_PATH = DATASET_DIR / "messages.csv"
IMAGES_PATH = DATASET_DIR / "images.csv"
OUTPUT_PATH = DATASET_DIR / "output.csv"
ROOT_OUTPUT_PATH = BASE_DIR / "output.csv"

# Configuration constants
FORECAST_DAYS = 90
MAX_SPENDING_CHANGES = 3
DEFAULT_CURRENCY = "USD"
