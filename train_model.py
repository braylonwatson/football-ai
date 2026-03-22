import joblib
import nfl_data_py as nfl
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from feature_builder import build_situational_flags


SEASONS = [2020, 2021, 2022, 2023]


def main():
    print(f"Loading nflfastR play-by-play data for seasons: {SEASONS}")
    pbp = nfl.import_pbp_data(SEASONS)

    pbp = pbp[pbp["play_type"].isin(["run", "pass"])].copy()

    pbp = pbp.dropna(
        subset=[
            "game_id",
            "play_id",
            "drive",
            "down",
            "ydstogo",
            "yardline_100",
            "game_seconds_remaining",
            "qtr",
            "score_differential",
            "posteam",
            "defteam",
        ]
    ).copy()

    pbp["down"] = pbp["down"].astype(int)
    pbp["ydstogo"] = pbp["ydstogo"].astype(int)
    pbp["yardline_100"] = pbp["yardline_100"].astype(int)
    pbp["game_seconds_remaining"] = pbp["game_seconds_remaining"].astype(int)
    pbp["qtr"] = pbp["qtr"].astype(int)
    pbp["score_differential"] = pbp["score_differential"].astype(int)

    pbp["is_pass"] = (pbp["play_type"] == "pass").astype(int)

    pbp = pbp.sort_values(by=["game_id", "play_id"]).copy()

    pbp["prev_play_pass"] = pbp.groupby("game_id")["is_pass"].shift(1)

    pbp["game_pass_rate"] = (
        pbp.groupby("game_id")["is_pass"]
        .expanding()
        .mean()
        .shift(1)
        .reset_index(level=0, drop=True)
    )

    pbp["drive_pass_rate"] = (
        pbp.groupby(["game_id", "drive"])["is_pass"]
        .expanding()
        .mean()
        .shift(1)
        .reset_index(level=[0, 1], drop=True)
    )

    # Safe situational feature creation
    situational_rows = pbp.apply(
        lambda row: build_situational_flags(
            down=int(row["down"]),
            ydstogo=int(row["ydstogo"]),
            yardline_100=int(row["yardline_100"]),
            game_seconds_remaining=int(row["game_seconds_remaining"]),
            qtr=int(row["qtr"]),
            score_differential=int(row["score_differential"]),
        ),
        axis=1,
        result_type="expand"
    )

    for col in situational_rows.columns:
        pbp[col] = situational_rows[col]

    features = [
        "down",
        "ydstogo",
        "yardline_100",
        "game_seconds_remaining",
        "qtr",
        "score_differential",
        "posteam",
        "defteam",
        "prev_play_pass",
        "game_pass_rate",
        "drive_pass_rate",
        "is_third_down",
        "is_fourth_down",
        "short_yardage",
        "medium_yardage",
        "long_yardage",
        "red_zone",
        "goal_to_go",
        "backed_up",
        "plus_territory",
        "two_minute",
        "leading_team",
        "trailing_team",
        "neutral_score",
    ]

    df = pbp[features + ["is_pass"]].dropna().copy()
    df_encoded = pd.get_dummies(df, columns=["posteam", "defteam"], drop_first=True)

    X = df_encoded.drop(columns=["is_pass"])
    y = df_encoded["is_pass"]

    duplicate_cols = X.columns[X.columns.duplicated()].tolist()
    if duplicate_cols:
        print("Duplicate columns found:", duplicate_cols)
        raise ValueError(f"Duplicate columns in X: {duplicate_cols}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        eval_metric="logloss",
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    print("\n=== Evaluation ===")
    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print(classification_report(y_test, preds, digits=4))

    importance = pd.Series(model.feature_importances_, index=X.columns)
    importance = importance.sort_values(ascending=False).head(20)
    print("\nTop 20 Feature Importances:")
    print(importance)

    joblib.dump(model, "play_predictor_model.pkl")
    joblib.dump(X.columns.tolist(), "model_columns.pkl")

    print("\nSaved:")
    print("- play_predictor_model.pkl")
    print("- model_columns.pkl")


if __name__ == "__main__":
    main()