import pandas as pd


def safe_rate(passes: int, plays: int, default: float = 0.5) -> float:
    # Bayesian smoothing to prevent extreme early values
    if plays < 0:
        return default
    return (passes + 1) / (plays + 2)


def build_situational_flags(
    down: int,
    ydstogo: int,
    yardline_100: int,
    game_seconds_remaining: int,
    qtr: int,
    score_differential: int
) -> dict:
    is_third_down = 1 if down == 3 else 0
    is_fourth_down = 1 if down == 4 else 0

    short_yardage = 1 if ydstogo <= 2 else 0
    medium_yardage = 1 if 3 <= ydstogo <= 6 else 0
    long_yardage = 1 if ydstogo >= 7 else 0

    red_zone = 1 if yardline_100 <= 20 else 0
    goal_to_go = 1 if yardline_100 <= 10 and ydstogo >= yardline_100 else 0
    backed_up = 1 if yardline_100 >= 90 else 0
    plus_territory = 1 if yardline_100 <= 50 else 0

    two_minute = 1 if qtr in [2, 4] and game_seconds_remaining <= 120 else 0
    leading_team = 1 if score_differential > 0 else 0
    trailing_team = 1 if score_differential < 0 else 0
    neutral_score = 1 if score_differential == 0 else 0

    return {
        "is_third_down": is_third_down,
        "is_fourth_down": is_fourth_down,
        "short_yardage": short_yardage,
        "medium_yardage": medium_yardage,
        "long_yardage": long_yardage,
        "red_zone": red_zone,
        "goal_to_go": goal_to_go,
        "backed_up": backed_up,
        "plus_territory": plus_territory,
        "two_minute": two_minute,
        "leading_team": leading_team,
        "trailing_team": trailing_team,
        "neutral_score": neutral_score,
    }


def build_feature_row(
    down: int,
    ydstogo: int,
    yardline_100: int,
    game_seconds_remaining: int,
    qtr: int,
    score_differential: int,
    posteam: str,
    defteam: str,
    prev_play_pass: int,
    game_pass_rate: float,
    drive_pass_rate: float
) -> pd.DataFrame:
    row = {
        "down": down,
        "ydstogo": ydstogo,
        "yardline_100": yardline_100,
        "game_seconds_remaining": game_seconds_remaining,
        "qtr": qtr,
        "score_differential": score_differential,
        "posteam": posteam,
        "defteam": defteam,
        "prev_play_pass": prev_play_pass,
        "game_pass_rate": game_pass_rate,
        "drive_pass_rate": drive_pass_rate,
    }

    row.update(
        build_situational_flags(
            down=down,
            ydstogo=ydstogo,
            yardline_100=yardline_100,
            game_seconds_remaining=game_seconds_remaining,
            qtr=qtr,
            score_differential=score_differential,
        )
    )

    return pd.DataFrame([row])