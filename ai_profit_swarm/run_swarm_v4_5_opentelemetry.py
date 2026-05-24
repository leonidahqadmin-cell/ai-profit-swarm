"""
AI Profit Swarm v4.5 - OpenTelemetry Integration

This version adds OpenTelemetry tracing for better observability.

What you get:
- Distributed tracing across agents
- Visibility into how long each agent takes
- Easy to export traces to Jaeger, Grafana Tempo, etc.

To run with tracing:
1. Install requirements
2. Run this script
3. Traces will be printed to console (can be sent to a collector)

This significantly improves debugging and performance analysis.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Set up OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export traces to console (easy for testing)
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

STATE_FILE = "swarm_state_v4_5.json"

print("=== AI PROFIT SWARM v4.5 (OpenTelemetry Enabled) ===\n")

# ==================== CONFIG ====================
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

ENABLED_AGENTS = ["lead_website", "app_factory", "aaas_seller", "polymarket"]

# ==================== PROMPTS ====================

PROMPTS = {
    "orchestrator": "You are the Master Orchestrator...",
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
    return {"history": [], "metrics": {"total_cycles": 0, "total_tasks_completed": 0}}

def save_state(state: Dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ==================== LLM & TOOL ====================

def call_llm(prompt: str, task: str, model: str = "grok") -> str:
    with tracer.start_as_current_span(f"llm_call_{model}") as span:
        span.set_attribute("model", model)
        span.set_attribute("task", task[:100])
        print(f"[LLM] {model.upper()} processing...")
        return f"[{model.upper()} OUTPUT] Completed: {task[:60]}..."

def use_tool(tool_name: str, query: str) -> str:
    with tracer.start_as_current_span(f"tool_{tool_name}") as span:
        span.set_attribute("tool", tool_name)
        span.set_attribute("query", query[:80])
        print(f"[TOOL] {tool_name}...")
        return f"[TOOL DATA] Results for: {query[:50]}..."

# ==================== AGENTS WITH TRACING ====================

def orchestrator(state: Dict) -> Dict:
    with tracer.start_as_current_span("orchestrator") as span:
        print("\n" + "="*75)
        print("MASTER ORCHESTRATOR")
        print("="*75)
        
        output = call_llm(PROMPTS["orchestrator"], "Plan today's tasks")
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
    with tracer.start_as_current_span(f"agent_{agent_name}") as span:
        span.set_attribute("agent", agent_name)
        print(f"\n--- {agent_name.upper().replace('_', ' ')} AGENT ---")
        
        for task in state.get("tasks", []):
            if task["agent"] == agent_name:
                if agent_name == "polymarket":
                    use_tool("web_search", "current Polymarket markets")
                
                output = call_llm(PROMPTS[prompt_key], task["task"])
                state[f"{agent_name}_output"] = output
        return state

def reviewer(state: Dict) -> Dict:
    with tracer.start_as_current_span("reviewer") as span:
        print("\n" + "="*75)
        print("REVIEWER")
        print("="*75)
        
        output = call_llm(PROMPTS["reviewer"], "Review performance")
        state["review_output"] = output
        
        state["improvements"] = [
            "Connect real LLM APIs",
            "Add real tool integration",
            "Improve tracing and metrics"
        ]
        return state

# ==================== MAIN CYCLE ====================

def run_daily_cycle():
    with tracer.start_as_current_span("full_cycle") as span:
        print(f"Starting v4.5 cycle at {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
        persistent = load_state()
        
        state: Dict[str, Any] = {
            "date": datetime.now().isoformat(),
            "tasks": [],
            "improvements": []
        }
        
        state = orchestrator(state)
        state = execute_agent(state, "lead_website", "lead_website")
        state = execute_agent(state, "app_factory", "app_factory")
        state = execute_agent(state, "aaas_seller", "aaas_seller")
        state = execute_agent(state, "polymarket", "polymarket")
        state = reviewer(state)
        
        # Update metrics
        persistent["metrics"] = persistent.get("metrics", {"total_cycles": 0, "total_tasks_completed": 0})
        persistent["metrics"]["total_cycles"] += 1
        persistent["metrics"]["total_tasks_completed"] += len(state["tasks"])
        
        persistent["history"].append({
            "date": state["date"],
            "tasks": len(state["tasks"])
        })
        
        if len(persistent["history"]) > 20:
            persistent["history"] = persistent["history"][-20:]
        
        save_state(persistent)
        
        print("\n" + "="*75)
        print("CYCLE COMPLETE - v4.5 (OpenTelemetry)")
        print("="*75)
        print(f"Tasks executed: {len(state['tasks'])}")
        print("\nTraces have been generated (visible in console output above).")
        print("For production, configure an OTLP exporter to send traces to Jaeger/Grafana.")
        
        return state

if __name__ == "__main__":
    run_daily_cycle()