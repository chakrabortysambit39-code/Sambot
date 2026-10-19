# Sambot X direct UPI billing setup

## Payment flow
- Premium costs **₹299 for 30 days** (one-time payment; no automatic renewal).
- Users sign in with a 6-digit email code; there are no passwords.
- The app displays the configured UPI ID and a QR code. Users pay in their own UPI app and submit the UPI transaction reference/UTR.
- A payment request stays pending until the owner checks the transaction in the receiving UPI app and approves it in Sambot X.
- The server grants 30 days of Premium only after the owner-only review endpoint approves a pending request. Ordinary users cannot approve payments or change subscription status.
- **No Razorpay integration is used by this direct-UPI flow.** A transaction reference submitted by a user is not proof of payment on its own.

## Required Render environment variables
Configure these under the Render service's Environment page:
- `BILLING_SESSION_SECRET`: at least 32 random characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `SAMBOT_OWNER_EMAIL`: the exact email address you will use to sign in to Sambot X and access the owner dashboard. This value is checked on the server and must not be hard-coded into source code.
- `SMTP_HOST`, `SMTP_PORT` (normally 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`: an email account that can send sign-in codes.
- `BILLING_DB_PATH` should remain `/var/data/sambot_billing.sqlite3` when the persistent disk is attached.

The UPI payee displayed by the app is `Sambot X`; the configured UPI ID is `chandrani.ghosh480@oksbi`. Verify that the UPI ID is yours/authorized and that the payee name shown in your UPI app is correct before accepting real payments.

## Owner review
1. Sign into Sambot X using the email configured in `SAMBOT_OWNER_EMAIL`.
2. Open **Premium**; the Owner dashboard appears only for that signed-in email.
3. Check each pending UTR against the actual incoming payment in your UPI app/bank transaction history. Do not approve based only on a screenshot or user-submitted reference.
4. Approve only when the amount and transaction match. The server then grants 30 days of Premium and records an audit entry. Reject invalid or unmatched requests.

## Usage limits and storage
- Free: 30 chat requests per UTC calendar month.
- Premium: 1,000 chat requests per UTC calendar month while Premium is active.
- Billing state is stored in SQLite at `/var/data/sambot_billing.sqlite3`. Confirm the selected Render service plan supports persistent disks before deployment. This SQLite setup is intended for a small pilot with one app instance.

## Before launch
1. Configure the environment variables above, especially `SAMBOT_OWNER_EMAIL`, `BILLING_SESSION_SECRET`, and SMTP.
2. Deploy and confirm the email sign-in flow works.
3. Sign in as the configured owner and confirm the Owner dashboard loads.
4. Make a small test payment, submit its UTR from a separate account, confirm the owner can review it, and confirm Premium activates only after approval.
5. Test duplicate UTRs, incorrect references, rejected requests, expired sessions, owner authorization, and the 30/1,000 usage limits.

**Deployment and live payment processing have not been verified by this code change.** The QR code is generated through a third-party QR image endpoint; the UPI transfer itself takes place in the user's UPI app.