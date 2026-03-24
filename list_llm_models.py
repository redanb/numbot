#!/usr/bin/env python3
"""
LLM Selection & Status Guide (2026 Edition)
Provides a 'sep by step' view of available models based on 'com intel' data.
"""
import os
import sys
from pathlib import Path

# Add master to path to check router
MASTER_DIR = Path(r"C:\Users\admin\.antigravity\master")
# Add local brainbot to path for current context
sys.path.insert(0, str(Path(__file__).resolve().parent / "brainbot"))
# Add master to path for global context
sys.path.append(str(MASTER_DIR))

try:
    import llm_router
    # Force env load in case of stale cache
    if hasattr(llm_router, "_load_env_manually"):
        llm_router._load_env_manually()
except ImportError:
    llm_router = None

def get_router_status():
    if not llm_router:
        return {}
    return llm_router.check_api_status()

def display_provider(name, stat, models, best_for, fix_hint):
    health = stat.get("health", "MISSING")
    print(f"\n{name}")
    print(f"   - Health: {health}")
    print(f"   - {models}")
    print(f"   - {best_for}")
    if "READY" not in health and "ONLINE" not in health:
        print(f"   - ACTION: {fix_hint}")

def display_selection_guide():
    status = get_router_status()
    
    print("\n" + "="*60)
    print(" [SHOCK] ANTIGRAVITY LLM MODELS SELECTION GUIDE (MARCH 2026) [SHOCK]")
    print("="*60)
    
    # -- TIER 1: HIGH PERFORMANCE ------------------
    print(f"\n[TIER 1] - MAXIMUM PERFORMANCE & QUALITY ($0 COST)")
    print("-" * 50)
    
    display_provider("1. Google Gemini (PRIMARY)", status.get("gemini", {}), 
                     "Models: Gemini 2.0 Flash (Standard), Gemini 2.0 Pro (Deep)",
                     "Best For: Multi-modal, long context (1M+), stable daily runs.",
                     "FIX: If exhausted, add a second API key (GEMINI_API_KEY_1) from a different project.")

    display_provider("2. Groq (HIGH SPEED)", status.get("groq", {}),
                     "Models: Llama 3.3 70B (800 t/s), Llama 3.1 8B (1200 t/s)",
                     "Best For: Rapid alpha evolution, high-frequency iterations.",
                     "FIX: None needed if READY. This is currently our most stable fallback.")

    display_provider("3. Github Models (PREMIUM FALLBACK)", status.get("github", {}),
                     "Models: GPT-4o, Llama 3.1 405B, o1 (Reasoning)",
                     "Best For: Complex logic when Gemini is rate-limited.",
                     "FIX: Your PAT needs the 'Github Models' permission enabled in Github Settings.")

    # -- TIER 2: REASONING & THEORETICAL ----------------
    print(f"\n[TIER 2] - DEEP REASONING & THEORETICAL")
    print("-" * 50)
    
    display_provider("1. OpenRouter (REASONING)", status.get("openrouter", {}),
                     "Models: DeepSeek R1 (The King of Thinking), Qwen 2.5 Coder",
                     "Best For: Reverse engineering winning alphas, complex math fixes.",
                     "FIX: DeepSeek R1 is ideal for the SATE Thinking Engine.")

    display_provider("2. Perplexity (SONAR SEARCH)", status.get("perplexity", {}),
                     "Models: Sonar Reasoning, Sonar Pro",
                     "Best For: Real-time market news and alpha hypothesis research.",
                     "FIX: Add PERPLEXITY_API_KEY to .env for real-time research synthesis.")

    print("\n" + "="*60)
    print(" [INFO] HOW TO CHANGE MODELS:")
    print(" 1. To set a priority, edit 'preferred_provider' in thinking_engine.py")
    print(" 2. To update keys, edit C:\\Users\\admin\\.antigravity\\master\\.env")
    print(" 3. Run this script to verify after any change.")
    print("="*60 + "\n")

if __name__ == "__main__":
    display_selection_guide()
