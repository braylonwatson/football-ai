import joblib
import pandas as pd

from feature_builder import build_feature_row, safe_rate
from recommendation_engine import get_confidence_tier


def load_model_and_columns():
    model = joblib.load("play_predictor_model.pkl")
    model_columns = joblib.load("model_columns.pkl")
    return model, model_columns


def get_defensive_strategy(
    prediction: str,
    run_prob: float,
    pass_prob: float,
    down: int,
    ydstogo: int,
    yardline_100: int,
    score_differential: int,
    confidence_tier: str,
    situational_snapshot: dict | None = None,
):
    confidence = max(run_prob, pass_prob)

    short_yardage = ydstogo <= 2
    medium_yardage = 3 <= ydstogo <= 6
    long_yardage = (
        (down == 1 and ydstogo >= 11) or
        (down == 2 and ydstogo >= 8) or
        (down in [3, 4] and ydstogo >= 7)
    )
    red_zone = yardline_100 <= 20
    backed_up = yardline_100 >= 90

    situation_notes = []
    pass_rate_signals = []

    if situational_snapshot:
        for key, stats in situational_snapshot.items():
            if stats["plays"] > 0:
                rate = stats["pass_rate"]
                pass_rate_signals.append(rate)
                situation_notes.append(
                    f"{key} pass_rate={rate:.3f} ({stats['passes']}/{stats['plays']})"
                )

    live_pass_rate = None
    if pass_rate_signals:
        live_pass_rate = sum(pass_rate_signals) / len(pass_rate_signals)

    # Blend model output with live situational tendency
    if live_pass_rate is not None:
        blended_pass_prob = (0.7 * pass_prob) + (0.3 * live_pass_rate)
    else:
        blended_pass_prob = pass_prob

    blended_run_prob = 1 - blended_pass_prob
    blended_prediction = "PASS" if blended_pass_prob >= 0.5 else "RUN"

    tendency_conflict = False
    if live_pass_rate is not None:
        if prediction == "RUN" and live_pass_rate >= 0.65:
            tendency_conflict = True
        elif prediction == "PASS" and live_pass_rate <= 0.35:
            tendency_conflict = True

    softened = False
    if confidence_tier in ["WEAK", "NEUTRAL"] or tendency_conflict:
        softened = True

    if confidence_tier == "NEUTRAL":
        return {
            "defensive_personnel": "Match offense",
            "front": "Balanced front",
            "coverage_shell": "Neutral shell",
            "pressure": "Standard rush",
            "aggression": "Conservative",
            "primary_focus": "Stay structurally sound",
            "reason": "Prediction confidence is low, so avoid overcommitting.",
            "situation_notes": situation_notes,
            "blended_pass_probability": round(blended_pass_prob, 3),
            "blended_run_probability": round(blended_run_prob, 3),
        }

    if blended_prediction == "RUN":
        if short_yardage:
            if softened:
                return {
                    "defensive_personnel": "Base / Big Nickel",
                    "front": "Firm box, not all-in",
                    "coverage_shell": "Single-high with play-action awareness",
                    "pressure": "Controlled pressure",
                    "aggression": "Balanced",
                    "primary_focus": "Defend short-yardage run while respecting quick pass",
                    "reason": (
                        f"Blended run lean is {blended_run_prob:.1%}. "
                        f"Model and/or live tendency suggest some pass risk, so do not fully sell out."
                    ),
                    "situation_notes": situation_notes,
                    "blended_pass_probability": round(blended_pass_prob, 3),
                    "blended_run_probability": round(blended_run_prob, 3),
                }

            return {
                "defensive_personnel": "Base / Heavy",
                "front": "Heavy box",
                "coverage_shell": "Single-high",
                "pressure": "Run pressure optional",
                "aggression": "Aggressive",
                "primary_focus": "Defend interior run / short conversion",
                "reason": f"Blended run probability is {blended_run_prob:.1%} in a short-yardage situation.",
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        if red_zone:
            if softened:
                return {
                    "defensive_personnel": "Base / Big Nickel",
                    "front": "Compact front",
                    "coverage_shell": "Single-high or matchup zone",
                    "pressure": "Controlled pressure",
                    "aggression": "Balanced",
                    "primary_focus": "Close run lanes but stay alert for quick pass/play-action",
                    "reason": (
                        f"Blended run lean is {blended_run_prob:.1%}, "
                        f"but live situational tendency raises pass risk."
                    ),
                    "situation_notes": situation_notes,
                    "blended_pass_probability": round(blended_pass_prob, 3),
                    "blended_run_probability": round(blended_run_prob, 3),
                }

            return {
                "defensive_personnel": "Base / Big Nickel",
                "front": "Compact front",
                "coverage_shell": "Single-high or matchup zone",
                "pressure": "Controlled pressure",
                "aggression": "Balanced",
                "primary_focus": "Close run lanes and watch play-action",
                "reason": f"Blended run probability is {blended_run_prob:.1%} in the red zone.",
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        if backed_up:
            return {
                "defensive_personnel": "Base",
                "front": "Attack front",
                "coverage_shell": "Single-high",
                "pressure": "Run pressure optional",
                "aggression": "Aggressive",
                "primary_focus": "Force run into a crowded box and win field position",
                "reason": f"Blended run probability is {blended_run_prob:.1%} while offense is backed up.",
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        if softened:
            return {
                "defensive_personnel": "Base / Big Nickel",
                "front": "Balanced front",
                "coverage_shell": "Single-high with pass alert",
                "pressure": "Standard rush",
                "aggression": "Balanced",
                "primary_focus": "Lean run first without losing pass integrity",
                "reason": (
                    f"Blended run lean is {blended_run_prob:.1%}, "
                    f"but live tendencies suggest the offense still may throw here."
                ),
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        return {
            "defensive_personnel": "Base",
            "front": "Balanced-to-heavy front",
            "coverage_shell": "Single-high",
            "pressure": "Standard rush",
            "aggression": "Balanced",
            "primary_focus": "Lean run first",
            "reason": f"Blended run probability is {blended_run_prob:.1%}.",
            "situation_notes": situation_notes,
            "blended_pass_probability": round(blended_pass_prob, 3),
            "blended_run_probability": round(blended_run_prob, 3),
        }

    if long_yardage or down in [3, 4]:
        if softened:
            return {
                "defensive_personnel": "Nickel / Big Nickel",
                "front": "Balanced pass front",
                "coverage_shell": "Two-high with underneath awareness",
                "pressure": "Sim pressure optional",
                "aggression": "Balanced",
                "primary_focus": "Defend the sticks without giving away run support",
                "reason": (
                    f"Blended pass lean is {blended_pass_prob:.1%}, "
                    f"but live tendencies soften a full pass-commit recommendation."
                ),
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        return {
            "defensive_personnel": "Nickel / Dime",
            "front": "Pass front",
            "coverage_shell": "Two-high / sticks shell",
            "pressure": "Sim pressure or pass-rush emphasis",
            "aggression": "Balanced",
            "primary_focus": "Defend the sticks / force checkdown",
            "reason": f"Blended pass probability is {blended_pass_prob:.1%} in a likely passing situation.",
            "situation_notes": situation_notes,
            "blended_pass_probability": round(blended_pass_prob, 3),
            "blended_run_probability": round(blended_run_prob, 3),
        }

    if red_zone:
        if softened:
            return {
                "defensive_personnel": "Big Nickel",
                "front": "Balanced front",
                "coverage_shell": "Match coverage",
                "pressure": "Selective pressure",
                "aggression": "Balanced",
                "primary_focus": "Protect quick-game while staying sound versus run",
                "reason": (
                    f"Blended pass lean is {blended_pass_prob:.1%}, "
                    f"but the live tendency does not support a full pass sellout."
                ),
                "situation_notes": situation_notes,
                "blended_pass_probability": round(blended_pass_prob, 3),
                "blended_run_probability": round(blended_run_prob, 3),
            }

        return {
            "defensive_personnel": "Nickel / Big Nickel",
            "front": "Balanced front",
            "coverage_shell": "Match coverage",
            "pressure": "Selective pressure",
            "aggression": "Balanced",
            "primary_focus": "Protect against quick-game and spacing concepts",
            "reason": f"Blended pass probability is {blended_pass_prob:.1%} in the red zone.",
            "situation_notes": situation_notes,
            "blended_pass_probability": round(blended_pass_prob, 3),
            "blended_run_probability": round(blended_run_prob, 3),
        }

    if medium_yardage:
        return {
            "defensive_personnel": "Nickel",
            "front": "Balanced pass front",
            "coverage_shell": "Two-high",
            "pressure": "Pressure optional",
            "aggression": "Moderate",
            "primary_focus": "Lean pass first while staying sound versus draw/RPO",
            "reason": f"Blended pass probability is {blended_pass_prob:.1%} in a medium-yardage situation.",
            "situation_notes": situation_notes,
            "blended_pass_probability": round(blended_pass_prob, 3),
            "blended_run_probability": round(blended_run_prob, 3),
        }

    return {
        "defensive_personnel": "Nickel",
        "front": "Balanced pass front",
        "coverage_shell": "Two-high",
        "pressure": "Pressure optional",
        "aggression": "Moderate",
        "primary_focus": "Lean pass first",
        "reason": f"Blended pass probability is {blended_pass_prob:.1%}.",
        "situation_notes": situation_notes,
        "blended_pass_probability": round(blended_pass_prob, 3),
        "blended_run_probability": round(blended_run_prob, 3),
    }



def classify_defensive_success(yards_gained: float, down: int, ydstogo: int) -> tuple[bool, str]:
    """
    Defensive success = offense fails standard success-rate thresholds.
    1st down: offense needs >= 40% of yards to go
    2nd down: offense needs >= 60% of yards to go
    3rd/4th down: offense needs full conversion
    """
    if down == 1:
        threshold = 0.4 * ydstogo
        rule = "1st down: offense needs at least 40% of yards-to-go"
    elif down == 2:
        threshold = 0.6 * ydstogo
        rule = "2nd down: offense needs at least 60% of yards-to-go"
    else:
        threshold = ydstogo
        rule = "3rd/4th down: offense needs full conversion"

    return yards_gained < threshold, rule


def classify_explosive_play(actual_play_type: str, yards_gained: float) -> bool:
    actual = actual_play_type.strip().upper()
    if actual == "RUN":
        return yards_gained >= 12
    return yards_gained >= 16


class GameTracker:
    def __init__(self):
        self.model, self.model_columns = load_model_and_columns()
        self.offense = None
        self.defense = None

        self.prev_play_pass = 0
        self.game_total_plays = 0
        self.game_total_passes = 0

        self.current_drive_number = 1
        self.drive_total_plays = 0
        self.drive_total_passes = 0

        self.situation_stats = {
            "third_down": {"plays": 0, "passes": 0},
            "fourth_down": {"plays": 0, "passes": 0},
            "short_yardage": {"plays": 0, "passes": 0},
            "medium_yardage": {"plays": 0, "passes": 0},
            "long_yardage": {"plays": 0, "passes": 0},
            "red_zone": {"plays": 0, "passes": 0},
            "leading": {"plays": 0, "passes": 0},
            "trailing": {"plays": 0, "passes": 0},
        }

        self.play_log = []
        self.pending_play_context = None

    def set_teams(self, offense, defense):
        self.offense = offense.strip().upper()
        self.defense = defense.strip().upper()

    def _current_game_pass_rate(self):
        if self.game_total_plays < 8:
            return 0.5
        return safe_rate(self.game_total_passes, self.game_total_plays)

    def _current_drive_pass_rate(self):
        if self.drive_total_plays < 4:
            return 0.5
        return safe_rate(self.drive_total_passes, self.drive_total_plays)

    def _is_short_yardage(self, down, ydstogo):
        return ydstogo <= 2

    def _is_medium_yardage(self, down, ydstogo):
        return (
            (down == 1 and 3 <= ydstogo <= 9) or
            (down == 2 and 3 <= ydstogo <= 7) or
            (down in [3, 4] and 3 <= ydstogo <= 6)
        )

    def _is_long_yardage(self, down, ydstogo):
        return (
            (down == 1 and ydstogo >= 11) or
            (down == 2 and ydstogo >= 8) or
            (down in [3, 4] and ydstogo >= 7)
        )

    def _is_red_zone(self, yardline_100):
        return yardline_100 <= 20

    def _context_keys(self, down, ydstogo, yardline_100, score_differential):
        keys = []

        if down == 3:
            keys.append("third_down")
        if down == 4:
            keys.append("fourth_down")

        if self._is_short_yardage(down, ydstogo):
            keys.append("short_yardage")
        elif self._is_medium_yardage(down, ydstogo):
            keys.append("medium_yardage")
        elif self._is_long_yardage(down, ydstogo):
            keys.append("long_yardage")

        if self._is_red_zone(yardline_100):
            keys.append("red_zone")

        if score_differential > 0:
            keys.append("leading")
        elif score_differential < 0:
            keys.append("trailing")

        return keys

    def _get_situation_snapshot(self, down, ydstogo, yardline_100, score_differential):
        keys = self._context_keys(down, ydstogo, yardline_100, score_differential)
        snapshot = {}

        for key in keys:
            plays = self.situation_stats[key]["plays"]
            passes = self.situation_stats[key]["passes"]
            snapshot[key] = {
                "plays": plays,
                "passes": passes,
                "pass_rate": round(safe_rate(passes, plays), 3),
            }

        return snapshot

    def _update_situation_stats(self, down, ydstogo, yardline_100, score_differential, is_pass):
        keys = self._context_keys(down, ydstogo, yardline_100, score_differential)
        for key in keys:
            self.situation_stats[key]["plays"] += 1
            self.situation_stats[key]["passes"] += is_pass

    def start_new_drive(self):
        self.current_drive_number += 1
        self.drive_total_plays = 0
        self.drive_total_passes = 0
        print(f"Started new drive: Drive {self.current_drive_number}")

    def _build_model_input(
        self,
        down,
        ydstogo,
        yardline_100,
        game_seconds_remaining,
        qtr,
        score_differential
    ):
        game_pass_rate = self._current_game_pass_rate()
        drive_pass_rate = self._current_drive_pass_rate()

        df = build_feature_row(
            down=down,
            ydstogo=ydstogo,
            yardline_100=yardline_100,
            game_seconds_remaining=game_seconds_remaining,
            qtr=qtr,
            score_differential=score_differential,
            posteam=self.offense,
            defteam=self.defense,
            prev_play_pass=self.prev_play_pass,
            game_pass_rate=game_pass_rate,
            drive_pass_rate=drive_pass_rate,
        )

        df = pd.get_dummies(df, columns=["posteam", "defteam"], drop_first=True)
        df = df.reindex(columns=self.model_columns, fill_value=0)

        return df, game_pass_rate, drive_pass_rate

    def show_live_state(self):
        print("\n=== Live Game State ===")
        print(f"Offense: {self.offense}")
        print(f"Defense: {self.defense}")
        print(f"Previous play pass flag: {self.prev_play_pass}")
        print(f"Game total plays: {self.game_total_plays}")
        print(f"Game total passes: {self.game_total_passes}")
        print(f"Game pass rate: {self._current_game_pass_rate():.3f}")
        print(f"Current drive: {self.current_drive_number}")
        print(f"Drive total plays: {self.drive_total_plays}")
        print(f"Drive total passes: {self.drive_total_passes}")
        print(f"Drive pass rate: {self._current_drive_pass_rate():.3f}")

        print("\n=== Situational Tendencies (Current Game) ===")
        for key, value in self.situation_stats.items():
            rate = safe_rate(value["passes"], value["plays"])
            print(
                f"{key}: plays={value['plays']}, "
                f"passes={value['passes']}, "
                f"pass_rate={rate:.3f}"
            )

    def predict_next_play(
        self,
        down,
        ydstogo,
        yardline_100,
        game_seconds_remaining,
        qtr,
        score_differential
    ):
        if self.offense is None or self.defense is None:
            raise ValueError("Teams not set. Call set_teams() first.")

        df, g_rate, d_rate = self._build_model_input(
            down=down,
            ydstogo=ydstogo,
            yardline_100=yardline_100,
            game_seconds_remaining=game_seconds_remaining,
            qtr=qtr,
            score_differential=score_differential
        )

        pred = self.model.predict(df)[0]
        prob = self.model.predict_proba(df)[0]

        prediction = "PASS" if pred == 1 else "RUN"
        run_prob = float(prob[0])
        pass_prob = float(prob[1])
        confidence = max(run_prob, pass_prob)
        tier = get_confidence_tier(run_prob, pass_prob)

        situation_alert = None
        if down == 4 and ydstogo >= 4 and prediction == "RUN":
            situation_alert = "PASS-DOWN ALERT: 4th & medium/long is usually pass-heavy"
        elif down == 3 and ydstogo >= 7 and prediction == "RUN":
            situation_alert = "PASS-DOWN ALERT: 3rd & long is usually pass-heavy"

        situational_snapshot = self._get_situation_snapshot(
            down=down,
            ydstogo=ydstogo,
            yardline_100=yardline_100,
            score_differential=score_differential,
        )

        defensive_strategy = get_defensive_strategy(
            prediction=prediction,
            run_prob=run_prob,
            pass_prob=pass_prob,
            down=down,
            ydstogo=ydstogo,
            yardline_100=yardline_100,
            score_differential=score_differential,
            confidence_tier=tier,
            situational_snapshot=situational_snapshot,
        )

        self.pending_play_context = {
            "drive_number": self.current_drive_number,
            "down": down,
            "ydstogo": ydstogo,
            "yardline_100": yardline_100,
            "game_seconds_remaining": game_seconds_remaining,
            "qtr": qtr,
            "score_differential": score_differential,
            "pred_prev_play_pass_used": self.prev_play_pass,
            "pred_game_pass_rate_used": g_rate,
            "pred_drive_pass_rate_used": d_rate,
            "situational_snapshot": situational_snapshot,
            "predicted_play_type": prediction,
            "run_probability": run_prob,
            "pass_probability": pass_prob,
            "confidence": confidence,
            "confidence_tier": tier,
            "situation_alert": situation_alert,
            "defensive_strategy": defensive_strategy,
        }

        return {
            "prediction": prediction,
            "run_probability": run_prob,
            "pass_probability": pass_prob,
            "confidence": round(confidence, 3),
            "confidence_tier": tier,
            "game_pass_rate_used": round(g_rate, 3),
            "drive_pass_rate_used": round(d_rate, 3),
            "situational_snapshot": situational_snapshot,
            "situation_alert": situation_alert,
            "defensive_strategy": defensive_strategy,
        }

    def log_pending_result(self, actual_play_type, yards_gained=None, epa=None):
        if self.pending_play_context is None:
            raise ValueError("No pending predicted play to log.")

        actual = actual_play_type.strip().upper()
        if actual not in ["RUN", "PASS"]:
            raise ValueError("actual_play_type must be 'run' or 'pass'")

        if yards_gained is None:
            raise ValueError("yards_gained is required for success tracking.")

        yards_gained = float(yards_gained)
        epa = None if epa is None else float(epa)
        is_pass = 1 if actual == "PASS" else 0

        play = self.pending_play_context.copy()
        play["actual_play_type"] = actual
        play["yards_gained"] = yards_gained
        play["epa"] = epa
        play["correct_prediction"] = (play["predicted_play_type"] == actual)

        defensive_success, success_rule = classify_defensive_success(
            yards_gained=yards_gained,
            down=play["down"],
            ydstogo=play["ydstogo"],
        )
        play["defensive_success"] = defensive_success
        play["success_rule"] = success_rule
        play["explosive_allowed"] = classify_explosive_play(actual, yards_gained)
        play["first_down_allowed"] = yards_gained >= play["ydstogo"]
        play["defensive_success_epa"] = None if epa is None else (epa < 0)

        self.play_log.append(play)

        self.prev_play_pass = is_pass
        self.game_total_plays += 1
        self.game_total_passes += is_pass
        self.drive_total_plays += 1
        self.drive_total_passes += is_pass

        self._update_situation_stats(
            down=play["down"],
            ydstogo=play["ydstogo"],
            yardline_100=play["yardline_100"],
            score_differential=play["score_differential"],
            is_pass=is_pass,
        )

        self.pending_play_context = None

    def show_play_log(self):
        if not self.play_log:
            print("\nNo plays logged yet.")
            return

        print("\n=== Game Play Log ===")
        for i, play in enumerate(self.play_log, start=1):
            print(
                f"{i}. Drive {play['drive_number']} | "
                f"Q{play['qtr']} | Down {play['down']} & {play['ydstogo']} | "
                f"Yardline_100={play['yardline_100']} | "
                f"ScoreDiff={play['score_differential']} | "
                f"Pred={play['predicted_play_type']} | "
                f"Conf={play['confidence']:.3f} ({play['confidence_tier']}) | "
                f"Actual={play['actual_play_type']} | "
                f"Yards={play.get('yards_gained', 'N/A')} | "
                f"DefSuccess={play.get('defensive_success', 'N/A')} | "
                f"Correct={play['correct_prediction']}"
            )

    def show_pending_play(self):
        if self.pending_play_context is None:
            print("\nNo pending prediction waiting to be logged.")
            return

        play = self.pending_play_context
        strategy = play["defensive_strategy"]

        print("\n=== Pending Predicted Play ===")
        print(
            f"Drive {play['drive_number']} | "
            f"Q{play['qtr']} | Down {play['down']} & {play['ydstogo']} | "
            f"Yardline_100={play['yardline_100']} | "
            f"ScoreDiff={play['score_differential']}"
        )
        print(
            f"Prediction: {play['predicted_play_type']} | "
            f"RunProb={play['run_probability']:.3f} | "
            f"PassProb={play['pass_probability']:.3f} | "
            f"Confidence={play['confidence']:.3f} ({play['confidence_tier']})"
        )
        print(
            f"GameRate={play['pred_game_pass_rate_used']:.3f} | "
            f"DriveRate={play['pred_drive_pass_rate_used']:.3f}"
        )

        if play["situational_snapshot"]:
            print("\nSituational Tendencies Used For Context:")
            for key, stats in play["situational_snapshot"].items():
                print(
                    f"- {key}: plays={stats['plays']}, "
                    f"passes={stats['passes']}, "
                    f"pass_rate={stats['pass_rate']:.3f}"
                )

        if play.get("situation_alert"):
            print("\nSituation Alert:")
            print(f"- {play['situation_alert']}")

        print("\n=== Defensive Strategy Suggestion ===")
        print(f"- Personnel: {strategy['defensive_personnel']}")
        print(f"- Front: {strategy['front']}")
        print(f"- Coverage Shell: {strategy['coverage_shell']}")
        print(f"- Pressure: {strategy['pressure']}")
        print(f"- Aggression: {strategy['aggression']}")
        print(f"- Primary Focus: {strategy['primary_focus']}")
        print(f"- Reason: {strategy['reason']}")
        print(f"- Blended Pass Probability: {strategy['blended_pass_probability']:.3f}")
        print(f"- Blended Run Probability: {strategy['blended_run_probability']:.3f}")

        if strategy.get("situation_notes"):
            print("- Situation Notes:")
            for note in strategy["situation_notes"]:
                print(f"  * {note}")

    def show_performance_summary(self):
        if not self.play_log:
            print("\nNo logged plays yet.")
            return

        total = len(self.play_log)
        correct = sum(1 for p in self.play_log if p["correct_prediction"])
        last_5 = self.play_log[-5:]
        last_10 = self.play_log[-10:]

        def acc(plays):
            if not plays:
                return 0.0
            return sum(1 for p in plays if p["correct_prediction"]) / len(plays)

        def avg_conf(plays):
            if not plays:
                return 0.0
            return sum(p["confidence"] for p in plays) / len(plays)

        high_conf = [p for p in self.play_log if p["confidence"] >= 0.75]
        pred_pass = [p for p in self.play_log if p["predicted_play_type"] == "PASS"]
        pred_run = [p for p in self.play_log if p["predicted_play_type"] == "RUN"]
        correct_plays = [p for p in self.play_log if p["correct_prediction"]]
        incorrect_plays = [p for p in self.play_log if not p["correct_prediction"]]
        third_fourth = [p for p in self.play_log if p["down"] in [3, 4]]
        long_yardage = [p for p in self.play_log if self._is_long_yardage(p["down"], p["ydstogo"])]

        print("\n=== Live Performance Summary ===")
        print(f"Total predictions: {total}")
        print(f"Correct predictions: {correct}")
        print(f"Game accuracy: {correct / total:.3f}")
        print(f"Last 5 accuracy: {acc(last_5):.3f}")
        print(f"Last 10 accuracy: {acc(last_10):.3f}")
        print(f"High-confidence (>=0.75) accuracy: {acc(high_conf):.3f}" if high_conf else "High-confidence (>=0.75) accuracy: N/A")
        print(f"Predicted PASS accuracy: {acc(pred_pass):.3f}" if pred_pass else "Predicted PASS accuracy: N/A")
        print(f"Predicted RUN accuracy: {acc(pred_run):.3f}" if pred_run else "Predicted RUN accuracy: N/A")
        print(f"Avg confidence (correct): {avg_conf(correct_plays):.3f}" if correct_plays else "Avg confidence (correct): N/A")
        print(f"Avg confidence (incorrect): {avg_conf(incorrect_plays):.3f}" if incorrect_plays else "Avg confidence (incorrect): N/A")
        print(f"3rd/4th down accuracy: {acc(third_fourth):.3f}" if third_fourth else "3rd/4th down accuracy: N/A")
        print(f"Long-yardage accuracy: {acc(long_yardage):.3f}" if long_yardage else "Long-yardage accuracy: N/A")


if __name__ == "__main__":
    tracker = GameTracker()

    print("=== Football Play Prediction Game Tracker ===")
    offense = input("Enter offense team abbreviation (e.g. KC): ")
    defense = input("Enter defense team abbreviation (e.g. BUF): ")
    tracker.set_teams(offense, defense)

    while True:
        print("\nOptions:")
        print("1. Predict next play")
        print("2. Log actual result for pending play")
        print("3. Start new drive")
        print("4. Show play log")
        print("5. Show pending prediction")
        print("6. Show live state")
        print("7. Show performance summary")
        print("8. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            try:
                down = int(input("Down: "))
                ydstogo = int(input("Yards to go: "))
                yardline_100 = int(input("Yardline_100: "))
                game_seconds_remaining = int(input("Game seconds remaining: "))
                qtr = int(input("Quarter: "))
                score_differential = int(input("Score differential (offense perspective): "))

                result = tracker.predict_next_play(
                    down=down,
                    ydstogo=ydstogo,
                    yardline_100=yardline_100,
                    game_seconds_remaining=game_seconds_remaining,
                    qtr=qtr,
                    score_differential=score_differential
                )

                print("\nPrediction Result:")
                print(result)
                print("\nNow watch the play, then use option 2 to log the actual result.")

            except ValueError as e:
                print(f"Input error: {e}")

        elif choice == "2":
            try:
                actual_play_type = input("Actual play type (run/pass): ")
                yards_gained = float(input("Yards gained on play: ").strip())
                epa_raw = input("EPA on play (optional, press Enter to skip): ").strip()
                epa = float(epa_raw) if epa_raw else None
                tracker.log_pending_result(actual_play_type, yards_gained=yards_gained, epa=epa)
                print("Pending play result logged successfully.")

            except ValueError as e:
                print(f"Input error: {e}")

        elif choice == "3":
            tracker.start_new_drive()

        elif choice == "4":
            tracker.show_play_log()

        elif choice == "5":
            tracker.show_pending_play()

        elif choice == "6":
            tracker.show_live_state()

        elif choice == "7":
            tracker.show_performance_summary()

        elif choice == "8":
            print("Exiting game tracker.")
            break

        else:
            print("Invalid option. Please choose 1, 2, 3, 4, 5, 6, 7, or 8.")
