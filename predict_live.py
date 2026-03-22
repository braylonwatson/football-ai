import joblib
import pandas as pd

from feature_builder import build_feature_row
from recommendation_engine import get_defensive_recommendation


def load_model_and_columns():
    model = joblib.load("play_predictor_model.pkl")
    model_columns = joblib.load("model_columns.pkl")
    return model, model_columns


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
        "game_pass_rate_used": round(game_pass_rate, 3),
        "drive_pass_rate_used": round(drive_pass_rate, 3),
        "recommendation": recommendation,
    }


if __name__ == "__main__":
    print("Enter current game situation:\n")

    down = int(input("Down: "))
    ydstogo = int(input("Yards to go: "))
    yardline_100 = int(input("Yardline_100: "))
    game_seconds_remaining = int(input("Game seconds remaining: "))
    qtr = int(input("Quarter: "))
    score_differential = int(input("Score differential (offense perspective): "))
    posteam = input("Offense team abbreviation (e.g. KC): ").strip().upper()
    defteam = input("Defense team abbreviation (e.g. BUF): ").strip().upper()
    prev_play_pass = int(input("Was previous play a pass? (1=yes, 0=no): "))
    game_pass_rate = float(input("Current game pass rate so far (default 0.5 if unknown): ") or 0.5)
    drive_pass_rate = float(input("Current drive pass rate so far (default 0.5 if unknown): ") or 0.5)

    result = predict_play(
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
        drive_pass_rate=drive_pass_rate
    )

    print("\nPrediction Result:")
    print(result)