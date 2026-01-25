"""
ai_agent.py - LLM Integration (Claude API)

Responsibilities:
- Build prompt from market context + portfolio state + strategy rules
- Call Claude API
- Parse JSON response
- Validate recommendations against hard constraints
- Handle API errors

Key Functions:
- build_prompt(context: dict, portfolio: dict, config: dict) -> str
- call_claude_api(prompt: str) -> str
- parse_recommendation(response: str) -> dict
- validate_actions(actions: list, portfolio: dict) -> bool
"""

# TODO: Sprint 2 - Implement AI agent
