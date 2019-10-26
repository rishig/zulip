from datetime import datetime
from decimal import Decimal
from functools import wraps
import logging
import math
import os
from typing import Any, Callable, Dict, Optional, TypeVar, Tuple, cast
import ujson

from django.conf import settings
from django.db import transaction
from django.db.models.query import QuerySet
from django.utils.translation import ugettext as _
from django.utils.timezone import now as timezone_now
from django.core.signing import Signer
import stripe

from zerver.lib.logging_util import log_to_file
from zerver.lib.timestamp import datetime_to_timestamp, timestamp_to_datetime
from zerver.lib.utils import generate_random_token
from zerver.models import Realm, UserProfile, RealmAuditLog, AbstractRealmAuditLog
from corporate.models import Customer, CustomerPlan, LicenseLedger, \
    get_current_plan
from zproject.settings import get_secret

STRIPE_PUBLISHABLE_KEY = get_secret('stripe_publishable_key')
stripe.api_key = get_secret('stripe_secret_key')

BILLING_LOG_PATH = os.path.join('/var/log/zulip'
                                if not settings.DEVELOPMENT
                                else settings.DEVELOPMENT_LOG_DIRECTORY,
                                'billing.log')
billing_logger = logging.getLogger('corporate.stripe')
log_to_file(billing_logger, BILLING_LOG_PATH)
log_to_file(logging.getLogger('stripe'), BILLING_LOG_PATH)

CallableT = TypeVar('CallableT', bound=Callable[..., Any])

MIN_INVOICED_LICENSES = 30
DEFAULT_INVOICE_DAYS_UNTIL_DUE = 30

class BillingOrg(object):
    def __init__(self, realm: Realm) -> None:
        self.realm = realm
        self.customer_args = {'realm': self.realm}

    def get_customer_if_exists(self) -> Optional[Customer]:
        return Customer.objects.filter(**self.customer_args).first()

    def get_customer(self) -> Customer:
        return Customer.objects.get(**self.customer_args)

    def get_audit_log_filter(self) -> QuerySet:
        return RealmAuditLog.objects.filter(realm=self.realm)

    def get_latest_seat_count(self) -> int:
        log_entry = self.get_audit_log_filter().filter(
            event_type__in=RealmAuditLog.SYNCED_BILLING_EVENTS).order_by('-id').first()
        if log_entry is None:
            raise AssertionError(
                '{}: get_latest_seat_count called with no log entries'.format(self))
        return get_seat_count(log_entry)

    def change_plan_type(self, value: int) -> None:
        from zerver.lib.actions import do_change_plan_type
        do_change_plan_type(self.realm, value)

    def stripe_description(self) -> str:
        return '{} ({})'.format(self.realm.string_id, self.realm.name)

    def stripe_metadata(self) -> Dict[str, Any]:
        return {'realm_id': self.realm.id, 'realm_str': self.realm.string_id}

    def __str__(self) -> str:
        return 'BillingOrg: {}'.format(self.realm)

# Note that BillingUser subclasses BillingOrg
class BillingUser(BillingOrg):
    def __init__(self, user: UserProfile) -> None:
        self.user = user
        super().__init__(realm=user.realm)

    def get_email(self) -> str:
        return self.user.email

    def has_billing_access(self) -> bool:
        return self.user.is_realm_admin or self.user.is_billing_admin

    def do_change_is_billing_admin(self, value: bool) -> None:
        self.user.is_billing_admin = value
        self.user.save(update_fields=['is_billing_admin'])

    def create_log_entry(self, event_type: int, event_time: datetime=timezone_now(),
                         extra_data: Optional[str]=None) -> None:
        RealmAuditLog.objects.create(
            realm=self.user.realm, acting_user=self.user, event_type=event_type,
            event_time=event_time, extra_data=extra_data)

def get_seat_count(log_entry: RealmAuditLog) -> int:
    assert log_entry.extra_data is not None  # for mypy
    role_count = ujson.loads(log_entry.extra_data)[str(RealmAuditLog.ROLE_COUNT)]
    humans = role_count[str(RealmAuditLog.ROLE_COUNT_HUMANS)]
    guests = humans[str(UserProfile.ROLE_GUEST)]
    non_guests = sum(humans.values()) - guests
    return max(non_guests, math.ceil(guests / 5))

def sign_string(string: str) -> Tuple[str, str]:
    salt = generate_random_token(64)
    signer = Signer(salt=salt)
    return signer.sign(string), salt

def unsign_string(signed_string: str, salt: str) -> str:
    signer = Signer(salt=salt)
    return signer.unsign(signed_string)

# Be extremely careful changing this function. Historical billing periods
# are not stored anywhere, and are just computed on the fly using this
# function. Any change you make here should return the same value (or be
# within a few seconds) for basically any value from when the billing system
# went online to within a year from now.
def add_months(dt: datetime, months: int) -> datetime:
    assert(months >= 0)
    # It's fine that the max day in Feb is 28 for leap years.
    MAX_DAY_FOR_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                         7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    year = dt.year
    month = dt.month + months
    while month > 12:
        year += 1
        month -= 12
    day = min(dt.day, MAX_DAY_FOR_MONTH[month])
    # datetimes don't support leap seconds, so don't need to worry about those
    return dt.replace(year=year, month=month, day=day)

def next_month(billing_cycle_anchor: datetime, dt: datetime) -> datetime:
    estimated_months = round((dt - billing_cycle_anchor).days * 12. / 365)
    for months in range(max(estimated_months - 1, 0), estimated_months + 2):
        proposed_next_month = add_months(billing_cycle_anchor, months)
        if 20 < (proposed_next_month - dt).days < 40:
            return proposed_next_month
    raise AssertionError('Something wrong in next_month calculation with '
                         'billing_cycle_anchor: %s, dt: %s' % (billing_cycle_anchor, dt))

def start_of_next_billing_cycle(plan: CustomerPlan, event_time: datetime) -> datetime:
    months_per_period = {
        CustomerPlan.ANNUAL: 12,
        CustomerPlan.MONTHLY: 1,
    }[plan.billing_schedule]
    periods = 1
    dt = plan.billing_cycle_anchor
    while dt <= event_time:
        dt = add_months(plan.billing_cycle_anchor, months_per_period * periods)
        periods += 1
    return dt

def next_invoice_date(plan: CustomerPlan) -> Optional[datetime]:
    if plan.status == CustomerPlan.ENDED:
        return None
    assert(plan.next_invoice_date is not None)  # for mypy
    months_per_period = {
        CustomerPlan.ANNUAL: 12,
        CustomerPlan.MONTHLY: 1,
    }[plan.billing_schedule]
    if plan.automanage_licenses:
        months_per_period = 1
    periods = 1
    dt = plan.billing_cycle_anchor
    while dt <= plan.next_invoice_date:
        dt = add_months(plan.billing_cycle_anchor, months_per_period * periods)
        periods += 1
    return dt

def renewal_amount(plan: CustomerPlan, event_time: datetime) -> int:  # nocoverage: TODO
    if plan.fixed_price is not None:
        return plan.fixed_price
    last_ledger_entry = make_end_of_cycle_updates_if_needed(plan, event_time)
    if last_ledger_entry is None:
        return 0
    if last_ledger_entry.licenses_at_next_renewal is None:
        return 0
    assert(plan.price_per_license is not None)  # for mypy
    return plan.price_per_license * last_ledger_entry.licenses_at_next_renewal

class BillingError(Exception):
    # error messages
    CONTACT_SUPPORT = _("Something went wrong. Please contact %s.") % (settings.ZULIP_ADMINISTRATOR,)
    TRY_RELOADING = _("Something went wrong. Please reload the page.")

    # description is used only for tests
    def __init__(self, description: str, message: str=CONTACT_SUPPORT) -> None:
        self.description = description
        self.message = message

class StripeCardError(BillingError):
    pass

class StripeConnectionError(BillingError):
    pass

def catch_stripe_errors(func: CallableT) -> CallableT:
    @wraps(func)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if settings.DEVELOPMENT and not settings.TEST_SUITE:  # nocoverage
            if STRIPE_PUBLISHABLE_KEY is None:
                raise BillingError('missing stripe config', "Missing Stripe config. "
                                   "See https://zulip.readthedocs.io/en/latest/subsystems/billing.html.")
        try:
            return func(*args, **kwargs)
        # See https://stripe.com/docs/api/python#error_handling, though
        # https://stripe.com/docs/api/ruby#error_handling suggests there are additional fields, and
        # https://stripe.com/docs/error-codes gives a more detailed set of error codes
        except stripe.error.StripeError as e:
            err = e.json_body.get('error', {})
            billing_logger.error("Stripe error: %s %s %s %s" % (
                e.http_status, err.get('type'), err.get('code'), err.get('param')))
            if isinstance(e, stripe.error.CardError):
                # TODO: Look into i18n for this
                raise StripeCardError('card error', err.get('message'))
            if isinstance(e, stripe.error.RateLimitError) or \
               isinstance(e, stripe.error.APIConnectionError):  # nocoverage TODO
                raise StripeConnectionError(
                    'stripe connection error',
                    _("Something went wrong. Please wait a few seconds and try again."))
            raise BillingError('other stripe error', BillingError.CONTACT_SUPPORT)
    return wrapped  # type: ignore # https://github.com/python/mypy/issues/1927

@catch_stripe_errors
def stripe_get_customer(stripe_customer_id: str) -> stripe.Customer:
    return stripe.Customer.retrieve(stripe_customer_id, expand=["default_source"])

@catch_stripe_errors
def do_create_stripe_customer(billing_user: BillingUser, stripe_token: Optional[str]=None) -> Customer:
    # We could do a better job of handling race conditions here, but if two
    # people from a realm try to upgrade at exactly the same time, the main
    # bad thing that will happen is that we will create an extra stripe
    # customer that we can delete or ignore.
    stripe_customer = stripe.Customer.create(
        description=billing_user.stripe_description(),
        email=billing_user.get_email(),
        metadata=billing_user.stripe_metadata(),
        source=stripe_token)
    event_time = timestamp_to_datetime(stripe_customer.created)
    with transaction.atomic():
        billing_user.create_log_entry(RealmAuditLog.STRIPE_CUSTOMER_CREATED, event_time=event_time)
        if stripe_token is not None:
            billing_user.create_log_entry(RealmAuditLog.STRIPE_CARD_CHANGED, event_time=event_time)
        customer, created = Customer.objects.update_or_create(
            defaults={'stripe_customer_id': stripe_customer.id},
            **billing_user.customer_args)
        billing_user.do_change_is_billing_admin(True)
    return customer

@catch_stripe_errors
def do_replace_payment_source(billing_user: BillingUser, stripe_token: str,
                              pay_invoices: bool=False) -> stripe.Customer:
    stripe_customer = stripe_get_customer(billing_user.get_customer().stripe_customer_id)
    stripe_customer.source = stripe_token
    # Deletes existing card: https://stripe.com/docs/api#update_customer-source
    updated_stripe_customer = stripe.Customer.save(stripe_customer)
    billing_user.create_log_entry(RealmAuditLog.STRIPE_CARD_CHANGED)
    if pay_invoices:
        for stripe_invoice in stripe.Invoice.list(
                billing='charge_automatically', customer=stripe_customer.id, status='open'):
            # The user will get either a receipt or a "failed payment" email, but the in-app
            # messaging could be clearer here (e.g. it could explictly tell the user that there
            # were payment(s) and that they succeeded or failed).
            # Worth fixing if we notice that a lot of cards end up failing at this step.
            stripe.Invoice.pay(stripe_invoice)
    return updated_stripe_customer

# event_time should roughly be timezone_now(). Not designed to handle
# event_times in the past or future
def make_end_of_cycle_updates_if_needed(plan: CustomerPlan,
                                        event_time: datetime) -> Optional[LicenseLedger]:
    last_ledger_entry = LicenseLedger.objects.filter(plan=plan).order_by('-id').first()
    last_renewal = LicenseLedger.objects.filter(plan=plan, is_renewal=True) \
                                        .order_by('-id').first().event_time
    next_billing_cycle = start_of_next_billing_cycle(plan, last_renewal)
    if next_billing_cycle <= event_time:
        if plan.status == CustomerPlan.ACTIVE:
            return LicenseLedger.objects.create(
                plan=plan, is_renewal=True, event_time=next_billing_cycle,
                licenses=last_ledger_entry.licenses_at_next_renewal,
                licenses_at_next_renewal=last_ledger_entry.licenses_at_next_renewal)
        if plan.status == CustomerPlan.DOWNGRADE_AT_END_OF_CYCLE:
            process_downgrade(plan)
        return None
    return last_ledger_entry

# Returns Customer instead of stripe_customer so that we don't make a Stripe
# API call if there's nothing to update
def update_or_create_stripe_customer(billing_user: BillingUser,
                                     stripe_token: Optional[str]=None) -> Customer:
    customer = billing_user.get_customer_if_exists()
    if customer is None or customer.stripe_customer_id is None:
        return do_create_stripe_customer(billing_user, stripe_token=stripe_token)
    if stripe_token is not None:
        do_replace_payment_source(billing_user, stripe_token)
    return customer

def compute_plan_parameters(
        automanage_licenses: bool, billing_schedule: int,
        discount: Optional[Decimal]) -> Tuple[datetime, datetime, datetime, int]:
    # Everything in Stripe is stored as timestamps with 1 second resolution,
    # so standardize on 1 second resolution.
    # TODO talk about leapseconds?
    billing_cycle_anchor = timezone_now().replace(microsecond=0)
    if billing_schedule == CustomerPlan.ANNUAL:
        # TODO use variables to account for Zulip Plus
        price_per_license = 8000
        period_end = add_months(billing_cycle_anchor, 12)
    elif billing_schedule == CustomerPlan.MONTHLY:
        price_per_license = 800
        period_end = add_months(billing_cycle_anchor, 1)
    else:
        raise AssertionError('Unknown billing_schedule: {}'.format(billing_schedule))
    if discount is not None:
        # There are no fractional cents in Stripe, so round down to nearest integer.
        price_per_license = int(float(price_per_license * (1 - discount / 100)) + .00001)
    next_invoice_date = period_end
    if automanage_licenses:
        next_invoice_date = add_months(billing_cycle_anchor, 1)
    return billing_cycle_anchor, next_invoice_date, period_end, price_per_license

# Only used for cloud signups
@catch_stripe_errors
def process_initial_upgrade(billing_user: BillingUser, licenses: int, automanage_licenses: bool,
                            billing_schedule: int, stripe_token: Optional[str]) -> None:
    customer = update_or_create_stripe_customer(billing_user, stripe_token=stripe_token)
    if get_current_plan(customer) is not None:
        # Unlikely race condition from two people upgrading (clicking "Make payment")
        # at exactly the same time. Doesn't fully resolve the race condition, but having
        # a check here reduces the likelihood.
        billing_logger.warning(
            "Customer {} trying to upgrade, but has an active subscription".format(customer))
        raise BillingError('subscribing with existing subscription', BillingError.TRY_RELOADING)

    billing_cycle_anchor, next_invoice_date, period_end, price_per_license = compute_plan_parameters(
        automanage_licenses, billing_schedule, customer.default_discount)
    # The main design constraint in this function is that if you upgrade with a credit card, and the
    # charge fails, everything should be rolled back as if nothing had happened. This is because we
    # expect frequent card failures on initial signup.
    # Hence, if we're going to charge a card, do it at the beginning, even if we later may have to
    # adjust the number of licenses.
    charge_automatically = stripe_token is not None
    if charge_automatically:
        stripe_charge = stripe.Charge.create(
            amount=price_per_license * licenses,
            currency='usd',
            customer=customer.stripe_customer_id,
            description="Upgrade to Zulip Standard, ${} x {}".format(price_per_license/100, licenses),
            receipt_email=billing_user.get_email(),
            statement_descriptor='Zulip Standard')
        # Not setting a period start and end, but maybe we should? Unclear what will make things
        # most similar to the renewal case from an accounting perspective.
        stripe.InvoiceItem.create(
            amount=price_per_license * licenses * -1,
            currency='usd',
            customer=customer.stripe_customer_id,
            description="Payment (Card ending in {})".format(cast(stripe.Card, stripe_charge.source).last4),
            discountable=False)

    # TODO: The correctness of this relies on user creation, deactivation, etc being
    # in a transaction.atomic() with the relevant RealmAuditLog entries
    with transaction.atomic():
        # billed_licenses can greater than licenses if users are added between the start of
        # this function (process_initial_upgrade) and now
        billed_licenses = max(billing_user.get_latest_seat_count(), licenses)
        plan_params = {
            'automanage_licenses': automanage_licenses,
            'charge_automatically': charge_automatically,
            'price_per_license': price_per_license,
            'discount': customer.default_discount,
            'billing_cycle_anchor': billing_cycle_anchor,
            'billing_schedule': billing_schedule,
            'tier': CustomerPlan.STANDARD}
        plan = CustomerPlan.objects.create(
            customer=customer,
            next_invoice_date=next_invoice_date,
            **plan_params)
        ledger_entry = LicenseLedger.objects.create(
            plan=plan,
            is_renewal=True,
            event_time=billing_cycle_anchor,
            licenses=billed_licenses,
            licenses_at_next_renewal=billed_licenses)
        plan.invoiced_through = ledger_entry
        plan.save(update_fields=['invoiced_through'])
        billing_user.create_log_entry(RealmAuditLog.CUSTOMER_PLAN_CREATED,
                                      event_time=billing_cycle_anchor,
                                      extra_data=ujson.dumps(plan_params))
    stripe.InvoiceItem.create(
        currency='usd',
        customer=customer.stripe_customer_id,
        description='Zulip Standard',
        discountable=False,
        period = {'start': datetime_to_timestamp(billing_cycle_anchor),
                  'end': datetime_to_timestamp(period_end)},
        quantity=billed_licenses,
        unit_amount=price_per_license)

    if charge_automatically:
        billing_method = 'charge_automatically'
        days_until_due = None
    else:
        billing_method = 'send_invoice'
        days_until_due = DEFAULT_INVOICE_DAYS_UNTIL_DUE
    stripe_invoice = stripe.Invoice.create(
        auto_advance=True,
        billing=billing_method,
        customer=customer.stripe_customer_id,
        days_until_due=days_until_due,
        statement_descriptor='Zulip Standard')
    stripe.Invoice.finalize_invoice(stripe_invoice)

    billing_user.change_plan_type(Realm.STANDARD)

def update_license_ledger_for_automanaged_plan(log_entry: AbstractRealmAuditLog,
                                               plan: CustomerPlan) -> None:
    last_ledger_entry = make_end_of_cycle_updates_if_needed(plan, log_entry.event_time)
    if last_ledger_entry is None:
        return
    licenses_at_next_renewal = get_seat_count(log_entry)
    licenses = max(licenses_at_next_renewal, last_ledger_entry.licenses)
    LicenseLedger.objects.create(
        plan=plan, event_time=log_entry.event_time, licenses=licenses,
        licenses_at_next_renewal=licenses_at_next_renewal)

def update_license_ledger_if_needed(log_entry: AbstractRealmAuditLog) -> None:
    customer = BillingOrg(log_entry.realm).get_customer_if_exists()
    if customer is None:
        return
    plan = get_current_plan(customer)
    if plan is None:
        return
    if not plan.automanage_licenses:
        return
    update_license_ledger_for_automanaged_plan(log_entry, plan)

def invoice_plan(plan: CustomerPlan, event_time: datetime) -> None:
    if plan.invoicing_status == CustomerPlan.STARTED:
        raise NotImplementedError('Plan with invoicing_status==STARTED needs manual resolution.')
    make_end_of_cycle_updates_if_needed(plan, event_time)
    assert(plan.invoiced_through is not None)
    licenses_base = plan.invoiced_through.licenses
    invoice_item_created = False
    for ledger_entry in LicenseLedger.objects.filter(plan=plan, id__gt=plan.invoiced_through.id,
                                                     event_time__lte=event_time).order_by('id'):
        price_args = {}  # type: Dict[str, int]
        if ledger_entry.is_renewal:
            if plan.fixed_price is not None:
                price_args = {'amount': plan.fixed_price}
            else:
                assert(plan.price_per_license is not None)  # needed for mypy
                price_args = {'unit_amount': plan.price_per_license,
                              'quantity': ledger_entry.licenses}
            description = "Zulip Standard - renewal"
        elif ledger_entry.licenses != licenses_base:
            assert(plan.price_per_license)
            last_renewal = LicenseLedger.objects.filter(
                plan=plan, is_renewal=True, event_time__lte=ledger_entry.event_time) \
                .order_by('-id').first().event_time
            period_end = start_of_next_billing_cycle(plan, ledger_entry.event_time)
            proration_fraction = (period_end - ledger_entry.event_time) / (period_end - last_renewal)
            price_args = {'unit_amount': int(plan.price_per_license * proration_fraction + .5),
                          'quantity': ledger_entry.licenses - licenses_base}
            description = "Additional license ({} - {})".format(
                ledger_entry.event_time.strftime('%b %-d, %Y'), period_end.strftime('%b %-d, %Y'))

        if price_args:
            plan.invoiced_through = ledger_entry
            plan.invoicing_status = CustomerPlan.STARTED
            plan.save(update_fields=['invoicing_status', 'invoiced_through'])
            idempotency_key = 'ledger_entry:{}'.format(ledger_entry.id)  # type: Optional[str]
            if settings.TEST_SUITE:
                idempotency_key = None
            stripe.InvoiceItem.create(
                currency='usd',
                customer=plan.customer.stripe_customer_id,
                description=description,
                discountable=False,
                period = {'start': datetime_to_timestamp(ledger_entry.event_time),
                          'end': datetime_to_timestamp(
                              start_of_next_billing_cycle(plan, ledger_entry.event_time))},
                idempotency_key=idempotency_key,
                **price_args)
            invoice_item_created = True
        plan.invoiced_through = ledger_entry
        plan.invoicing_status = CustomerPlan.DONE
        plan.save(update_fields=['invoicing_status', 'invoiced_through'])
        licenses_base = ledger_entry.licenses

    if invoice_item_created:
        if plan.charge_automatically:
            billing_method = 'charge_automatically'
            days_until_due = None
        else:
            billing_method = 'send_invoice'
            days_until_due = DEFAULT_INVOICE_DAYS_UNTIL_DUE
        stripe_invoice = stripe.Invoice.create(
            auto_advance=True,
            billing=billing_method,
            customer=plan.customer.stripe_customer_id,
            days_until_due=days_until_due,
            statement_descriptor='Zulip Standard')
        stripe.Invoice.finalize_invoice(stripe_invoice)

    plan.next_invoice_date = next_invoice_date(plan)
    plan.save(update_fields=['next_invoice_date'])

def invoice_plans_as_needed(event_time: datetime=timezone_now()) -> None:
    for plan in CustomerPlan.objects.filter(next_invoice_date__lte=event_time):
        invoice_plan(plan, event_time)

def attach_discount_to_realm(billing_org: BillingOrg, discount: Decimal) -> None:
    Customer.objects.update_or_create(defaults={'default_discount': discount},
                                      **billing_org.customer_args)

def get_discount_for_realm(billing_org: BillingOrg) -> Optional[Decimal]:
    customer = billing_org.get_customer_if_exists()
    if customer is not None:
        return customer.default_discount
    return None

def do_change_plan_status(plan: CustomerPlan, status: int) -> None:
    plan.status = status
    plan.save(update_fields=['status'])
    billing_logger.info('Change plan status: Customer.id: %s, CustomerPlan.id: %s, status: %s' % (
        plan.customer.id, plan.id, status))

def process_downgrade(plan: CustomerPlan) -> None:
    from zerver.lib.actions import do_change_plan_type
    do_change_plan_type(plan.customer.realm, Realm.LIMITED)
    plan.status = CustomerPlan.ENDED
    plan.save(update_fields=['status'])

def estimate_annual_recurring_revenue_by_realm() -> Dict[str, int]:  # nocoverage
    annual_revenue = {}
    for plan in CustomerPlan.objects.filter(
            status=CustomerPlan.ACTIVE).select_related('customer__realm'):
        # TODO: figure out what to do for plans that don't automatically
        # renew, but which probably will renew
        renewal_cents = renewal_amount(plan, timezone_now())
        if plan.billing_schedule == CustomerPlan.MONTHLY:
            renewal_cents *= 12
        # TODO: Decimal stuff
        annual_revenue[plan.customer.realm.string_id] = int(renewal_cents / 100)
    return annual_revenue
