import joblib
import pandas as pd

from backend.feature_builder import build_feature_row
from backend.recommendation_engine import get_defensive_recommendation


def load_model_and_columns():
    model = joblib.load("play_predictor_model.pkl")
    model_columns = joblib.load("model_columns.pkl")
    return model, model_columns


def get_confidence_info(run_probability, pass_probability):
    confidence = max(run_probability, pass_probability)

    if confidence >= 0.80:
        tier = "STRONG"
    elif confidence >= 0.65:
        tier = "MODERATE"
    else:
        tier = "WEAK"

    return round(confidence, 3), tier


def predict_play(
    down,
    ydstogo,
    yardline_100,
    game_seconds_remaining,
    qtr,
    score_differential,
    posteam,
    defteam,
    prev_play_pass,
    game_pass_rate=0.5,
    drive_pass_rate=0.5
):
    model, model_columns = load_model_and_columns()

    input_data = build_feature_row(
        down=down,
        ydstogo=ydstogo,
        yardline_100=yardline_100,
        game_seconds_remaining=game_seconds_remaining,
        qtr=qtr,
        score_differential=score_differential,
        posteam=posteam,
        defteam=defteam,
        prev_play_pass=prev_play_pass,
        game_pass_rate=game_pass_rate,
        drive_pass_rate=drive_pass_rate,
    )

    input_encoded = pd.get_dummies(
        input_data,
        columns=["posteam", "defteam"],
        drop_first=True
    )

    input_encoded = input_encoded.reindex(columns=model_columns, fill_value=0)

    pred = model.predict(input_encoded)[0]
    prob = model.predict_proba(input_encoded)[0]

    prediction = "PASS" if pred == 1 else "RUN"
    run_probability = float(prob[0])
    pass_probability = float(prob[1])

    confidence, confidence_tier = get_confidence_info(run_probability, pass_probability)

    recommendation = get_defensive_recommendation(
        prediction=prediction,
        run_prob=run_probability,
        pass_prob=pass_probability,
        down=down,
        ydstogo=ydstogo,
        yardline_100=yardline_100,
        score_differential=score_differential,
    )

    return {
        "prediction": prediction,
        "run_probability": run_probability,
        "pass_probability": pass_probability,
        "confidence": confidence,
        "confidence_tier": confidence_tier,
        "game_pass_rate_used": round(game_pass_rate, 3),
        "drive_pass_rate_used": round(drive_pass_rate, 3),
        "recommendation": recommendation,
    }


def predict_next_play(
    down,
    ydstogo,
    yardline,
    time_remaining,
    quarter,
    score_diff,
    posteam,
    defteam,
    prev_play_pass,
    game_pass_rate=0.5,
    drive_pass_rate=0.5
):
    return predict_play(
        down=down,
        ydstogo=ydstogo,
        yardline_100=yardline,
        game_seconds_remaining=time_remaining,
        qtr=quarter,
        score_differential=score_diff,
        posteam=posteam,
        defteam=defteam,
        prev_play_pass=prev_play_pass,
        game_pass_rate=game_pass_rate,
        drive_pass_rate=drive_pass_rate
    )
