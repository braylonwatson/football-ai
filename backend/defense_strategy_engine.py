def get_defensive_strategy(
    prediction: str,
    run_prob: float,
    pass_prob: float,
    down: int,
    ydstogo: int,
    yardline_100: int,
    score_differential: int,
    confidence_tier: str,
):
    confidence = max(run_prob, pass_prob)

    short_yardage = ydstogo <= 2
    medium_yardage = 3 <= ydstogo <= 6
    long_yardage = ydstogo >= 7
    red_zone = yardline_100 <= 20

    if confidence_tier == "NEUTRAL":
        return {
            "defensive_personnel": "Match offense",
            "front": "Balanced front",
            "coverage_shell": "Neutral shell",
            "pressure": "Standard rush",
            "aggression": "Conservative",
            "primary_focus": "Stay structurally sound",
            "reason": "Prediction confidence is low, so avoid overcommitting."
        }

    if prediction == "RUN":
        if short_yardage:
            return {
                "defensive_personnel": "Base / Heavy",
                "front": "Heavy box",
                "coverage_shell": "Single-high",
                "pressure": "Run pressure optional",
                "aggression": "Aggressive",
                "primary_focus": "Defend interior run / short conversion",
                "reason": f"Run probability is {confidence:.1%} in a short-yardage situation."
            }

        if red_zone:
            return {
                "defensive_personnel": "Base / Big Nickel",
                "front": "Compact front",
                "coverage_shell": "Single-high or matchup zone",
                "pressure": "Controlled pressure",
                "aggression": "Balanced",
                "primary_focus": "Close run lanes and watch play-action",
                "reason": f"Run probability is {confidence:.1%} in the red zone."
            }

        return {
            "defensive_personnel": "Base",
            "front": "Balanced-to-heavy front",
            "coverage_shell": "Single-high",
            "pressure": "Standard rush",
            "aggression": "Balanced",
            "primary_focus": "Lean run first",
            "reason": f"Run probability is {confidence:.1%}."
        }

    if long_yardage or down in [3, 4]:
        return {
            "defensive_personnel": "Nickel / Dime",
            "front": "Pass front",
            "coverage_shell": "Two-high / sticks shell",
            "pressure": "Sim pressure or pass-rush emphasis",
            "aggression": "Balanced",
            "primary_focus": "Defend the sticks / force checkdown",
            "reason": f"Pass probability is {confidence:.1%} in a likely passing situation."
        }

    if red_zone:
        return {
            "defensive_personnel": "Nickel / Big Nickel",
            "front": "Balanced front",
            "coverage_shell": "Match coverage",
            "pressure": "Selective pressure",
            "aggression": "Balanced",
            "primary_focus": "Protect against quick-game and spacing concepts",
            "reason": f"Pass probability is {confidence:.1%} in the red zone."
        }

    return {
        "defensive_personnel": "Nickel",
        "front": "Balanced pass front",
        "coverage_shell": "Two-high",
        "pressure": "Pressure optional",
        "aggression": "Moderate",
        "primary_focus": "Lean pass first",
        "reason": f"Pass probability is {confidence:.1%}."
    }