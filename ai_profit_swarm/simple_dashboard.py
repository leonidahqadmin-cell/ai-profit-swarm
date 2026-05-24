"""
Simple Text Dashboard for AI Profit Swarm

Run this to see current performance and history.
"""

import json
import os
from datetime import datetime

STATE_FILE = "swarm_state_v4.json"

def show_dashboard():
    print("\n" + "="*70)
    print("AI PROFIT SWARM - PERFORMANCE DASHBOARD")
    print("="*70)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    if not os.path.exists(STATE_FILE):
        print("\nNo state file found. Run the swarm first to generate data.")
        return
    
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    
    metrics = state.get("metrics", {})
    history = state.get("history", [])
    
    print("\n--- LIFETIME METRICS ---")
    print(f"Total Cycles Run:     {metrics.get('total_cycles', 0)}")
    print(f"Total Tasks Completed: {metrics.get('total_tasks_completed', 0)}")
    
    if history:
        print("\n--- RECENT CYCLES (Last 5) ---")
        for entry in history[-5:]:
            print(f"\n{entry['date'][:16]}")
            print(f"  Tasks completed: {entry.get('tasks_completed', 'N/A')}")
            if entry.get('improvements'):
                print(f"  Top improvement: {entry['improvements'][0][:60]}...")
    
    print("\n" + "="*70)
    print("Dashboard complete. Run the swarm regularly to see improving metrics.")
    print("="*70 + "\n")

if __name__ == "__main__":
    show_dashboard()