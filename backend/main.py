from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from game_tracker import GameTracker

app = FastAPI(title="Football AI Backend")
tracker = GameTracker()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TeamRequest(BaseModel):
    offense: str
    defense: str


class PredictRequest(BaseModel):
    down: int
    ydstogo: int
    yardline_100: int
    game_seconds_remaining: int
    qtr: int
    score_differential: int


class LogPlayRequest(BaseModel):
    actual_play_type: str
    yards_gained: float
    epa: float | None = None


@app.get("/")
def root():
    return {"message": "Football AI backend is running"}


@app.post("/set-teams")
def set_teams(data: TeamRequest):
    tracker.set_teams(data.offense, data.defense)
    return {
        "message": "Teams set successfully",
        "offense": tracker.offense,
        "defense": tracker.defense,
    }


@app.get("/state")
def get_state():
    return {
        "offense": tracker.offense,
        "defense": tracker.defense,
        "prev_play_pass": tracker.prev_play_pass,
        "game_total_plays": tracker.game_total_plays,
        "game_total_passes": tracker.game_total_passes,
        "current_drive_number": tracker.current_drive_number,
        "drive_total_plays": tracker.drive_total_plays,
        "drive_total_passes": tracker.drive_total_passes,
    }


@app.post("/predict")
def predict(data: PredictRequest):
    try:
        return tracker.predict_next_play(
            down=data.down,
            ydstogo=data.ydstogo,
            yardline_100=data.yardline_100,
            game_seconds_remaining=data.game_seconds_remaining,
            qtr=data.qtr,
            score_differential=data.score_differential,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/pending")
def get_pending():
    return tracker.pending_play_context or {}


@app.post("/log-play")
def log_play(data: LogPlayRequest):
    try:
        tracker.log_pending_result(
            actual_play_type=data.actual_play_type,
            yards_gained=data.yards_gained,
            epa=data.epa,
        )
        return {"message": "Play logged successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/play-log")
def get_play_log():
    return tracker.play_log


@app.post("/new-drive")
def new_drive():
    tracker.start_new_drive()
    return {
        "message": "New drive started",
        "drive_number": tracker.current_drive_number,
    }


@app.get("/summary")
def get_summary():
    plays = tracker.play_log

    if not plays:
        return {
            "total_predictions": 0,
            "correct_predictions": 0,
            "game_accuracy": None,
            "last_5_accuracy": None,
            "last_10_accuracy": None,
            "high_conf_accuracy": None,
            "pred_pass_accuracy": None,
            "pred_run_accuracy": None,
            "avg_conf_correct": None,
            "avg_conf_incorrect": None,
            "third_fourth_accuracy": None,
            "long_yardage_accuracy": None,
            "defensive_success_rate": None,
            "explosive_rate_allowed": None,
        }

    def acc(subset):
        if not subset:
            return None
        return sum(1 for p in subset if p["correct_prediction"]) / len(subset)

    def avg_conf(subset):
        if not subset:
            return None
        return sum(p["confidence"] for p in subset) / len(subset)

    total = len(plays)
    correct = sum(1 for p in plays if p["correct_prediction"])
    last_5 = plays[-5:]
    last_10 = plays[-10:]
    high_conf = [p for p in plays if p["confidence"] >= 0.75]
    pred_pass = [p for p in plays if p["predicted_play_type"] == "PASS"]
    pred_run = [p for p in plays if p["predicted_play_type"] == "RUN"]
    correct_plays = [p for p in plays if p["correct_prediction"]]
    incorrect_plays = [p for p in plays if not p["correct_prediction"]]
    third_fourth = [p for p in plays if p["down"] in [3, 4]]
    long_yardage = [
        p for p in plays
        if (
            (p["down"] == 1 and p["ydstogo"] >= 11)
            or (p["down"] == 2 and p["ydstogo"] >= 8)
            or (p["down"] in [3, 4] and p["ydstogo"] >= 7)
        )
    ]

    defensive_successes = sum(1 for p in plays if p.get("defensive_success") is True)
    explosives = sum(1 for p in plays if p.get("explosive_allowed") is True)

    return {
        "total_predictions": total,
        "correct_predictions": correct,
        "game_accuracy": correct / total,
        "last_5_accuracy": acc(last_5),
        "last_10_accuracy": acc(last_10),
        "high_conf_accuracy": acc(high_conf),
        "pred_pass_accuracy": acc(pred_pass),
        "pred_run_accuracy": acc(pred_run),
        "avg_conf_correct": avg_conf(correct_plays),
        "avg_conf_incorrect": avg_conf(incorrect_plays),
        "third_fourth_accuracy": acc(third_fourth),
        "long_yardage_accuracy": acc(long_yardage),
        "defensive_success_rate": defensive_successes / total,
        "explosive_rate_allowed": explosives / total,
    }