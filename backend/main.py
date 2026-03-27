from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from game_tracker import GameTracker

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from passlib.hash import pbkdf2_sha256
from dotenv import load_dotenv
import stripe
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID_TIER2 = os.getenv("STRIPE_PRICE_ID_TIER2")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

stripe.api_key = STRIPE_SECRET_KEY

VALID_TEAMS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
    "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS",
}


def normalize_team(team: Optional[str]) -> str:
    return (team or "").strip().upper()


def normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def validate_team_code(team: str, field_name: str) -> None:
    if team not in VALID_TEAMS:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid NFL team abbreviation.",
        )


def hash_password(password: str):
    return pbkdf2_sha256.hash(password)


def verify_password(password: str, hashed: str):
    return pbkdf2_sha256.verify(password, hashed)


def subscription_is_active(status: Optional[str]) -> bool:
    return status in {"active", "trialing"}


def stripe_value(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # Stripe / subscription fields
    tier = Column(String, nullable=False, default="free")
    subscription_status = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)


class SavedGame(Base):
    __tablename__ = "saved_games"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    game_state = Column(JSON, nullable=False)

    user = relationship("User")


Base.metadata.create_all(bind=engine)

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
    user_id: Optional[int] = None


class LogPlayRequest(BaseModel):
    actual_play_type: str
    yards_gained: float
    epa: Optional[float] = None


class SignupRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SaveGameRequest(BaseModel):
    user_id: int
    title: str
    game_state: dict


class LoadGameRequest(BaseModel):
    game_id: int


class CheckoutSessionRequest(BaseModel):
    user_id: int


def get_user_by_id(db, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def sync_user_subscription_fields(user: User, subscription_status: Optional[str]) -> None:
    user.subscription_status = subscription_status
    user.tier = "tier2" if subscription_is_active(subscription_status) else "free"


def get_or_create_stripe_customer(db, user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.username,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    db.refresh(user)
    return user.stripe_customer_id


def update_user_from_subscription_event(db, subscription_obj) -> None:
    customer_id = stripe_value(subscription_obj, "customer")
    subscription_id = stripe_value(subscription_obj, "id")
    status = stripe_value(subscription_obj, "status")

    if not customer_id:
        return

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    user.stripe_subscription_id = subscription_id
    sync_user_subscription_fields(user, status)
    db.commit()


@app.get("/")
def root():
    return {"message": "Football AI backend is running"}


@app.get("/tier2-status")
def tier2_status():
    return {"tier2_available": tracker.tier2_available()}


@app.get("/me/subscription")
def get_my_subscription(user_id: int):
    db = SessionLocal()
    try:
        user = get_user_by_id(db, user_id)
        return {
            "user_id": user.id,
            "tier": user.tier or "free",
            "subscription_status": user.subscription_status,
            "tier2_access": subscription_is_active(user.subscription_status),
            "tier2_models_available": tracker.tier2_available(),
        }
    finally:
        db.close()


@app.post("/signup")
def signup(data: SignupRequest):
    db = SessionLocal()
    try:
        email = normalize_email(data.email)
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        user = User(
            username=data.username.strip(),
            email=email,
            password_hash=hash_password(data.password),
            tier="free",
            subscription_status=None,
            stripe_customer_id=None,
            stripe_subscription_id=None,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {
            "user_id": user.id,
            "username": user.username,
            "tier": user.tier,
            "subscription_status": user.subscription_status,
        }
    finally:
        db.close()


@app.post("/login")
def login(data: LoginRequest):
    db = SessionLocal()
    try:
        email = normalize_email(data.email)
        user = db.query(User).filter(User.email == email).first()

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "user_id": user.id,
            "username": user.username,
            "tier": user.tier or "free",
            "subscription_status": user.subscription_status,
        }
    finally:
        db.close()


@app.post("/create-checkout-session")
def create_checkout_session(data: CheckoutSessionRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key is not configured.")
    if not STRIPE_PRICE_ID_TIER2:
        raise HTTPException(status_code=500, detail="Stripe price ID is not configured.")

    db = SessionLocal()
    try:
        user = get_user_by_id(db, data.user_id)

        customer_id = get_or_create_stripe_customer(db, user)

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(user.id),
            line_items=[
                {
                    "price": STRIPE_PRICE_ID_TIER2,
                    "quantity": 1,
                }
            ],
            metadata={"user_id": str(user.id)},
            success_url=f"{FRONTEND_URL}/?success=true",
            cancel_url=f"{FRONTEND_URL}/?canceled=true",
        )

        return {"url": session.url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")
    finally:
        db.close()


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_SECRET_KEY:
        return JSONResponse({"detail": "Stripe secret key is not configured."}, status_code=500)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=STRIPE_WEBHOOK_SECRET,
            )
        else:
            # Fallback for local testing if webhook secret is not set yet
            event = stripe.Event.construct_from(await request.json(), stripe.api_key)
    except ValueError:
        return JSONResponse({"detail": "Invalid webhook payload."}, status_code=400)
    except stripe.error.SignatureVerificationError:
        return JSONResponse({"detail": "Invalid webhook signature."}, status_code=400)
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=400)

    db = SessionLocal()
    try:
        event_type = stripe_value(event, "type")
        event_data = stripe_value(event, "data")
        event_obj = stripe_value(event_data, "object")

        if event_type == "checkout.session.completed":
            customer_id = stripe_value(event_obj, "customer")
            subscription_id = stripe_value(event_obj, "subscription")
            metadata = stripe_value(event_obj, "metadata", {}) or {}
            user_id = stripe_value(metadata, "user_id") or stripe_value(event_obj, "client_reference_id")

            user = None
            if user_id:
                try:
                    user = db.query(User).filter(User.id == int(user_id)).first()
                except ValueError:
                    user = None

            if not user and customer_id:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

            if user:
                if customer_id:
                    user.stripe_customer_id = customer_id
                if subscription_id:
                    user.stripe_subscription_id = subscription_id
                    try:
                        sub = stripe.Subscription.retrieve(subscription_id)
                        sync_user_subscription_fields(user, stripe_value(sub, "status", "active"))
                    except Exception as sub_err:
                        print("Stripe subscription retrieve failed:", str(sub_err))
                        sync_user_subscription_fields(user, "active")
                else:
                    sync_user_subscription_fields(user, "active")

                db.commit()
            else:
                print("checkout.session.completed: no matching user found")

        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            update_user_from_subscription_event(db, event_obj)

        elif event_type == "invoice.payment_failed":
            customer_id = stripe_value(event_obj, "customer")
            if customer_id:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
                if user:
                    sync_user_subscription_fields(user, "past_due")
                    db.commit()

        elif event_type == "invoice.payment_succeeded":
            customer_id = stripe_value(event_obj, "customer")
            subscription_id = stripe_value(event_obj, "subscription")
            if customer_id:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
                if user:
                    if subscription_id:
                        user.stripe_subscription_id = subscription_id
                    sync_user_subscription_fields(user, "active")
                    db.commit()

        return JSONResponse({"status": "success"})

    except Exception as e:
        print("Webhook handler error:", str(e))
        return JSONResponse({"detail": f"Webhook handler error: {str(e)}"}, status_code=500)
    finally:
        db.close()


@app.post("/games")
def save_game(data: SaveGameRequest):
    db = SessionLocal()
    try:
        game = SavedGame(
            user_id=data.user_id,
            title=data.title,
            game_state=data.game_state,
        )

        db.add(game)
        db.commit()
        db.refresh(game)

        return {"game_id": game.id}
    finally:
        db.close()


@app.get("/games/{user_id}")
def get_games(user_id: int):
    db = SessionLocal()
    try:
        games = db.query(SavedGame).filter(SavedGame.user_id == user_id).all()

        return [
            {
                "id": game.id,
                "user_id": game.user_id,
                "title": game.title,
                "game_state": game.game_state,
            }
            for game in games
        ]
    finally:
        db.close()


@app.post("/games/load")
def load_game(data: LoadGameRequest):
    db = SessionLocal()
    try:
        game = db.query(SavedGame).filter(SavedGame.id == data.game_id).first()

        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        state = game.game_state

        tracker.offense = normalize_team(state.get("offense"))
        tracker.defense = normalize_team(state.get("defense"))
        tracker.play_log = state.get("play_log", [])
        tracker.current_drive_number = state.get("current_drive_number", 1)

        return {"message": "Game loaded", "state": state}
    finally:
        db.close()


@app.delete("/games/{game_id}")
def delete_game(game_id: int, user_id: int):
    db = SessionLocal()
    try:
        game = (
            db.query(SavedGame)
            .filter(SavedGame.id == game_id, SavedGame.user_id == user_id)
            .first()
        )

        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        db.delete(game)
        db.commit()

        return {"message": "Game deleted"}
    finally:
        db.close()


@app.post("/set-teams")
def set_teams(data: TeamRequest):
    offense = normalize_team(data.offense)
    defense = normalize_team(data.defense)

    if not offense or not defense:
        raise HTTPException(
            status_code=400,
            detail="Both offense and defense teams are required.",
        )

    validate_team_code(offense, "Offense")
    validate_team_code(defense, "Defense")

    tracker.set_teams(offense, defense)
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
        "tier2_available": tracker.tier2_available(),
    }


@app.post("/predict")
def predict(data: PredictRequest):
    offense = normalize_team(getattr(tracker, "offense", ""))
    defense = normalize_team(getattr(tracker, "defense", ""))

    if not offense or not defense:
        raise HTTPException(
            status_code=400,
            detail="Set both teams before requesting a prediction.",
        )

    validate_team_code(offense, "Offense")
    validate_team_code(defense, "Defense")

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


@app.post("/predict-tier2")
def predict_tier2(data: PredictRequest):
    if not data.user_id:
        raise HTTPException(
            status_code=403,
            detail="Tier 2 prediction requires a logged-in Tier 2 account.",
        )

    db = SessionLocal()
    try:
        user = get_user_by_id(db, data.user_id)

        if not subscription_is_active(user.subscription_status):
            raise HTTPException(
                status_code=403,
                detail="Tier 2 subscription required for this endpoint.",
            )
    finally:
        db.close()

    offense = normalize_team(getattr(tracker, "offense", ""))
    defense = normalize_team(getattr(tracker, "defense", ""))

    if not offense or not defense:
        raise HTTPException(
            status_code=400,
            detail="Set both teams before requesting a prediction.",
        )

    validate_team_code(offense, "Offense")
    validate_team_code(defense, "Defense")

    try:
        return tracker.predict_next_play_tier2(
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