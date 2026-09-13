import os
import json
from typing import Dict, Any, List
from pathlib import Path

class UsageTracker:
    """
    Tracks model calls, input and output tokens, and computes cost estimates.
    Generates evaluation/usage_report.md per Hackathon requirement §6.5.
    
    For deterministic / zero-API rule-based executions, accurately records 0 model calls,
    0 tokens, and $0.00 runtime cost while providing full audit details.
    """
    def __init__(self):
        self.model_name = "None (Deterministic Algorithmic Engine)"
        self.model_provider = "None (100% Local / Zero Runtime API Calls)"
        self.total_requests = 0
        self.total_model_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.input_cost_per_1k = 0.0
        self.output_cost_per_1k = 0.0

    def record_request(self, input_tokens: int = 0, output_tokens: int = 0, calls: int = 0):
        self.total_requests += 1
        self.total_model_calls += calls
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def generate_report(self, output_file: Path):
        tot_tokens = self.total_input_tokens + self.total_output_tokens
        avg_tokens = tot_tokens / max(1, self.total_requests)
        tot_cost = (self.total_input_tokens / 1000.0) * self.input_cost_per_1k + (self.total_output_tokens / 1000.0) * self.output_cost_per_1k
        avg_cost = tot_cost / max(1, self.total_requests)

        report_md = f"""# Token Usage and Cost Analysis Report

## Summary
- **Evaluation Run**: HackerRank Orchestrate — Buy or Wait?
- **Total Requests Processed**: {self.total_requests}
- **Model Provider**: {self.model_provider}
- **Model Name**: {self.model_name}
- **Total Model Calls**: {self.total_model_calls}

## Token Metrics
| Metric | Value |
| --- | --- |
| Total Input Tokens | {self.total_input_tokens:,} |
| Total Output Tokens | {self.total_output_tokens:,} |
| Total Tokens | {tot_tokens:,} |
| Average Tokens per Request | {avg_tokens:.1f} |

## Cost Analysis
| Metric | Value (USD) |
| --- | --- |
| Estimated Input Cost | ${(self.total_input_tokens / 1000.0) * self.input_cost_per_1k:.4f} |
| Estimated Output Cost | ${(self.total_output_tokens / 1000.0) * self.output_cost_per_1k:.4f} |
| Total Estimated Cost | ${tot_cost:.4f} |
| Average Cost per Request | ${avg_cost:.6f} |

## System Architecture & Runtime Notes
- **Execution Mode**: 100% Deterministic offline execution.
- **Model Inference**: 0 runtime model API calls. No third-party LLM/VLM tokens consumed during evaluation.
- **Multimodal & Financial Engine**: Reconstructs cashflows, verifies all constraint invariants, matches dated exchange rates, and simulates plans via custom algorithmic logic.
- **Reproducibility**: Fully deterministic, zero latency overhead, zero financial API cost ($0.00).

---
*Generated automatically by the evaluation engine.*
"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        return report_md
