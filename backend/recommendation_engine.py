def get_confidence_tier(run_prob: float, pass_prob: float) -> str:
    confidence = max(run_prob, pass_prob)
    if confidence >= 0.75:
        return "STRONG"
    if confidence >= 0.62:
        return "MODERATE"
    if confidence >= 0.55:
        return "WEAK"
    return "NEUTRAL"


def get_defensive_recommendation(
    prediction: str,
    run_prob: float,
    pass_prob: float,
    down: int,
    ydstogo: int,
    yardline_100: int,
    score_differential: int
) -> dict:
    tier = get_confidence_tier(run_prob, pass_prob)
    confidence = max(run_prob, pass_prob)

    short_yardage = ydstogo <= 2
    long_yardage = ydstogo >= 7
    red_zone = yardline_100 <= 20
    goal_to_go = yardline_100 <= 10 and ydstogo >= yardline_100

    if tier == "NEUTRAL":
        return {
            "confidence_tier": tier,
            "recommendation": "Stay balanced",
            "front": "Base / neutral fit",
            "coverage": "Do not tip hand",
            "pressure": "Standard rush",
            "note": "Prediction edge is small. Do not overcommit."
        }

    if prediction == "RUN":
        if short_yardage or goal_to_go:
            return {
                "confidence_tier": tier,
                "recommendation": "Defend run first",
                "front": "Heavier box / fit-first front",
                "coverage": "Single-high acceptable",
                "pressure": "Low pressure, prioritize gap integrity",
                "note": f"Run lean at {confidence:.1%} in a high-run situation."
            }

        if red_zone:
            return {
                "confidence_tier": tier,
                "recommendation": "Compact run alert",
                "front": "Tighter box structure",
                "coverage": "Eyes on play-action / condensed space",
                "pressure": "Controlled pressure only",
                "note": f"Run lean at {confidence:.1%} with red-zone compression."
            }

        return {
            "confidence_tier": tier,
            "recommendation": "Shade toward run",
            "front": "Slightly heavier box",
            "coverage": "Single-high or balanced shell",
            "pressure": "Moderate, disciplined edges",
            "note": f"Run lean at {confidence:.1%}."
        }

    if long_yardage or down in [3, 4]:
        return {
            "confidence_tier": tier,
            "recommendation": "Defend pass first",
            "front": "Nickel / dime look",
            "coverage": "Sticks awareness / coverage-first",
            "pressure": "Sim pressure or clear passing-down pressure",
            "note": f"Pass lean at {confidence:.1%} in a passing situation."
        }

    if red_zone:
        return {
            "confidence_tier": tier,
            "recommendation": "Pass alert in red zone",
            "front": "Balanced sub package",
            "coverage": "Match routes in compressed field",
            "pressure": "Selective pressure",
            "note": f"Pass lean at {confidence:.1%} near the goal line area."
        }

    return {
        "confidence_tier": tier,
        "recommendation": "Shade toward pass",
        "front": "Nickel-capable structure",
        "coverage": "Two-high or matchup shell",
        "pressure": "Pressure optional, disguise preferred",
        "note": f"Pass lean at {confidence:.1%}."
    }