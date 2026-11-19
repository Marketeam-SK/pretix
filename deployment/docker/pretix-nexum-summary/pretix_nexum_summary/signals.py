from decimal import Decimal

from django.db.models import Count, Sum
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse

from pretix.base.models import OrderPosition
from pretix.control.signals import (
    event_dashboard_top, organizer_ticket_sales_adjustment,
)

from .policy import (
    RESERVED_CAPACITY, SOURCE, SOURCE_ITEM, SOURCE_SUBEVENT, can_read_both,
    is_target, position_filters,
)


def totals(event, old=False):
    result = OrderPosition.objects.filter(**position_filters(event, old)).aggregate(
        count=Count('pk'), amount=Sum('price'))
    return dict(count=result['count'], amount=result['amount'] or Decimal('0.00'))


def legacy_source(target, request):
    if not is_target(target):
        return None
    source = target.organizer.events.filter(slug=SOURCE).first()
    if source is None or source.currency != target.currency:
        return None
    # Both permissions are required before even querying counts or values.
    if not can_read_both(request, target, source):
        return None
    if not source.subevents.filter(pk=SOURCE_SUBEVENT).exists():
        return None
    if not source.items.filter(pk=SOURCE_ITEM, admission=True).exists():
        return None
    return source


@receiver(organizer_ticket_sales_adjustment)
def historical_sales(sender, request, **kwargs):
    source = legacy_source(sender, request)
    if source is None:
        return None
    return {**totals(source, old=True), 'reserved_capacity': RESERVED_CAPACITY}


@receiver(event_dashboard_top)
def combined_dashboard(sender, request, **kwargs):
    source = legacy_source(sender, request)
    if source is None:
        return ''
    old, new = totals(source, True), totals(sender)

    def orders_url(event):
        return reverse('control:event.orders', kwargs={
            'organizer': sender.organizer.slug, 'event': event.slug})
    return render_to_string('pretix_nexum_summary/panel.html', {
        'old': old, 'new': new, 'count': old['count'] + new['count'],
        'amount': old['amount'] + new['amount'], 'currency': sender.currency,
        'old_url': orders_url(source) + '?subevent=' + str(SOURCE_SUBEVENT),
        'new_url': orders_url(sender),
    }, request=request)
