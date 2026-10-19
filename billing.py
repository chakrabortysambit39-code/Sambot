"""Email OTP identity and Razorpay UPI subscription APIs for Sambot X.

Requires Razorpay account credentials and SMTP settings before live use.
Payment status is only activated after server-side signature verification or a verified webhook.
"""
import os, re, json, time, hmac, hashlib, secrets, smtplib, sqlite3
from email.message import EmailMessage
from urllib.parse import quote
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/billing", tags=["billing"])
PRICE_PAISE = 29900
PLAN_ID = "premium_monthly"
DB_PATH = os.getenv("BILLING_DB_PATH", "/var/data/sambot_billing.sqlite3")
OTP_TTL = 600
SESSION_TTL = 60 * 60 * 24 * 30

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
    """)
    return con

def _secret():
    s=os.getenv("BILLING_SESSION_SECRET")
    if not s or len(s)<32:
        raise HTTPException(503, "Billing is not configured: set a random BILLING_SESSION_SECRET of at least 32 characters.")
    return s.encode()

def _token(email):
    payload={"email":email,"exp":int(time.time())+SESSION_TTL}
    raw=__import__("base64").urlsafe_b64encode(json.dumps(payload,separators=(",",":")).encode()).decode().rstrip("=")
    sig=hmac.new(_secret(),raw.encode(),hashlib.sha256).hexdigest()
    return raw+"."+sig

def _email_from_token(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401,"Sign in with your email to manage billing.")
    try:
        raw,sig=authorization[7:].split(".",1)
        expected=hmac.new(_secret(),raw.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): raise ValueError()
        payload=json.loads(__import__("base64").urlsafe_b64decode(raw+"="*((4-len(raw)%4)%4)))
        if payload["exp"]<int(time.time()): raise ValueError()
        return payload["email"]
    except HTTPException: raise
    except Exception: raise HTTPException(401,"Your session expired. Please sign in again.")

def _send_otp(email, code):
    host=os.getenv("SMTP_HOST"); user=os.getenv("SMTP_USER"); password=os.getenv("SMTP_PASSWORD")
    sender=os.getenv("SMTP_FROM") or user
    if not all([host,user,password,sender]):
        raise HTTPException(503,"Email sign-in is not configured yet. Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM in Render.")
    msg=EmailMessage()
    msg["Subject"]="Your Sambot X sign-in code"
    msg["From"]=sender; msg["To"]=email
    msg.set_content(f"Your Sambot X verification code is {code}. It expires in 10 minutes. If you did not request this, ignore this email.")
    port=int(os.getenv("SMTP_PORT","587"))
    with smtplib.SMTP(host,port,timeout=15) as server:
        server.starttls(); server.login(user,password); server.send_message(msg)

def _razorpay():
    key=os.getenv("RAZORPAY_KEY_ID"); secret=os.getenv("RAZORPAY_KEY_SECRET")
    if not key or not secret: raise HTTPException(503,"UPI payments are not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in Render.")
    return key,secret

class OTPRequest(BaseModel):
    email: str
class OTPVerify(BaseModel):
    email: str
    code: str
class OrderRequest(BaseModel):
    plan: str = PLAN_ID
class VerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.get("/config")
def billing_config():
    return {"enabled":bool(os.getenv("BILLING_SESSION_SECRET") and os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET")),
            "email_login_enabled":bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_FROM")),
            "provider":"Razorpay UPI/card checkout","price_paise":PRICE_PAISE,"currency":"INR","plan":PLAN_ID,
            "price_display":"₹299/month","live_payments_enabled":bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET") and os.getenv("RAZORPAY_WEBHOOK_SECRET"))}

@router.post("/request-code")
def request_code(body: OTPRequest, request: Request):
    email=str(body.email).lower().strip()
    if not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", email): raise HTTPException(400,"Enter a valid email address.")
    now=int(time.time())
    con=_db()
    try:
        old=con.execute("SELECT sent_at FROM otp WHERE email=?",(email,)).fetchone()
        if old and now-old["sent_at"]<60: raise HTTPException(429,"Wait 60 seconds before requesting another code.")
        code=f"{secrets.randbelow(1000000):06d}"
        _send_otp(email,code)
        digest=hmac.new(_secret(),(email+":"+code).encode(),hashlib.sha256).hexdigest()
        con.execute("INSERT INTO otp(email,code_hash,expires,attempts,sent_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash,expires=excluded.expires,attempts=0,sent_at=excluded.sent_at",(email,digest,now+OTP_TTL,0,now))
        con.commit()
        return {"ok":True,"message":"Verification code sent. Check your email."}
    finally: con.close()

@router.post("/verify-code")
def verify_code(body: OTPVerify):
    email=str(body.email).lower().strip()
    if not re.fullmatch(r"\d{6}",body.code): raise HTTPException(400,"Enter the 6-digit code.")
    con=_db(); now=int(time.time())
    try:
        row=con.execute("SELECT * FROM otp WHERE email=?",(email,)).fetchone()
        if not row or row["expires"]<now or row["attempts"]>=5: raise HTTPException(400,"Code expired or invalid. Request a new code.")
        digest=hmac.new(_secret(),(email+":"+body.code).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest,row["code_hash"]):
            con.execute("UPDATE otp SET attempts=attempts+1 WHERE email=?",(email,));con.commit()
            raise HTTPException(400,"Incorrect code.")
        con.execute("INSERT INTO users(email,created_at) VALUES(?,?) ON CONFLICT(email) DO NOTHING",(email,now))
        con.execute("DELETE FROM otp WHERE email=?",(email,));con.commit()
        return {"ok":True,"token":_token(email),"email":email}
    finally: con.close()

@router.get("/status")
def subscription_status(authorization: str|None=Header(default=None)):
    email=_email_from_token(authorization); con=_db()
    try:
        row=con.execute("SELECT status,current_period_end FROM subscriptions WHERE email=?",(email,)).fetchone()
        active=bool(row and row["status"]=="active" and (not row["current_period_end"] or row["current_period_end"]>int(time.time())))
        period=time.strftime("%Y-%m",time.gmtime())
        usage=con.execute("SELECT count FROM usage WHERE email=? AND period=?",(email,period)).fetchone()
        return {"email":email,"plan":"premium" if active else "free","subscription_status":row["status"] if row else "free","current_period_end":row["current_period_end"] if row else None,"usage":usage["count"] if usage else 0,"limits":{"free_messages_per_month":30,"premium_messages_per_month":1000},"price_display":"₹299/month"}
    finally: con.close()

@router.post("/create-order")
def create_order(body: OrderRequest, authorization: str|None=Header(default=None)):
    email=_email_from_token(authorization)
    if body.plan!=PLAN_ID: raise HTTPException(400,"Unknown plan.")
    key,secret=_razorpay()
    import requests
    response=requests.post("https://api.razorpay.com/v1/orders",auth=(key,secret),json={"amount":PRICE_PAISE,"currency":"INR","receipt":"sambot_"+secrets.token_hex(8),"notes":{"email":email,"plan":PLAN_ID}},timeout=20)
    if not response.ok: raise HTTPException(502,"Payment provider could not create an order. Please try again.")
    order=response.json()
    con=_db()
    try:
        con.execute("INSERT INTO orders(order_id,email,amount,status,created_at) VALUES(?,?,?,?,?)",(order["id"],email,PRICE_PAISE,"created",int(time.time())));con.commit()
    finally: con.close()
    return {"order_id":order["id"],"amount":PRICE_PAISE,"currency":"INR","key_id":key,"email":email,"name":"Sambot X","description":"Sambot X Premium — one month"}

def _activate(email, payment_id, order_id, amount):
    now=int(time.time()); period_end=now+30*24*60*60
    con=_db()
    try:
        existing=con.execute("SELECT status FROM payments WHERE payment_id=?",(payment_id,)).fetchone()
        if existing and existing["status"]=="captured": return
        con.execute("INSERT OR REPLACE INTO payments(payment_id,email,order_id,amount,status,created_at) VALUES(?,?,?,?,?,?)",(payment_id,email,order_id,amount,"captured",now))
        con.execute("INSERT INTO subscriptions(email,status,provider_subscription_id,current_period_end,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(email) DO UPDATE SET status='active',provider_subscription_id=excluded.provider_subscription_id,current_period_end=excluded.current_period_end,updated_at=excluded.updated_at",(email,"active",payment_id,period_end,now))
        con.execute("UPDATE orders SET status='paid' WHERE order_id=?",(order_id,));con.commit()
    finally: con.close()

@router.post("/verify-payment")
def verify_payment(body: VerifyPayment, authorization: str|None=Header(default=None)):
    email=_email_from_token(authorization); key,secret=_razorpay()
    expected=hmac.new(secret.encode(),(body.razorpay_order_id+"|"+body.razorpay_payment_id).encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,body.razorpay_signature): raise HTTPException(400,"Payment signature verification failed.")
    con=_db()
    try: order=con.execute("SELECT * FROM orders WHERE order_id=? AND email=?",(body.razorpay_order_id,email)).fetchone()
    finally: con.close()
    if not order: raise HTTPException(400,"Order not found for this account.")
    import requests
    response=requests.get("https://api.razorpay.com/v1/payments/"+quote(body.razorpay_payment_id,safe=""),auth=(key,secret),timeout=20)
    if not response.ok: raise HTTPException(502,"Could not verify payment with provider.")
    payment=response.json()
    if payment.get("order_id")!=body.razorpay_order_id or payment.get("amount")!=PRICE_PAISE or payment.get("currency")!="INR" or payment.get("status") not in ("captured","authorized"):
        raise HTTPException(400,"Payment details do not match this subscription.")
    if payment.get("status")=="authorized":
        cap=requests.post("https://api.razorpay.com/v1/payments/"+quote(body.razorpay_payment_id,safe="")+"/capture",auth=(key,secret),json={"amount":PRICE_PAISE},timeout=20)
        if not cap.ok or cap.json().get("status")!="captured": raise HTTPException(502,"Payment authorization succeeded but capture could not be confirmed.")
    _activate(email,body.razorpay_payment_id,body.razorpay_order_id,PRICE_PAISE)
    return {"ok":True,"plan":"premium","message":"Payment verified. Premium is active."}

@router.post("/webhook")
async def razorpay_webhook(request: Request):
    hook_secret=os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not hook_secret: raise HTTPException(503,"Webhook secret is not configured.")
    raw=await request.body(); supplied=request.headers.get("x-razorpay-signature","")
    expected=hmac.new(hook_secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,supplied): raise HTTPException(400,"Invalid webhook signature.")
    event=json.loads(raw)
    if event.get("event")=="payment.captured":
        entity=event.get("payload",{}).get("payment",{}).get("entity",{})
        order_id=entity.get("order_id");payment_id=entity.get("id");amount=entity.get("amount")
        if order_id and payment_id and amount==PRICE_PAISE:
            con=_db()
            try: order=con.execute("SELECT email FROM orders WHERE order_id=?",(order_id,)).fetchone()
            finally: con.close()
            if order: _activate(order["email"],payment_id,order_id,amount)
    elif event.get("event") in ("subscription.cancelled","subscription.halted"):
        entity=event.get("payload",{}).get("subscription",{}).get("entity",{})
        subid=entity.get("id")
        if subid:
            con=_db()
            try: con.execute("UPDATE subscriptions SET status='cancelled',updated_at=? WHERE provider_subscription_id=?",(int(time.time()),subid));con.commit()
            finally: con.close()
    return {"ok":True}

@router.post("/cancel")
def cancel_subscription(authorization: str|None=Header(default=None)):
    email=_email_from_token(authorization);con=_db()
    try:
        row=con.execute("SELECT status,current_period_end FROM subscriptions WHERE email=?",(email,)).fetchone()
        if not row or row["status"]!="active": raise HTTPException(400,"No active Premium access.")
        return {"ok":True,"message":"This is a one-time 30-day purchase with no auto-renewal, so there is no recurring payment to cancel. Premium remains active until the displayed expiry date."}
    finally: con.close()

@router.post("/record-usage")
def record_usage(authorization: str|None=Header(default=None), client_key: str = "anonymous"):
    email=_email_from_token(authorization) if authorization else None
    now=int(time.time());period=time.strftime("%Y-%m",time.gmtime())
    con=_db()
    try:
        active=False
        if email:
            sub=con.execute("SELECT status,current_period_end FROM subscriptions WHERE email=?",(email,)).fetchone()
            active=bool(sub and sub["status"]=="active" and (not sub["current_period_end"] or sub["current_period_end"]>now))
        limit=1000 if active else 30
        if email: who=email
        else: who="anon:"+hashlib.sha256((os.getenv("BILLING_SESSION_SECRET","")+ (client_key or "anonymous")).encode()).hexdigest()[:32]
        row=con.execute("SELECT count FROM usage WHERE email=? AND period=?",(who,period)).fetchone()
        count=row["count"] if row else 0
        if count>=limit: raise HTTPException(429,"Monthly chat limit reached. Sign in and upgrade to Premium for a higher limit.")
        con.execute("INSERT INTO usage(email,period,count) VALUES(?,?,1) ON CONFLICT(email,period) DO UPDATE SET count=count+1",(who,period));con.commit()
        return {"ok":True,"plan":"premium" if active else "free","remaining":limit-count-1}
    finally: con.close()
