"""Display-only reporting scope for the NEXUM Latino series."""

SEPARATED_SUBEVENTS = (35, 38)


def is_latino(event):
    return event.organizer.slug == 'nexum-productions' and event.slug == 'tanciaren'


def scoped_positions(event, queryset):
    return queryset.filter(subevent__isnull=False).exclude(subevent_id__in=SEPARATED_SUBEVENTS)
