from django.contrib import admin

from payments.models import Expense, Invoice, Payment, VendorPaymentPlan

admin.site.register([Invoice, Expense, Payment, VendorPaymentPlan])
