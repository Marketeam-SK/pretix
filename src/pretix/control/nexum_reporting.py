#
# This file is part of pretix (Community Edition).
#
# Copyright (C) 2014-2020  Raphael Michel and contributors
# Copyright (C) 2020-today pretix GmbH and contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation in version 3 of the License.
#
# ADDITIONAL TERMS APPLY: Pursuant to Section 7 of the GNU Affero General Public License, additional terms are
# applicable granting you additional permissions and placing additional restrictions on your usage of this software.
# Please refer to the pretix LICENSE file to obtain the full terms applicable to this work. If you did not receive
# this file, see <https://pretix.eu/about/en/license>.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.
#

"""Display-only reporting rules for NEXUM."""

from collections import defaultdict

from django.db.models import Prefetch, Q

from pretix.base.models import Item, ItemVariation, Quota

SEPARATED_SUBEVENTS = (35, 38)


def is_latino(event):
    return event.organizer.slug == 'nexum-productions' and event.slug == 'tanciaren'


def scoped_positions(event, queryset):
    return queryset.filter(subevent__isnull=False).exclude(subevent_id__in=SEPARATED_SUBEVENTS)


def ticket_capacities(standalone_ids, date_ids):
    quotas = Quota.objects.filter(
        Q(event_id__in=standalone_ids, subevent__isnull=True) | Q(subevent_id__in=date_ids)
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=Item.objects.filter(admission=True, active=True, variations__isnull=True),
            to_attr='capacity_items',
        ),
        Prefetch(
            'variations',
            queryset=ItemVariation.objects.filter(active=True, item__active=True, item__admission=True),
            to_attr='capacity_variations',
        ),
    )
    coverage = defaultdict(list)
    for quota in quotas:
        admissions = {(item.pk, None) for item in quota.capacity_items}
        admissions.update((variation.item_id, variation.pk) for variation in quota.capacity_variations)
        if admissions:
            coverage[quota.event_id, quota.subevent_id].append((admissions, quota.size))

    capacities = {}
    for scope, pools in coverage.items():
        all_admissions = set().union(*(admissions for admissions, size in pools))
        # A shared quota defines total capacity. Summing product quotas can count the same seats twice.
        sizes = [size for admissions, size in pools if size is not None and admissions == all_admissions]
        if sizes:
            capacities[scope] = min(sizes)
    return capacities
