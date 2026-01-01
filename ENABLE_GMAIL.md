# Enable Gmail for Compensation Workflow

## Status
- ✅ Gmail credentials configured (`credentials.json`)
- ✅ OAuth token exists (`token.json`)
- ❌ Google API Python packages NOT installed

## Install Required Packages

Run this command to install the Google API libraries:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Verify Installation

After installing, verify Gmail is working:

```bash
python -c "import sys; sys.path.insert(0, 'backend'); from gmail_service import is_gmail_configured; print(f'Gmail configured: {is_gmail_configured()}')"
```

Should output:
```
Gmail configured: True
```

## Test with Compensation Workflow

### Test Success Scenario (with real email):
```bash
python test_compensation_direct.py success
```

This will:
- Book flight and hotel
- Process payment successfully
- Send **real confirmation email** to `mkanoor@gmail.com`

### Test Failure Scenario (with real email):
```bash
python test_compensation_direct.py failure
```

This will:
- Book flight and hotel
- Payment fails
- Trigger compensation (cancel bookings)
- Send **real failure notification email** to `mkanoor@gmail.com` with:
  - Flight booking ID that was cancelled
  - Hotel booking ID that was cancelled
  - Refund/cancellation status

## What Emails Will Be Sent

### Success Email:
```
Subject: ✅ Travel Booking Confirmed - Paris
To: mkanoor@gmail.com

BOOKING SUMMARY:
• Destination: Paris
• Total Paid: $1500

YOUR RESERVATIONS:
✈️  FLIGHT CONFIRMED
   Confirmation: FLIGHT-TEST-SUC
   Status: Booked and Ticketed

🏨 HOTEL CONFIRMED
   Confirmation: HOTEL-TEST-SUC
   Status: Reserved

💳 PAYMENT CONFIRMED
   Transaction ID: PAY-TEST-SUC
   Amount: $1500
   Status: Completed
```

### Failure/Compensation Email:
```
Subject: ❌ Travel Booking Failed - Reservations Cancelled
To: mkanoor@gmail.com

BOOKING DETAILS:
• Destination: Paris
• Total Amount: $1500

CANCELLED RESERVATIONS:
The following reservations were automatically cancelled at no charge to you:

✈️  Flight Booking: FLIGHT-TEST-FAI
   Status: CANCELLED - Full refund initiated

🏨 Hotel Booking: HOTEL-TEST-FAI
   Status: CANCELLED - No cancellation fees applied

NEXT STEPS:
Please update your payment information and try booking again.
All reservations have been fully reversed.
```

## No Installation? Workflow Still Works!

If you don't install the Google packages, the workflow will:
- ✅ Continue to work normally
- ✅ Execute all compensation logic
- ⚠️  Simulate email sending (log what would be sent)
- ✅ Complete successfully

The workflow gracefully degrades to simulation mode when Gmail isn't available.

## Troubleshooting

### Import Error After Installation

If you still get `ModuleNotFoundError: No module named 'google.auth'`:
- Make sure you're using the same Python environment
- Try: `which python` and `which pip` to verify
- Reinstall in the correct environment

### Token Expired

If you get authentication errors:
1. Delete `backend/token.json`
2. Run the workflow again
3. It will re-authenticate via OAuth browser flow

### Wrong Email Address

Update the context file:
```json
{
  "customer_email": "your-email@gmail.com",
  ...
}
```
