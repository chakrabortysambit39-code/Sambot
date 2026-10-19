# Sambot X billing setup (₹299/month)

## What is implemented
- Password-free email sign-in using a 6-digit one-time code.
- Razorpay order creation for INR 299 (29,900 paise), with UPI enabled in checkout.
- Server-side payment signature verification plus a Razorpay webhook signature check.
- Subscription status and monthly usage counters: Free 30 chat requests/month; Premium 1,000/month.
- A Premium modal in the app, plan status, sign-out, and billing details.
- Billing data stored in SQLite at `/var/data/sambot_billing.sqlite3`. Render needs a persistent disk mounted at `/var/data`; the Render Blueprint declares one. Confirm the chosen Render plan supports persistent disks before deploying.

## Required Render environment variables
Set these under the Render service's Environment page:
- `BILLING_SESSION_SECRET`: at least 32 random characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`: use Razorpay **Test Mode** keys first.
- `RAZORPAY_WEBHOOK_SECRET`: a webhook secret you configure in Razorpay.
- `SMTP_HOST`, `SMTP_PORT` (normally 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`: a transactional email account capable of sending sign-in codes.
- `BILLING_DB_PATH` should remain `/var/data/sambot_billing.sqlite3` when the persistent disk is attached.

## Razorpay webhook
In the Razorpay dashboard, add a webhook URL:
`https://YOUR-RENDER-HOST/api/billing/webhook`

Subscribe to `payment.captured`. Save the webhook secret in Render as `RAZORPAY_WEBHOOK_SECRET`. Keep API keys private; never paste them into GitHub or browser code.

## Test checklist before enabling real payments
1. Configure SMTP and `BILLING_SESSION_SECRET`, deploy, and verify the email code flow.
2. Add Razorpay Test Mode keys and the webhook, then deploy again.
3. Sign in, create a ₹299 test order, and complete a test UPI payment using Razorpay's test instructions.
4. Confirm the server verifies the payment and the account status changes to Premium.
5. Test invalid signatures, wrong amounts, duplicate webhooks, expired sessions, and the 30/1,000 monthly usage limits.
6. Only after tests pass, follow Razorpay's onboarding and switch to live credentials. A successful checkout redirect alone never grants Premium.

## Important current limitations
- Razorpay Checkout supports UPI, but available methods depend on merchant/account eligibility and provider settings.
- The current ₹299 payment creates 30 days of access from a verified payment; it is **not an auto-renewing subscription**. Users pay again to extend access.
- SQLite is suitable for a small pilot with one persistent app instance. For multiple app instances or larger production usage, migrate billing state to managed PostgreSQL and add transactional rate limits.
- Email OTP and billing are unavailable until the owner configures the environment variables. Live payments are not enabled or tested by this code change.
