import os
import logging
import json
from app.models.player import format_inr

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

_gemini_client = None
_gemini_initialized = False

def _init_gemini():
    """Initializes Google Generative AI safely."""
    global _gemini_client, _gemini_initialized
    if _gemini_initialized:
        return _gemini_client
    
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Running in smart heuristic fallback mode.")
        _gemini_initialized = True
        _gemini_client = None
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        _gemini_client = genai.GenerativeModel(model_name)
        _gemini_initialized = True
        logger.info(f"Gemini client initialized with model: {model_name}")
        return _gemini_client
    except Exception as e:
        logger.warning(f"Error initializing Gemini SDK: {str(e)}")
        _gemini_initialized = True
        _gemini_client = None
        return None


def get_player_analysis(player_dict, team_squad=None, remaining_budget=None):
    """
    Analyzes the current auction player:
    - Role & match impact
    - Recommended bid range
    - Tactical squad fit
    - Strengths & key qualities
    """
    client = _init_gemini()
    
    # Base heuristic fallback calculation
    base_price = player_dict.get("base_price", 20000000)
    rating = player_dict.get("rating", 80)
    multiplier = 1.0 + max(0, (rating - 75) * 0.12)
    recommended_max = int(base_price * multiplier)
    
    fallback_analysis = {
        "status": "fallback",
        "notice": "AI insights are temporarily unavailable. You can continue your auction normally.",
        "player_name": player_dict.get("name"),
        "role": player_dict.get("role"),
        "rating": rating,
        "recommended_bid_range": f"{format_inr(base_price)} - {format_inr(recommended_max)}",
        "strengths": [
            f"High impact {player_dict.get('role')} with rating {rating}/100",
            f"Proficient {player_dict.get('batting_style')} batting technique",
            f"Specialist bowling skill: {player_dict.get('bowling_style')}" if player_dict.get('bowling_style') != "None" else "Solid fielding and boundary saving"
        ],
        "squad_fit": f"Strong addition for teams looking to bolster their {player_dict.get('role')} depth.",
        "verdict": "Target aggressively if budget allows" if rating >= 90 else "Great tactical value pick around base price"
    }

    if not client:
        return fallback_analysis

    prompt = f"""
    You are an expert IPL Auction Director and Cricket Data Analyst.
    Analyze this cricket player for an IPL franchise:
    Name: {player_dict.get('name')}
    Role: {player_dict.get('role')}
    Country: {player_dict.get('country')} (Overseas: {player_dict.get('is_overseas')})
    Base Price: {format_inr(base_price)}
    Rating: {rating}/100
    Batting Style: {player_dict.get('batting_style')}
    Bowling Style: {player_dict.get('bowling_style')}
    
    Return a strictly valid JSON object with keys:
    "recommended_bid_range" (string with Cr/Lakhs),
    "strengths" (list of 3 concise strings),
    "squad_fit" (1-2 sentences),
    "verdict" (1 sentence recommendation)
    """

    try:
        response = client.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 400}
        )
        if response and response.text:
            text = response.text.strip()
            # Clean markdown codeblocks if returned
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            data["status"] = "success"
            data["notice"] = ""
            data["player_name"] = player_dict.get("name")
            data["role"] = player_dict.get("role")
            data["rating"] = rating
            return data
    except Exception as e:
        logger.warning(f"Gemini player analysis call failed: {str(e)}")

    return fallback_analysis


def get_auction_strategy(team_dict, auction_stats=None):
    """
    Suggests auction strategy for a team:
    - Priority player roles
    - Budget allocation strategy
    - Overseas slot advice
    """
    client = _init_gemini()
    
    roles = team_dict.get("roles", {})
    rem_budget = team_dict.get("remaining_budget", 0)
    squad_count = team_dict.get("squad_count", 0)
    overseas_count = team_dict.get("overseas_count", 0)

    # Heuristic strategy
    priorities = []
    if roles.get("Bowler", 0) < 5:
        priorities.append("Pace & Mystery Spin Bowling (need at least 5 bowlers)")
    if roles.get("All-rounder", 0) < 3:
        priorities.append("Power-hitting All-rounders (balance 6th & 7th slot)")
    if roles.get("Wicketkeeper", 0) < 2:
        priorities.append("Specialist Wicketkeeper-Batsman")
    if roles.get("Batsman", 0) < 5:
        priorities.append("Top-order Indian Anchor & Finisher")
    if not priorities:
        priorities.append("Emerging uncapped bench depth")

    fallback_strategy = {
        "status": "fallback",
        "notice": "AI insights are temporarily unavailable. You can continue your auction normally.",
        "team_name": team_dict.get("team_name"),
        "remaining_budget": format_inr(rem_budget),
        "priority_roles": priorities[:3],
        "budget_pacing": "Aggressive - Target marquee players" if rem_budget > 600000000 else "Conservative - Save funds for squad slots",
        "overseas_strategy": f"{overseas_count}/8 overseas signed. {'Slots available for premium imports.' if overseas_count < 8 else 'Max overseas reached, target Indian talent.'}"
    }

    if not client:
        return fallback_strategy

    prompt = f"""
    You are an IPL Chief Cricket Strategist.
    Provide auction strategy for {team_dict.get('team_name')}:
    Remaining Budget: {format_inr(rem_budget)}
    Squad Count: {squad_count}
    Overseas Count: {overseas_count}/8
    Current Role Distribution: {json.dumps(roles)}
    
    Return a strictly valid JSON object with keys:
    "priority_roles" (list of 2-3 target roles with short reason),
    "budget_pacing" (1 sentence advice on how to spend remaining purse),
    "overseas_strategy" (1 sentence recommendation for international slots)
    """

    try:
        response = client.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 400}
        )
        if response and response.text:
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            data["status"] = "success"
            data["notice"] = ""
            data["team_name"] = team_dict.get("team_name")
            return data
    except Exception as e:
        logger.warning(f"Gemini auction strategy call failed: {str(e)}")

    return fallback_strategy


def get_team_squad_analysis(team_dict, squad_list):
    """
    Analyzes the complete squad after/during auction:
    - Squad strengths
    - Squad weaknesses
    - Suggested Playing XI
    - Rating & verdict
    """
    client = _init_gemini()
    
    player_names = [f"{p['player']['name']} ({p['player']['role']})" for p in squad_list if p.get('player')]
    
    fallback_analysis = {
        "status": "fallback",
        "notice": "AI insights are temporarily unavailable. You can continue your auction normally.",
        "team_name": team_dict.get("team_name"),
        "squad_rating": min(95, max(65, 75 + len(squad_list))),
        "strengths": [
            f"Formed solid core of {len(squad_list)} players",
            f"Preserved {format_inr(team_dict.get('remaining_budget', 0))} purse balance",
            f"Balanced {team_dict.get('overseas_count', 0)} overseas talents"
        ],
        "weaknesses": [
            "Bench depth in specialist roles could be strengthened"
        ],
        "suggested_xi": player_names[:11] if len(player_names) >= 11 else player_names,
        "recommendation": "Well-constructed roster capable of competing in IPL knockout stages."
    }

    if not client or len(squad_list) == 0:
        return fallback_analysis

    prompt = f"""
    You are an IPL head coach. Evaluate this finalized squad for {team_dict.get('team_name')}:
    Players: {', '.join(player_names)}
    Money Spent: {format_inr(team_dict.get('spent_budget', 0))}
    
    Return a strictly valid JSON object with keys:
    "squad_rating" (integer 60-100),
    "strengths" (list of 3 strings),
    "weaknesses" (list of 2 strings),
    "suggested_xi" (list of 11 player names from the squad),
    "recommendation" (2 sentences overall verdict)
    """

    try:
        response = client.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 500}
        )
        if response and response.text:
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
            data["status"] = "success"
            data["notice"] = ""
            data["team_name"] = team_dict.get("team_name")
            return data
    except Exception as e:
        logger.warning(f"Gemini squad analysis failed: {str(e)}")

    return fallback_analysis
