import joblib
import nfl_data_py as nfl
import pandas as pd
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

import sys

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR / "backend"))

from model_wrappers import EncodedClassifier
from feature_builder import build_situational_flags


SEASONS = [2020, 2021, 2022, 2023]
BACKEND_DIR = BASE_DIR / "backend"


def make_xgb_classifier(num_classes=None):
    params = {
        "n_estimators": 300,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "random_state": 42,
        "eval_metric": "mlogloss" if num_classes and num_classes > 2 else "logloss",
    }

    if num_classes and num_classes > 2:
        params["objective"] = "multi:softprob"
        params["num_class"] = num_classes

    return XGBClassifier(**params)


def normalize_direction(value):
    if pd.isna(value):
        return None

    value = str(value).strip().lower()

    mapping = {
        "left": "left",
        "middle": "middle",
        "center": "middle",
        "right": "right",
    }

    return mapping.get(value)


def classify_run_concept(row):
    run_location = normalize_direction(row.get("run_location"))
    run_gap = row.get("run_gap")
    ydstogo = row.get("ydstogo")

    if pd.isna(run_gap):
        return None

    run_gap = str(run_gap).strip().lower()

    if run_location == "middle" and run_gap == "guard" and pd.notna(ydstogo) and float(ydstogo) <= 1:
        return "qb_sneak"

    if run_location == "middle" and run_gap in {"guard", "tackle"}:
        return "inside_zone"

    if run_location in {"left", "right"} and run_gap == "guard":
        return "power_counter"

    if run_location in {"left", "right"} and run_gap == "end":
        return "edge_sweep"

    if run_location in {"left", "right"} and run_gap in {"tackle", "end"}:
        return "outside_zone"

    return None


def classify_pass_concept(row):
    qb_scramble = row.get("qb_scramble", 0)
    air_yards = row.get("air_yards")

    if pd.notna(qb_scramble) and int(qb_scramble) == 1:
        return "qb_scramble"

    if pd.isna(air_yards):
        return None

    air_yards = float(air_yards)

    if air_yards <= 0:
        return "screen"

    if air_yards <= 5:
        return "quick_game"

    if air_yards <= 15:
        return "intermediate"

    return "deep_shot"


def add_shared_features(pbp):
    pbp = pbp.copy()

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
        result_type="expand",
    )

    for col in situational_rows.columns:
        pbp[col] = situational_rows[col]

    return pbp


def get_feature_columns(include_is_pass=False):
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

    if include_is_pass:
        features.append("is_pass")

    return features


def prepare_encoded_xy(df, feature_columns, target_column):
    working = df[feature_columns + [target_column]].dropna().copy()
    encoded = pd.get_dummies(working, columns=["posteam", "defteam"], drop_first=True)

    X = encoded.drop(columns=[target_column])
    y = encoded[target_column]

    duplicate_cols = X.columns[X.columns.duplicated()].tolist()
    if duplicate_cols:
        raise ValueError(f"Duplicate columns in X: {duplicate_cols}")

    return X, y


def train_and_save_binary_run_pass_model(pbp):
    print("\n=== Training Tier 1 Run/Pass Model ===")

    features = get_feature_columns(include_is_pass=False)
    X, y = prepare_encoded_xy(pbp.assign(target_is_pass=pbp["is_pass"]), features, "target_is_pass")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = make_xgb_classifier()
    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print(classification_report(y_test, preds, digits=4))

    importance = pd.Series(model.feature_importances_, index=X.columns)
    print("\nTop 20 Feature Importances (Tier 1):")
    print(importance.sort_values(ascending=False).head(20))

    joblib.dump(model, BACKEND_DIR / "play_predictor_model.pkl")
    joblib.dump(X.columns.tolist(), BACKEND_DIR / "model_columns.pkl")

    print("\nSaved:")
    print(f"- {BACKEND_DIR / 'play_predictor_model.pkl'}")
    print(f"- {BACKEND_DIR / 'model_columns.pkl'}")


def train_and_save_direction_model(pbp):
    print("\n=== Training Tier 2 Direction Model ===")

    pbp = pbp.copy()

    pbp["play_direction"] = pbp.apply(
        lambda row: normalize_direction(row["run_location"])
        if row["play_type"] == "run"
        else normalize_direction(row["pass_location"]),
        axis=1,
    )

    direction_df = pbp.dropna(subset=["play_direction"]).copy()

    if direction_df.empty:
        raise ValueError("No valid play_direction labels found.")

    features = get_feature_columns(include_is_pass=True)
    X, y = prepare_encoded_xy(direction_df, features, "play_direction")

    unique_classes = sorted(y.unique())
    print(f"Direction classes: {unique_classes}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    wrapped_model = EncodedClassifier(
        make_xgb_classifier(num_classes=len(unique_classes))
    )
    wrapped_model.fit(X_train, y_train)

    preds = wrapped_model.predict(X_test)

    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print(classification_report(y_test, preds, digits=4))

    importance = pd.Series(wrapped_model.feature_importances_, index=X.columns)
    print("\nTop 20 Feature Importances (Direction):")
    print(importance.sort_values(ascending=False).head(20))

    joblib.dump(wrapped_model, BACKEND_DIR / "direction_predictor_model.pkl")
    joblib.dump(X.columns.tolist(), BACKEND_DIR / "direction_model_columns.pkl")

    print("\nSaved:")
    print(f"- {BACKEND_DIR / 'direction_predictor_model.pkl'}")
    print(f"- {BACKEND_DIR / 'direction_model_columns.pkl'}")


def train_and_save_run_concept_model(pbp):
    print("\n=== Training Tier 2 Run Concept Model ===")

    run_df = pbp[pbp["play_type"] == "run"].copy()
    run_df["run_concept"] = run_df.apply(classify_run_concept, axis=1)
    run_df = run_df.dropna(subset=["run_concept"]).copy()

    if run_df.empty:
        raise ValueError("No valid run_concept labels found.")

    features = get_feature_columns(include_is_pass=False)
    X, y = prepare_encoded_xy(run_df, features, "run_concept")

    unique_classes = sorted(y.unique())
    print(f"Run concept classes: {unique_classes}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    wrapped_model = EncodedClassifier(
        make_xgb_classifier(num_classes=len(unique_classes))
    )
    wrapped_model.fit(X_train, y_train)

    preds = wrapped_model.predict(X_test)

    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print(classification_report(y_test, preds, digits=4))

    importance = pd.Series(wrapped_model.feature_importances_, index=X.columns)
    print("\nTop 20 Feature Importances (Run Concept):")
    print(importance.sort_values(ascending=False).head(20))

    joblib.dump(wrapped_model, BACKEND_DIR / "run_concept_predictor_model.pkl")
    joblib.dump(X.columns.tolist(), BACKEND_DIR / "run_concept_model_columns.pkl")

    print("\nSaved:")
    print(f"- {BACKEND_DIR / 'run_concept_predictor_model.pkl'}")
    print(f"- {BACKEND_DIR / 'run_concept_model_columns.pkl'}")


def train_and_save_pass_concept_model(pbp):
    print("\n=== Training Tier 2 Pass Concept Model ===")

    pass_df = pbp[pbp["play_type"] == "pass"].copy()
    pass_df["pass_concept"] = pass_df.apply(classify_pass_concept, axis=1)
    pass_df = pass_df.dropna(subset=["pass_concept"]).copy()

    class_counts = pass_df["pass_concept"].value_counts()
    valid_classes = class_counts[class_counts >= 20].index
    pass_df = pass_df[pass_df["pass_concept"].isin(valid_classes)].copy()

    print("Filtered pass concept classes:")
    print(pass_df["pass_concept"].value_counts())

    if pass_df.empty:
        raise ValueError("No valid pass_concept labels found after filtering rare classes.")

    features = get_feature_columns(include_is_pass=False)
    X, y = prepare_encoded_xy(pass_df, features, "pass_concept")

    unique_classes = sorted(y.unique())
    print(f"Pass concept classes: {unique_classes}")

    if len(unique_classes) < 2:
        raise ValueError("Need at least two pass concept classes to train the model.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    wrapped_model = EncodedClassifier(
        make_xgb_classifier(num_classes=len(unique_classes))
    )
    wrapped_model.fit(X_train, y_train)

    preds = wrapped_model.predict(X_test)

    print("Accuracy:", round(accuracy_score(y_test, preds), 4))
    print(classification_report(y_test, preds, digits=4))

    importance = pd.Series(wrapped_model.feature_importances_, index=X.columns)
    print("\nTop 20 Feature Importances (Pass Concept):")
    print(importance.sort_values(ascending=False).head(20))

    joblib.dump(wrapped_model, BACKEND_DIR / "pass_concept_predictor_model.pkl")
    joblib.dump(X.columns.tolist(), BACKEND_DIR / "pass_concept_model_columns.pkl")

    print("\nSaved:")
    print(f"- {BACKEND_DIR / 'pass_concept_predictor_model.pkl'}")
    print(f"- {BACKEND_DIR / 'pass_concept_model_columns.pkl'}")


def main():
    print(f"Loading nflfastR play-by-play data for seasons: {SEASONS}")
    pbp = nfl.import_pbp_data(SEASONS)

    required_base_columns = [
        "game_id",
        "play_id",
        "drive",
        "play_type",
        "down",
        "ydstogo",
        "yardline_100",
        "game_seconds_remaining",
        "qtr",
        "score_differential",
        "posteam",
        "defteam",
    ]

    pbp = pbp[pbp["play_type"].isin(["run", "pass"])].copy()
    pbp = pbp.dropna(subset=required_base_columns).copy()
    pbp = add_shared_features(pbp)

    BACKEND_DIR.mkdir(parents=True, exist_ok=True)

    train_and_save_binary_run_pass_model(pbp)
    train_and_save_direction_model(pbp)
    train_and_save_run_concept_model(pbp)
    train_and_save_pass_concept_model(pbp)

    print("\n✅ All Tier 1 and Tier 2 models saved successfully.")


if __name__ == "__main__":
    main()