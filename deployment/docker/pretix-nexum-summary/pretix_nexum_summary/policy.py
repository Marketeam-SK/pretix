"""Narrow, explicit scope. No mutations, quota changes, or hard-coded +4."""
ORGANIZER = 'nexum-productions'
TARGET = 'novorocna-tanciaren'
SOURCE = 'tanciaren'
SOURCE_SUBEVENT = 35
SOURCE_ITEM = 141
# The standalone quota excludes these seats from the 150-seat venue capacity.
RESERVED_CAPACITY = 4


def is_target(event):
    return event.organizer.slug == ORGANIZER and event.slug == TARGET


def can_read_both(request, target, source):
    if not request.user.is_authenticated:
        return False
    return all(request.user.has_event_permission(
        target.organizer, event, 'can_view_orders', request=request
    ) for event in (target, source))


def position_filters(event, old=False):
    filters = dict(order__event=event, order__status='p',
                   order__testmode=False, canceled=False, item__admission=True)
    if old:
        filters.update(subevent_id=SOURCE_SUBEVENT, item_id=SOURCE_ITEM)
    return filters
