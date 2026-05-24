"""
AI Profit Swarm v5.2 - Deployment Optimized (Minimal Human Effort)

This version is built for easy deployment on Railway / Render / similar platforms.

Key features:
- Clean logging (easy to see what happened in each cycle)
- Supports both Scheduled runs (recommended) and Continuous mode
- Simple configuration via environment variables
- Robust error handling
- Production-friendly structure
- Minimal setup required from you

How to use:
1. Set environment variables (especially GROK_API_KEY)
2. Deploy to Railway (or similar)
3. Set it to run on a schedule (recommended) or continuously

This is the easiest version yet for long-term autonomous operation.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from db import init_db, log_cycle, set_state, get_state

# LLM clients
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

# ==================== SIMPLE CONFIGURATION ====================
# Change these via environment variables when deploying

CONFIG = {
    "enabled_agents": ["lead_website", "app_factory", "aaas_seller", "polymarket"],
    "run_mode": os.getenv("RUN_MODE", "scheduled"),        # "scheduled" or "continuous"
    "sleep_minutes": int(os.getenv("SLEEP_MINUTES", "360")),  # Only used in continuous mode
    "default_model": os.getenv("DEFAULT_MODEL", "grok"),
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
}

# Setup clean logging
logging.basicConfig(
    level=getattr(logging, CONFIG["log_level"]),
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("Swarm")

print("=== AI PROFIT SWARM v5.2 (Deployment Optimized) ===\n")

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

STATE_FILE = "swarm_state.json"

# ==================== PROMPTS ====================

PROMPTS = {
    "orchestrator": "You are the Master Orchestrator of a high-performance autonomous profit system...",
    "lead_website": "You are an expert Lead Generation + Website Building Agent...",
    "app_factory": "You are the App & SaaS Factory Agent...",
    "aaas_seller": "You are the AI Agent as a Service Sales Agent...",
    "polymarket": "You are the Polymarket Research & Edge Agent...",
    "reviewer": "You are the Reviewer & Self-Improvement Agent..."
}

# ==================== STATE ====================

def load_state() -> Dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "history": [],
        "metrics": {"total_cycles": 0, "total_tasks_completed": 0},
        "last_reviewer_feedback": ""
    }

def save_state(state: Dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ==================== LLM ====================

def call_llm(prompt: str, task: str, model: str = None) -> str:
    if model is None:
        model = CONFIG["default_model"]

    if model == "grok" and GROK_API_KEY and HAS_OPENAI:
        try:
            client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
            resp = client.chat.completions.create(
                model="grok-4",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": task}],
                max_tokens=900
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"Grok error: {e}")

    if model == "claude" and CLAUDE_API_KEY and HAS_ANTHROPIC:
        try:
            client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
            resp = client.messages.create(
                model="claude-4-opus-20250514",
                max_tokens=900,
                system=prompt,
                messages=[{"role": "user", "content": task}]
            )
            return resp.content[0].text
        except Exception as e:
            logger.warning(f"Claude error: {e}")

    logger.info(f"{model.upper()} (simulated)")
    return f"[{model.upper()} SIMULATED] Completed task."

# ==================== AGENTS ====================

def orchestrator(state: Dict) -> Dict:
    logger.info("=== ORCHESTRATOR ===")
    last_feedback = state.get("last_reviewer_feedback", "")
    output = call_llm(PROMPTS["orchestrator"], f"Plan tasks. Last feedback: {last_feedback[:150]}")
    state["orchestrator_output"] = output

    state["tasks"] = [
        {"agent": "lead_website", "task": "Find businesses with problems and send outreach"},
        {"agent": "app_factory", "task": "Build one high-potential micro-SaaS"},
        {"agent": "aaas_seller", "task": "Send AaaS offers to qualified businesses"},
        {"agent": "polymarket", "task": "Research Polymarket and find opportunities"},
    ]
    state["tasks"] = [t for t in state["tasks"] if t["agent"] in CONFIG["enabled_agents"]]
    return state

def execute_agent(state: Dict, agent_name: str, prompt_key: str) -> Dict:
    logger.info(f"=== {agent_name.upper()} ===")
    for task in state.get("tasks", []):
        if task["agent"] == agent_name:
            output = call_llm(PROMPTS.get(prompt_key, ""), task["task"])
            state[f"{agent_name}_output"] = output
    return state

def reviewer(state: Dict) -> Dict:
    logger.info("=== REVIEWER ===")
    output = call_llm(PROMPTS["reviewer"], "Review this cycle and suggest improvements.")
    state["review_output"] = output
    state["last_reviewer_feedback"] = output
    return state

# ==================== MAIN CYCLE ====================

def run_cycle():
    logger.info(f"Starting cycle at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    state = load_state()

    try:
        state = orchestrator(state)
        state = execute_agent(state, "lead_website", "lead_website")
        state = execute_agent(state, "app_factory", "app_factory")
        state = execute_agent(state, "aaas_seller", "aaas_seller")
        state = execute_agent(state, "polymarket", "polymarket")
        state = reviewer(state)
    except Exception as e:
        logger.error(f"Cycle error: {e}")

    # Update metrics
    state.setdefault("metrics", {})
    state["metrics"]["total_cycles"] = state["metrics"].get("total_cycles", 0) + 1
    state["metrics"]["total_tasks_completed"] = state["metrics"].get("total_tasks_completed", 0) + len(state.get("tasks", []))

    save_state(state)
    logger.info("Cycle complete.\n")

# ==================== RUN MODES ====================

def run_scheduled():
    """Run once and exit (best for Railway cron / scheduled jobs)"""
    run_cycle()

def run_continuous():
    """Run in a loop with sleep (for continuous operation)"""
    import time
    logger.info("Running in continuous mode...")
    while True:
        run_cycle()
        sleep_minutes = CONFIG["sleep_minutes"]
        logger.info(f"Sleeping for {sleep_minutes} minutes...")
        time.sleep(sleep_minutes * 60)

if __name__ == "__main__":
    init_db()                    # Initialize database tables
    if CONFIG["run_mode"] == "continuous":
        run_continuous()
    else:
        run_scheduled()
