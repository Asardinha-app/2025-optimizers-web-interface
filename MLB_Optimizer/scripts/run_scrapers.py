#!/usr/bin/env python3
"""CLI entry point for Data Scrapers"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from data.scrapers import AwesemoScraper, LabsScraper, SaberSimScraper, TheBatScraper

def main():
    """Run the Data Scrapers"""
    # TODO: Add command line argument parsing
    print("Data Scrapers CLI - Coming Soon")

if __name__ == "__main__":
    main()