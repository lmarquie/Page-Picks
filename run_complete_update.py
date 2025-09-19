#!/usr/bin/env python3
"""
Simple runner for the complete update
"""

import subprocess
import sys
import os

def run_update():
    """Run the complete update"""
    print("🏈 Running complete 2025 NFL update...")
    print("=" * 50)
    
    try:
        # Run the update script
        result = subprocess.run([sys.executable, "update_2025_and_injuries.py"], 
                              capture_output=True, text=True)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Complete update finished successfully!")
        else:
            print(f"\n❌ Update failed with return code {result.returncode}")
            
    except Exception as e:
        print(f"❌ Error running update: {e}")

if __name__ == "__main__":
    run_update()
