#!/usr/bin/env python3
"""
Entry point for the invoice‐processing pipeline.
Allows invoking the orchestrator with an optional number of days for the report window.
Usage: python -m src [period_days]
"""
import sys

def main():
    # Delay import until here so that -m src sets up the module path correctly
    from orchestrator import orchestrate

    # Default reporting window
    period_days = 1
    if len(sys.argv) > 1:
        try:
            period_days = int(sys.argv[1])
        except ValueError:
            print("Error: period_days must be an integer")
            sys.exit(1)

    orchestrate(period_days)


if __name__ == "__main__":
    main()
