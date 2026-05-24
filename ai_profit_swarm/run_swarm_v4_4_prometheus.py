"""
AI Profit Swarm v4.4 - With Prometheus Metrics

This version adds Prometheus metrics for monitoring:
- Total cycles run
- Total tasks completed
- Tasks completed per agent
- Last cycle timestamp

To view metrics:
1. Run this script (it starts a metrics server on port 8000)
2. Visit http://localhost:8000/metrics in your browser or Prometheus

This is a big step toward production observability.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
from prometheus_client import start_http_server, Counter, Gauge, Histogram

STATE_FILE = "swarm_state_v4_4.json"

print("=== AI PROFIT SWARM v4.4 (with Prometheus Metrics) ===\n")

# ==================== PROMETHEUS METRICS ====================

# Define metrics
CYCLES_TOTAL = Counter('swarm_cycles_total', 'Total number of swarm cycles run')
TASKS_TOTAL = Counter('swarm_tasks_total', 'Total number of tasks completed across all agents')
TASKS_BY_AGENT = Counter('swarm_tasks_by_agent_total', 'Tasks completed per agent', ['agent'])
LAST_CYCLE_TIMESTAMP = Gauge('swarm_last_cycle_timestamp', 'Unix timestamp of the last completed cycle')
CYCLE_DURATION = Histogram('swarm_cycle_duration_seconds', 'Time taken to complete one full cycle')

# ==================== CONFIG ====================
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

ENABLED_AGENTS = ["lead_website", "app_factory", "aaas_seller", "polymarket"]

# ==================== PROMPTS ====================

PROMPTS = {
    "orchestrator": "You are the Master Orchestrator... [shortened for brevity]",
    "lead_website": "You are an expert Lead Generation + Website Building Agent...",
    "app_factory": "You are the App & SaaS Factory Agent...",
    "aaas_seller": "You are the AI Agent as a Service Sales Agent...",
    "polymarket": "You are the Polymarket Research & Edge Agent...",
    "reviewer": "You are the Reviewer & Continuous Improvement Agent..."
}

# ==================== STATE MANAGEMENT ====================

def load_state() -> Dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {
        "history": [],
        "metrics": {"total_cycles": 0, "total_tasks_completed": 0}
    }

def save_state(state: Dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ==================== LLM & TOOL (Simulated) ====================

def call_llm(prompt: str, task: str, model: str = "grok") -> str:
    print(f"[LLM] {model.upper()} processing...")
    return f"[{model.upper()} OUTPUT] Completed: {task[:60]}..."

def use_tool(tool_name: str, query: str) -> str:
    print(f"[TOOL] {tool_name}...")
    return f"[TOOL DATA] Results for: {query[:50]}..."

# ==================== AGENTS ====================

def orchestrator(state: Dict) -> Dict:
    print("\n" + "="*75)
    print("MASTER ORCHESTRATOR")
    print("="*75)
    
    output = call_llm(PROMPTS["orchestrator"], "Plan today's high-ROI tasks")
    state["orchestrator_output"] = output
    
    state["tasks"] = [
        {"agent": "lead_website", "task": "Research 30 businesses with website problems"},
        {"agent": "app_factory", "task": "Develop one high-potential micro-SaaS"},
        {"agent": "aaas_seller", "task": "Send AaaS offers to 10 businesses"},
        {"agent": "polymarket", "task": "Research Polymarket markets and find edges"},
    ]
    state["tasks"] = [t for t in state["tasks"] if t["agent"] in ENABLED_AGENTS]
    return state

def execute_agent(state: Dict, agent_name: str, prompt_key: str) -> Dict:
    print(f"\n--- {agent_name.upper().replace('_', ' ')} ---")
    
    for task in state.get("tasks", []):
        if task["agent"] == agent_name:
            if agent_name == "polymarket":
                use_tool("web_search", "current Polymarket markets")
            
            output = call_llm(PROMPTS[prompt_key], task["task"])
            state[f"{agent_name}_output"] = output
            
            # Record Prometheus metric
            TASKS_BY_AGENT.labels(agent=agent_name).inc()
    return state

def reviewer(state: Dict) -> Dict:
    print("\n" + "="*75)
    print("REVIEWER")
    print("="*75)
    
    output = call_llm(PROMPTS["reviewer"], "Review performance")
    state["review_output"] = output
    
    state["improvements"] = [
        "Connect real LLM APIs",
        "Add real tool integration",
        "Improve per-agent metrics"
    ]
    return state

# ==================== MAIN CYCLE ====================

def run_daily_cycle():
    print(f"Starting v4.4 cycle at {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    persistent = load_state()
    
    state: Dict[str, Any] = {
        "date": datetime.now().isoformat(),
        "tasks": [],
        "improvements": []
    }
    
    import time
    start_time = time.time()
    
    state = orchestrator(state)
    state = execute_agent(state, "lead_website", "lead_website")
    state = execute_agent(state, "app_factory", "app_factory")
    state = execute_agent(state, "aaas_seller", "aaas_seller")
    state = execute_agent(state, "polymarket", "polymarket")
    state = reviewer(state)
    
    duration = time.time() - start_time
    CYCLE_DURATION.observe(duration)
    
    # Update Prometheus metrics
    CYCLES_TOTAL.inc()
    TASKS_TOTAL.inc(len(state["tasks"]))
    LAST_CYCLE_TIMESTAMP.set(time.time())
    
    # Update persistent state
    persistent["metrics"] = persistent.get("metrics", {"total_cycles": 0, "total_tasks_completed": 0})
    persistent["metrics"]["total_cycles"] += 1
    persistent["metrics"]["total_tasks_completed"] += len(state["tasks"])
    
    persistent["history"].append({
        "date": state["date"],
        "tasks": len(state["tasks"]),
        "duration_seconds": round(duration, 2)
    })
    
    if len(persistent["history"]) > 20:
        persistent["history"] = persistent["history"][-20:]
    
    save_state(persistent)
    
    print("\n" + "="*75)
    print("CYCLE COMPLETE - v4.4 (Prometheus Enabled)")
    print("="*75)
    print(f"Tasks executed: {len(state['tasks'])}")
    print(f"Cycle duration: {round(duration, 2)} seconds")
    print(f"\nPrometheus metrics available at: http://localhost:8000/metrics")
    
    return state

if __name__ == "__main__":
    # Start Prometheus metrics server on port 8000
    start_http_server(8000)
    print("Prometheus metrics server started on port 8000")
    print("View metrics at: http://localhost:8000/metrics\n")
    
    run_daily_cycle()