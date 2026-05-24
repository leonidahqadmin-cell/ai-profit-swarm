"""
AI Profit Swarm v5.2 - Deployment Optimized (Minimal Human Effort)

This version is built for easy deployment on Railway / Render / similar platforms.

Key features:
- Clean logging (easy to see what happened in each cycle)
- Supports both Scheduled runs (recommended) and Continuous mode
- Simple configuration via environment variables
- Robust error handling + production-grade DB persistence
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
from db import init_db, log_cycle, set_state, get_state, get_recent_cycles

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
    "run_mode": os.getenv("RUN_MODE", "scheduled"),  # "scheduled" or "continuous"
    "sleep_minutes": int(os.getenv("SLEEP_MINUTES", "360")),  # Only used in continuous mode
    "default_model": os.getenv("DEFAULT_MODEL", "grok"),
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
    "improvement_interval": int(os.getenv("IMPROVEMENT_INTERVAL", "5")),  # Run analysis every N cycles
    "improvement_lookback": int(os.getenv("IMPROVEMENT_LOOKBACK", "15")), # How many cycles to analyze
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

# Track API call count per cycle (reset each cycle)
_cycle_api_calls = 0

def call_llm(prompt: str, task: str, model: str = None) -> str:
    global _cycle_api_calls
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
            _cycle_api_calls += 1
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
            _cycle_api_calls += 1
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

# ==================== HELPERS ====================

def _safe_db(fn, *args, label="db", **kwargs):
    """
    Task 2: Resilient DB wrapper.
    Calls fn(*args, **kwargs) and returns the result.
    On any exception, logs the error and returns None — never crashes the swarm.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.error(f"[DB ERROR] {label} failed: {e}")
        return None

# ==================== SELF-IMPROVEMENT (MVP, read-only) ====================
#
# Goal: every IMPROVEMENT_INTERVAL cycles, look at the last N cycles, ask Grok
# for structured insights, and store them in swarm_state as *advisory* data.
#
# This is intentionally read-only — nothing the LLM says will modify prompts or
# strategies automatically. Insights are surfaced for review only.

def _summarize_recent_cycles(cycles: list) -> dict:
    """
    Build a small numeric summary of recent cycles so the LLM gets clean signal
    instead of a wall of raw JSON. Pure local computation — no LLM call.
    """
    if not cycles:
        return {"count": 0}

    total          = len(cycles)
    successes      = sum(1 for c in cycles if (c.get("details") or {}).get("status") == "success")
    failures       = total - successes
    durations      = [(c.get("metrics") or {}).get("cycle_duration_s", 0) for c in cycles]
    api_calls      = [(c.get("metrics") or {}).get("api_calls", 0)       for c in cycles]
    agents_counter = {}

    for c in cycles:
        for a in (c.get("details") or {}).get("agents_run", []) or []:
            agents_counter[a] = agents_counter.get(a, 0) + 1

    def _avg(xs): 
        xs = [x for x in xs if isinstance(x, (int, float))]
        return round(sum(xs) / len(xs), 2) if xs else 0

    return {
        "count":                total,
        "successes":            successes,
        "failures":             failures,
        "success_rate":         round(successes / total, 3) if total else 0,
        "avg_duration_s":       _avg(durations),
        "avg_api_calls":        _avg(api_calls),
        "agent_run_frequency":  agents_counter,
    }

def analyze_and_improve():
    """
    MVP self-improvement loop.

    - Pulls the last N cycles from cycle_logs
    - Computes a small numeric summary locally
    - Asks Grok for structured insights & recommendations
    - Stores the resulting insights in swarm_state (read-only advisory data)

    Fully resilient: any failure is logged and swallowed; the main swarm loop
    is never blocked or crashed by this function.
    """
    try:
        lookback = CONFIG["improvement_lookback"]
        logger.info(f"[IMPROVE] Running self-analysis on last {lookback} cycles...")

        # 1. Pull recent telemetry
        try:
            cycles = get_recent_cycles(lookback) or []
        except Exception as e:
            logger.error(f"[IMPROVE] Failed to fetch cycles: {e}")
            return

        if len(cycles) < 2:
            logger.info("[IMPROVE] Not enough data yet (need at least 2 cycles). Skipping.")
            return

        # 2. Local numeric summary (cheap, deterministic)
        summary = _summarize_recent_cycles(cycles)
        logger.info(f"[IMPROVE] Local summary: {summary}")

        # 3. Ask Grok for structured insights
        analysis_prompt = (
            "You are a senior strategy analyst for an autonomous AI profit swarm. "
            "You are given a JSON summary of the swarm's recent cycle telemetry. "
            "Your job is to produce ACTIONABLE, profit-focused insights — not vague observations.\n\n"
            "Respond ONLY with valid JSON that matches this schema exactly:\n"
            "{\n"
            '  "performance_trend": "improving" | "stable" | "declining",\n'
            '  "best_performing_agents": ["..."],\n'
            '  "weak_areas": ["..."],\n'
            '  "recommended_strategy": "short, concrete next-step strategy",\n'
            '  "improvement_suggestions": ["specific suggestion 1", "specific suggestion 2"],\n'
            '  "summary": "one-paragraph plain-English summary"\n'
            "}\n"
            "Be concrete. Focus on profit generation. No hedging."
        )

        analysis_task = (
            "Recent cycle summary:\n"
            + json.dumps(summary, indent=2)
            + "\n\nRaw recent cycles (most recent first, truncated):\n"
            + json.dumps(cycles[:10], indent=2)[:6000]   # cap context size
        )

        raw = call_llm(analysis_prompt, analysis_task, model="grok")

        # 4. Try to parse JSON; if it fails, keep the raw text as fallback
        insights = None
        try:
            # Strip code fences if the model added them
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            insights = json.loads(cleaned)
        except Exception as parse_err:
            logger.warning(f"[IMPROVE] Could not parse JSON insights: {parse_err}")
            insights = {"raw_response": raw[:2000]}

        # 5. Persist as read-only advisory data
        now_iso = datetime.now().isoformat()
        _safe_db(set_state, "last_analysis_at",      now_iso,                          label="set last_analysis_at")
        _safe_db(set_state, "last_analysis_summary", insights.get("summary", "n/a") if isinstance(insights, dict) else "n/a", label="set analysis_summary")
        _safe_db(set_state, "performance_trend",     insights.get("performance_trend") if isinstance(insights, dict) else None, label="set perf_trend")
        _safe_db(set_state, "best_performing_agents", insights.get("best_performing_agents", []) if isinstance(insights, dict) else [], label="set best_agents")
        _safe_db(set_state, "weak_areas",            insights.get("weak_areas", []) if isinstance(insights, dict) else [], label="set weak_areas")
        _safe_db(set_state, "recommended_strategy",  insights.get("recommended_strategy", "") if isinstance(insights, dict) else "", label="set strategy")
        _safe_db(set_state, "improvement_suggestions", insights.get("improvement_suggestions", []) if isinstance(insights, dict) else [], label="set suggestions")
        _safe_db(set_state, "last_analysis_numeric", summary, label="set analysis_numeric")
        _safe_db(set_state, "analysis_version",      1, label="set analysis_version")

        logger.info(
            f"[IMPROVE] Insights stored. trend={insights.get('performance_trend') if isinstance(insights, dict) else 'n/a'} "
            f"| strategy={(insights.get('recommended_strategy') if isinstance(insights, dict) else '')[:80]}"
        )

    except Exception as e:
        # Top-level guard — under no circumstances should this break run_cycle()
        logger.error(f"[IMPROVE] analyze_and_improve failed (non-fatal): {e}")

# ==================== MAIN CYCLE ====================

def run_cycle():
    global _cycle_api_calls
    _cycle_api_calls = 0  # Reset per-cycle API call counter

    cycle_start = datetime.now()
    logger.info(f"Starting cycle at {cycle_start.strftime('%Y-%m-%d %H:%M')}")

    state = load_state()
    cycle_error = None          # Track whether this cycle had an error
    tasks_completed = 0         # How many agent tasks ran
    agents_run = []             # Which agents were executed

    try:
        state = orchestrator(state)
        tasks_in_cycle = state.get("tasks", [])

        for agent_name, prompt_key in [
            ("lead_website", "lead_website"),
            ("app_factory",  "app_factory"),
            ("aaas_seller",  "aaas_seller"),
            ("polymarket",   "polymarket"),
        ]:
            if any(t["agent"] == agent_name for t in tasks_in_cycle):
                state = execute_agent(state, agent_name, prompt_key)
                agents_run.append(agent_name)
                tasks_completed += 1

        state = reviewer(state)

    except Exception as e:
        cycle_error = str(e)
        logger.error(f"Cycle error: {e}")

    # ── Update file-based metrics ─────────────────────────────────────────────
    state.setdefault("metrics", {})
    state["metrics"]["total_cycles"] = state["metrics"].get("total_cycles", 0) + 1
    state["metrics"]["total_tasks_completed"] = (
        state["metrics"].get("total_tasks_completed", 0) + tasks_completed
    )
    save_state(state)

    # ── Derived values for logging ────────────────────────────────────────────
    cycle_duration_s = round((datetime.now() - cycle_start).total_seconds(), 1)
    cycle_status     = "error" if cycle_error else "success"
    cycle_number     = (_safe_db(get_state, "total_cycles", 0, label="get total_cycles") or 0) + 1

    # TODO: replace with real lead-count variable once lead_website agent returns structured data
    leads_this_cycle = 0

    # Task 1: Improved log_cycle() — real data instead of all zeros
    _safe_db(
        log_cycle,
        summary=f"Cycle #{cycle_number} — {cycle_status} — {tasks_completed} agents ran in {cycle_duration_s}s",
        details={
            "status":          cycle_status,
            "agents_run":      agents_run,
            "tasks_completed": tasks_completed,
            "niche_focus":     "general",           # TODO: replace with dynamic niche when available
            "leads_generated": leads_this_cycle,    # TODO: replace with actual variable
            "error":           cycle_error,         # None if clean run
            "model_used":      CONFIG["default_model"],
            "run_mode":        CONFIG["run_mode"],
        },
        metrics={
            "api_calls":       _cycle_api_calls,    # Real count from call_llm()
            "tokens_used":     0,                   # TODO: sum token usage from LLM responses
            "cycle_duration_s": cycle_duration_s,
            "cycle_number":    cycle_number,
        },
        label="log_cycle"
    )

    # Task 2 + Task 3: Resilient state updates with expanded persistent tracking
    now_iso = datetime.now().isoformat()

    # Core counters
    _safe_db(set_state, "total_cycles",    cycle_number, label="set total_cycles")
    _safe_db(set_state, "last_cycle_at",   now_iso,      label="set last_cycle_at")

    # Task 3a: Track success / failure streaks and counts
    prev_failed = _safe_db(get_state, "failed_cycles_count", 0, label="get failed_cycles") or 0
    prev_streak = _safe_db(get_state, "current_success_streak", 0, label="get streak") or 0

    if cycle_error:
        _safe_db(set_state, "failed_cycles_count",      prev_failed + 1,  label="set failed_cycles")
        _safe_db(set_state, "current_success_streak",   0,                label="reset streak")
        _safe_db(set_state, "last_error",               cycle_error,      label="set last_error")
        _safe_db(set_state, "last_error_at",            now_iso,          label="set last_error_at")
    else:
        _safe_db(set_state, "current_success_streak",   prev_streak + 1,  label="set streak")
        _safe_db(set_state, "last_successful_cycle_at", now_iso,          label="set last_success")

    # Task 3b: Cumulative leads (TODO: replace 0 with real leads_this_cycle variable)
    prev_leads = _safe_db(get_state, "total_leads_generated", 0, label="get total_leads") or 0
    _safe_db(set_state, "total_leads_generated", prev_leads + leads_this_cycle, label="set total_leads")

    # Task 3c: Track which agents ran most recently
    _safe_db(set_state, "last_agents_run", agents_run, label="set last_agents_run")

    # Task 3d: Best performing niche (placeholder — update when niche scoring exists)
    # TODO: replace "general" with the actual niche from agent output when available
    _safe_db(set_state, "last_niche_focus", "general", label="set last_niche")

    # Task 3e: Total tasks completed across all cycles
    all_time_tasks = (_safe_db(get_state, "total_tasks_all_time", 0, label="get all_time_tasks") or 0)
    _safe_db(set_state, "total_tasks_all_time", all_time_tasks + tasks_completed, label="set all_time_tasks")

    # ── Task 4: Human-readable cycle summary ─────────────────────────────────
    total_leads_so_far = (_safe_db(get_state, "total_leads_generated", 0, label="summary get leads") or 0)
    logger.info(
        f"[SUMMARY] Cycle #{cycle_number} | Status: {cycle_status.upper()} | "
        f"Agents: {len(agents_run)} ({', '.join(agents_run) or 'none'}) | "
        f"API calls: {_cycle_api_calls} | Duration: {cycle_duration_s}s | "
        f"Success streak: {0 if cycle_error else prev_streak + 1} | "
        f"Total leads all-time: {total_leads_so_far} | "
        f"Total cycles: {cycle_number}"
    )

    # ── Self-improvement loop (MVP, read-only) ──────────────────────────────
    # Runs every IMPROVEMENT_INTERVAL cycles. Fully wrapped — cannot crash run_cycle.
    interval = CONFIG.get("improvement_interval", 5)
    if interval > 0 and cycle_number % interval == 0:
        try:
            analyze_and_improve()
        except Exception as e:
            logger.error(f"[IMPROVE] outer guard caught: {e}")

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
