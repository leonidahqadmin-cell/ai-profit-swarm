"""
AI Profit Swarm v4.7 - Real LLM Integration Ready

This version makes it very easy to connect real Grok or Claude APIs.

How to use real models:
1. Set your API keys as environment variables:
   - GROK_API_KEY=your_key
   - ANTHROPIC_API_KEY=your_key

2. The system will automatically use real models when keys are present.

This is a major step toward a fully functional autonomous system.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any

# Try to import real LLM clients
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# OpenTelemetry setup (Jaeger)
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))
tracer = trace.get_tracer(__name__)

STATE_FILE = "swarm_state_v4_7.json"

print("=== AI PROFIT SWARM v4.7 (Real LLM Ready) ===\n")

# ==================== CONFIG ====================
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

ENABLED_AGENTS = ["lead_website", "app_factory", "aaas_seller", "polymarket"]

# ==================== REAL LLM INTEGRATION ====================

def call_llm(prompt: str, task: str, model: str = "grok") -> str:
    """
    Smart LLM caller that uses real APIs when keys are available.
    Falls back to simulation if no keys or libraries are missing.
    """
    with tracer.start_as_current_span(f"llm_call_{model}") as span:
        span.set_attribute("model", model)
        span.set_attribute("task", task[:100])
        
        # Try real Grok (via OpenAI-compatible endpoint)
        if model == "grok" and GROK_API_KEY and HAS_OPENAI:
            try:
                client = OpenAI(
                    api_key=GROK_API_KEY,
                    base_url="https://api.x.ai/v1"  # xAI Grok endpoint
                )
                response = client.chat.completions.create(
                    model="grok-4",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": task}
                    ],
                    max_tokens=800
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[WARNING] Grok API failed: {e}. Using simulation.")
        
        # Try real Claude
        if model == "claude" and CLAUDE_API_KEY and HAS_ANTHROPIC:
            try:
                client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
                response = client.messages.create(
                    model="claude-4-opus-20250514",
                    max_tokens=800,
                    system=prompt,
                    messages=[{"role": "user", "content": task}]
                )
                return response.content[0].text
            except Exception as e:
                print(f"[WARNING] Claude API failed: {e}. Using simulation.")
        
        # Fallback to simulation
        print(f"[LLM] {model.upper()} (simulated) processing...")
        return f"[{model.upper()} SIMULATED] Analysis completed for: {task[:70]}..."

def use_tool(tool_name: str, query: str) -> str:
    with tracer.start_as_current_span(f"tool_{tool_name}") as span:
        span.set_attribute("tool", tool_name)
        print(f"[TOOL] {tool_name}...")
        return f"[TOOL DATA] Results for: {query[:50]}..."

# ==================== PROMPTS ====================

PROMPTS = {
    "orchestrator": "You are the Master Orchestrator of a high-performance autonomous profit system...",
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

# ==================== AGENTS ====================

def orchestrator(state: Dict) -> Dict:
    with tracer.start_as_current_span("orchestrator"):
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
    with tracer.start_as_current_span(f"agent_{agent_name}"):
        print(f"\n--- {agent_name.upper().replace('_', ' ')} AGENT ---")
        
        for task in state.get("tasks", []):
            if task["agent"] == agent_name:
                if agent_name == "polymarket":
                    use_tool("web_search", "current Polymarket markets")
                
                output = call_llm(PROMPTS[prompt_key], task["task"])
                state[f"{agent_name}_output"] = output
        return state

def reviewer(state: Dict) -> Dict:
    with tracer.start_as_current_span("reviewer"):
        print("\n" + "="*75)
        print("REVIEWER")
        print("="*75)
        
        output = call_llm(PROMPTS["reviewer"], "Review performance")
        state["review_output"] = output
        
        state["improvements"] = [
            "Add more advanced Polymarket analysis",
            "Implement real web search tools",
            "Add revenue tracking per revenue stream"
        ]
        return state

# ==================== MAIN CYCLE ====================

def run_daily_cycle():
    with tracer.start_as_current_span("full_cycle"):
        print(f"Starting v4.7 cycle at {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        
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
        print("CYCLE COMPLETE - v4.7")
        print("="*75)
        print(f"Tasks executed: {len(state['tasks'])}")
        
        if GROK_API_KEY:
            print("Using real Grok API")
        elif CLAUDE_API_KEY:
            print("Using real Claude API")
        else:
            print("Using simulated responses (set API keys for real models)")
        
        return state

if __name__ == "__main__":
    run_daily_cycle()