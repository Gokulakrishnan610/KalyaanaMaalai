"""Every email we send. One entry per use case: the subject, the file, and sample values for the preview page.

Each file in mailer/templates/mailer/ only holds the message itself; the shared look (header, footer) is in base.html.
"""
SAMPLE = {"name": "Priya", "couple": "Priya & Rahul", "wedding": "Priya & Rahul wedding", "date": "14 Mar 2027",
          "link": "http://localhost:5174/set-password?token=sample", "amount": "1,50,000", "title": "Booking deposit",
          "password": "Temp-Pass-123", "otp": "482913", "vendor": "Royal Caterers", "category": "Catering", "reply_by": "20 Nov 2026",
          "due_date": "10 Nov 2026", "receipt": "RCPT-0042", "planner": "Priya Planner", "email": "priya@example.com"}

TEMPLATES = {
    "enquiry_received": ("We have your request, {name}", "A couple's request arrives (website sign-up)."),
    "client_welcome": ("Welcome to Shaandaar Events: set up your account", "An enquiry becomes a client; sends the login."),
    "password_reset": ("Reset your password", "Someone asked to reset a customer or vendor password."),
    "agreement_ready": ("Your service agreement is ready to sign", "The agreement is sent for signing."),
    "agreement_otp": ("Your signing code is {otp}", "A one-time code, before the client signs."),
    "agreement_signed": ("Agreement signed: your copy", "Both sides get a copy once it is signed."),
    "invoice_issued": ("Payment due: {title}, Rs {amount}", "A new invoice for the client."),
    "payment_reminder": ("Reminder: {title} is due", "An invoice is overdue."),
    "payment_receipt": ("Payment received: Rs {amount}", "The client paid (online, by link or recorded by us)."),
    "vendor_invite": ("Your Shaandaar Events vendor account", "A vendor is invited to the vendor portal."),
    "vendor_quotation_request": ("New quotation request: {category}", "A vendor is asked for a price."),
    "vendor_booked": ("You are booked: {wedding}", "A vendor's quotation was selected."),
    "vendor_payment_sent": ("Payment sent: Rs {amount}", "We paid the vendor."),
}
