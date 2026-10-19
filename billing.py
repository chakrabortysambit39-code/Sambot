"""Password-free email identity and manual direct-UPI Premium payments for Sambot X.

Payments are not verified automatically. The configured owner checks the UPI app and
approves a pending transaction reference from the owner-only dashboard.
"""
import os, re, json, time, hmac, hashlib, secrets, smtplib, sqlite3
from email.message import EmailMessage
from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/billing", tags=["billing"])
PRICE_PAISE = 29900
PLAN_ID = "premium_30_days"
UPI_ID = "chandrani.ghosh480@oksbi"
PAYEE_NAME = "Sambot X"
DB_PATH = os.getenv("BILLING_DB_PATH", "/var/data/sambot_billing.sqlite3")
OTP_TTL = 600
SESSION_TTL = 60 * 60 * 24 * 30
FREE_LIMIT = 30
PREMIUM_LIMIT = 1000
PREMIUM_SECONDS = 30 * 24 * 60 * 60

def _db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS otp(email TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, sent_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS subscriptions(email TEXT PRIMARY KEY, status TEXT NOT NULL, provider_subscription_id TEXT, current_period_end INTEGER, updated_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS payments(payment_id TEXT PRIMARY KEY, email TEXT NOT NULL, order_id TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS usage(email TEXT NOT NULL, period TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(email, period));
    CREATE TABLE IF NOT EXISTS orders(order_id TEXT PRIMARY KEY, email TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS payment_requests(
      id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, reference TEXT NOT NULL UNIQUE,
      amount INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', submitted_at INTEGER NOT NULL,
      reviewed_at INTEGER, reviewed_by TEXT, review_note TEXT
    );
    CREATE TABLE IF NOT EXISTS billing_audit(
      id INTEGER PRIMARY KEY AUTOINCREMENT, actor_email TEXT NOT NULL, action TEXT NOT NULL,
      target_email TEXT NOT NULL, reference TEXT, created_at INTEGER NOT NULL, note TEXT
    );
    """)
    return con

def _secret():
    s = os.getenv("BILLING_SESSION_SECRET")
    if not s or len(s) < 32:
        raise HTTPException(503, "Billing is not configured: set a random BILLING_SESSION_SECRET of at least 32 characters.")
    return s.encode()

def _token(email):
    payload = {"email": email, "exp": int(time.time()) + SESSION_TTL}
    raw = __import__("base64").urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig

def _email_from_token(authorization):
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in with your email to manage billing.")
    try:
        raw, sig = authorization[7:].split(".", 1)
        expected = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError()
        payload = json.loads(__import__("base64").urlsafe_b64decode(raw + "=" * ((4 - len(raw) % 4) % 4)))
        if payload["exp"] < int(time.time()):
            raise ValueError()
        return str(payload["email"]).lower()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Your session expired. Please sign in again.")

def _owner_email():
    email = os.getenv("SAMBOT_OWNER_EMAIL", "").strip().lower()
    if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(503, "Owner access is not configured. Set SAMBOT_OWNER_EMAIL in Render.")
    return email

def _require_owner(authorization):
    email = _email_from_token(authorization)
    if not hmac.compare_digest(email, _owner_email()):
        raise HTTPException(403, "Owner-only action.")
    return email

def _send_otp(email, code):
    host = os.getenv("SMTP_HOST"); user = os.getenv("SMTP_USER"); password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or user
    if not all([host, user, password, sender]):
        raise HTTPException(503, "Email sign-in is not configured yet. Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM in Render.")
    msg = EmailMessage()
    msg["Subject"] = "Your Sambot X sign-in code"
    msg["From"] = sender; msg["To"] = email
    msg.set_content(f"Your Sambot X verification code is {code}. It expires in 10 minutes. If you did not request this, ignore this email.")
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
        server.starttls(); server.login(user, password); server.send_message(msg)

class OTPRequest(BaseModel):
    email: str
class OTPVerify(BaseModel):
    email: str
    code: str
class UpiPaymentRequest(BaseModel):
    reference: str
    amount_rupees: int = 299
class ReviewRequest(BaseModel):
    request_id: int
    decision: str
    note: str = ""

@router.get("/config")
def billing_config():
    return {
        "enabled": bool(os.getenv("BILLING_SESSION_SECRET") and os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD")),
        "email_login_enabled": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and (os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"))),
        "provider": "Direct UPI; manual owner approval",
        "upi_id": UPI_ID, "payee_name": PAYEE_NAME,
        "price_paise": PRICE_PAISE, "currency": "INR", "plan": PLAN_ID,
        "price_display": "₹299 for 30 days", "manual_approval": True,
        "owner_configured": bool(os.getenv("SAMBOT_OWNER_EMAIL"))
    }

@router.post("/request-code")
def request_code(body: OTPRequest, request: Request):
    email = str(body.email).lower().strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Enter a valid email address.")
    _secret()
    now = int(time.time())
    con = _db()
    try:
        old = con.execute("SELECT sent_at FROM otp WHERE email=?", (email,)).fetchone()
        if old and now - old["sent_at"] < 60:
            raise HTTPException(429, "Wait 60 seconds before requesting another code.")
        code = f"{secrets.randbelow(1000000):06d}"
        _send_otp(email, code)
        digest = hmac.new(_secret(), (email + ":" + code).encode(), hashlib.sha256).hexdigest()
        con.execute("INSERT INTO otp(email,code_hash,expires,attempts,sent_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash,expires=excluded.expires,attempts=0,sent_at=excluded.sent_at", (email, digest, now + OTP_TTL, 0, now))
        con.commit()
        return {"ok": True, "message": "Verification code sent. Check your email."}
    finally:
        con.close()

@router.post("/verify-code")
def verify_code(body: OTPVerify):
    email = str(body.email).lower().strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Enter a valid email address.")
    if not re.fullmatch(r"\d{6}", body.code):
        raise HTTPException(400, "Enter the 6-digit code.")
    con = _db(); now = int(time.time())
    try:
        row = con.execute("SELECT * FROM otp WHERE email=?", (email,)).fetchone()
        if not row or row["expires"] < now or row["attempts"] >= 5:
            raise HTTPException(400, "Code expired or invalid. Request a new code.")
        digest = hmac.new(_secret(), (email + ":" + body.code).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, row["code_hash"]):
            con.execute("UPDATE otp SET attempts=attempts+1 WHERE email=?", (email,)); con.commit()
            raise HTTPException(400, "Incorrect code.")
        con.execute("INSERT INTO users(email,created_at) VALUES(?,?) ON CONFLICT(email) DO NOTHING", (email, now))
        con.execute("DELETE FROM otp WHERE email=?", (email,)); con.commit()
        return {"ok": True, "token": _token(email), "email": email, "is_owner": email == os.getenv("SAMBOT_OWNER_EMAIL", "").strip().lower()}
    finally:
        con.close()

@router.get("/status")
def subscription_status(authorization: str | None = Header(default=None)):
    email = _email_from_token(authorization); con = _db()
    try:
        row = con.execute("SELECT status,current_period_end FROM subscriptions WHERE email=?", (email,)).fetchone()
        active = bool(row and row["status"] == "active" and (not row["current_period_end"] or row["current_period_end"] > int(time.time())))
        period = time.strftime("%Y-%m", time.gmtime())
        usage = con.execute("SELECT count FROM usage WHERE email=? AND period=?", (email, period)).fetchone()
        return {"email": email, "plan": "premium" if active else "free", "subscription_status": row["status"] if row else "free",
                "current_period_end": row["current_period_end"] if row else None,
                "usage": usage["count"] if usage else 0,
                "limits": {"free_messages_per_month": FREE_LIMIT, "premium_messages_per_month": PREMIUM_LIMIT},
                "price_display": "₹299 for 30 days", "is_owner": email == os.getenv("SAMBOT_OWNER_EMAIL", "").strip().lower()}
    finally:
        con.close()

@router.post("/submit-upi")
def submit_upi(body: UpiPaymentRequest, authorization: str | None = Header(default=None)):
    email = _email_from_token(authorization)
    reference = body.reference.strip()
    if body.amount_rupees != 299:
        raise HTTPException(400, "The payment request amount must be ₹299.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,100}", reference):
        raise HTTPException(400, "Enter the UPI transaction reference/UTR (6–100 letters or numbers).")
    now = int(time.time()); con = _db()
    try:
        already = con.execute("SELECT id,status FROM payment_requests WHERE reference=?", (reference,)).fetchone()
        if already:
            raise HTTPException(409, "That transaction reference has already been submitted.")
        con.execute("INSERT INTO payment_requests(email,reference,amount,status,submitted_at) VALUES(?,?,?,'pending',?)", (email, reference, PRICE_PAISE, now))
        con.commit()
        return {"ok": True, "status": "pending", "message": "Payment reference submitted. Premium will activate only after the owner verifies the payment."}
    finally:
        con.close()

@router.get("/requests")
def my_payment_requests(authorization: str | None = Header(default=None)):
    email = _email_from_token(authorization); con = _db()
    try:
        rows = con.execute("SELECT id,reference,amount,status,submitted_at,reviewed_at,review_note FROM payment_requests WHERE email=? ORDER BY submitted_at DESC LIMIT 20", (email,)).fetchall()
        return {"requests": [dict(r) for r in rows]}
    finally:
        con.close()

@router.get("/owner/requests")
def owner_requests(authorization: str | None = Header(default=None)):
    owner = _require_owner(authorization); con = _db()
    try:
        rows = con.execute("SELECT id,email,reference,amount,status,submitted_at FROM payment_requests ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, submitted_at DESC LIMIT 200").fetchall()
        return {"owner": owner, "requests": [dict(r) for r in rows]}
    finally:
        con.close()

@router.post("/owner/review")
def owner_review(body: ReviewRequest, authorization: str | None = Header(default=None)):
    owner = _require_owner(authorization)
    if body.decision not in ("approve", "reject"):
        raise HTTPException(400, "Decision must be approve or reject.")
    note = body.note.strip()[:500]
    now = int(time.time()); con = _db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM payment_requests WHERE id=?", (body.request_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Payment request not found.")
        if row["status"] != "pending":
            raise HTTPException(409, "This payment request has already been reviewed.")
        status = "approved" if body.decision == "approve" else "rejected"
        con.execute("UPDATE payment_requests SET status=?,reviewed_at=?,reviewed_by=?,review_note=? WHERE id=?", (status, now, owner, note, body.request_id))
        if body.decision == "approve":
            period_end = max(now, int((con.execute("SELECT current_period_end FROM subscriptions WHERE email=?", (row["email"],)).fetchone() or {"current_period_end": 0})["current_period_end"] or 0)) + PREMIUM_SECONDS
            con.execute("INSERT INTO subscriptions(email,status,provider_subscription_id,current_period_end,updated_at) VALUES(?,'active',?,?,?) ON CONFLICT(email) DO UPDATE SET status='active',current_period_end=excluded.current_period_end,updated_at=excluded.updated_at", (row["email"], "manual-upi:" + row["reference"], period_end, now))
            con.execute("INSERT OR IGNORE INTO payments(payment_id,email,order_id,amount,status,created_at) VALUES(?,?,?,?,?,?)", ("manual-upi:" + row["reference"], row["email"], "manual-upi", row["amount"], "approved", now))
        con.execute("INSERT INTO billing_audit(actor_email,action,target_email,reference,created_at,note) VALUES(?,?,?,?,?,?)", (owner, status, row["email"], row["reference"], now, note))
        con.commit()
        return {"ok": True, "status": status, "email": row["email"], "message": "Premium activated for 30 days." if body.decision == "approve" else "Payment request rejected."}
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

@router.get("/owner/summary")
def owner_summary(authorization: str | None = Header(default=None)):
    owner = _require_owner(authorization); con = _db()
    try:
        users = con.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        pending = con.execute("SELECT COUNT(*) AS n FROM payment_requests WHERE status='pending'").fetchone()["n"]
        active = con.execute("SELECT COUNT(*) AS n FROM subscriptions WHERE status='active' AND current_period_end>?", (int(time.time()),)).fetchone()["n"]
        recent = con.execute("SELECT actor_email,action,target_email,reference,created_at,note FROM billing_audit ORDER BY created_at DESC LIMIT 50").fetchall()
        return {"owner": owner, "users": users, "pending_requests": pending, "active_premium": active, "audit": [dict(r) for r in recent]}
    finally:
        con.close()

@router.post("/cancel")
def cancel_subscription(authorization: str | None = Header(default=None)):
    _email_from_token(authorization)
    return {"ok": True, "message": "Premium is a one-time 30-day purchase. There is no auto-renewal to cancel."}

def record_usage(authorization: str | None = None, client_key: str = "anonymous"):
    email = _email_from_token(authorization) if authorization else None
    now = int(time.time()); period = time.strftime("%Y-%m", time.gmtime())
    con = _db()
    try:
        active = False
        if email:
            sub = con.execute("SELECT status,current_period_end FROM subscriptions WHERE email=?", (email,)).fetchone()
            active = bool(sub and sub["status"] == "active" and (not sub["current_period_end"] or sub["current_period_end"] > now))
        limit = PREMIUM_LIMIT if active else FREE_LIMIT
        who = email if email else "anon:" + hashlib.sha256((os.getenv("BILLING_SESSION_SECRET", "") + (client_key or "anonymous")).encode()).hexdigest()[:32]
        row = con.execute("SELECT count FROM usage WHERE email=? AND period=?", (who, period)).fetchone()
        count = row["count"] if row else 0
        if count >= limit:
            raise HTTPException(429, "Monthly chat limit reached. Sign in and upgrade to Premium for a higher limit.")
        con.execute("INSERT INTO usage(email,period,count) VALUES(?,?,1) ON CONFLICT(email,period) DO UPDATE SET count=count+1", (who, period))
        con.commit()
        return {"ok": True, "plan": "premium" if active else "free", "remaining": limit - count - 1}
    finally:
        con.close()
