#!/usr/bin/env python3
"""
Main entry point for KVM Backup System
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from cli import app
    app()
