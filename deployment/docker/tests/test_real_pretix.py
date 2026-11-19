from decimal import Decimal
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import pytest
from django.test import RequestFactory
from django.contrib.sessions.backends.db import SessionStore
from django_scopes import scope, scopes_disabled
from pretix.base.models import Organizer, Event, User, Team, Order, OrderPosition
from pretix.base.templatetags.money import money_filter
from pretix.control.signals import event_dashboard_top, organizer_ticket_sales_adjustment
from pretix_nexum_summary.signals import combined_dashboard, historical_sales, totals

@pytest.fixture
def data(db):
    with scopes_disabled():
        org = Organizer.objects.create(name='Nexum',slug='nexum-productions')
        dt=datetime(2027,1,9,18,tzinfo=timezone.utc)
        old=Event.objects.create(organizer=org,name='Latino',slug='tanciaren',date_from=dt,has_subevents=True,currency='EUR')
        new=Event.objects.create(organizer=org,name='New Year',slug='novorocna-tanciaren',date_from=dt,currency='EUR',plugins='pretix_nexum_summary')
        sub=old.subevents.create(id=35,name='New Year',date_from=dt,active=True)
        olditem=old.items.create(id=141,name='Old ticket',default_price=55,admission=True)
        newitem=new.items.create(name='New ticket',default_price=55,admission=True)
        user=User.objects.create_user('integration@example.com','dummy')
        team=Team.objects.create(organizer=org,name='Both',can_view_orders=True)
        team.members.add(user);team.limit_events.add(old,new)
        def add(event,item,n,subevent=None,status='p',testmode=False,canceled=False):
            o=Order.objects.create(sales_channel=org.sales_channels.get(identifier='web'),event=event,status=status,total=55*n,locale='en',email='synthetic@example.com',expires=dt,testmode=testmode)
            for i in range(n):
                OrderPosition.objects.create(order=o,item=item,subevent=subevent,price=55,positionid=i+1,canceled=canceled)
            return o
        add(old,olditem,4,sub);add(new,newitem,1)
        req=RequestFactory().get('/');req.user=user;req.session=SessionStore();req.event=new;req.organizer=org
        yield org,old,new,team,req,add,sub,olditem,newitem

def test_real_orm_signal_template_and_permissions(data):
    org,old,new,team,req,add,sub,oi,ni=data
    with scope(organizer=org):
        assert totals(old,True)=={'count':4,'amount':Decimal('220')}
        html=combined_dashboard(new,req)
        assert '275' in html and '5' in html
        responses=event_dashboard_top.send(new,request=req)
        assert any(receiver==combined_dashboard and '275' in result for receiver,result in responses)
        team.limit_events.remove(old);req.user=User.objects.get(pk=req.user.pk)
        assert combined_dashboard(new,req)==''

def test_filter_and_cancel_real_models(data):
    org,old,new,team,req,add,sub,oi,ni=data
    with scope(organizer=org):
        add(old,oi,1,sub,status='n');add(old,oi,1,sub,testmode=True);add(old,oi,1,sub,canceled=True)
        other=old.subevents.create(name='Other date',date_from=sub.date_from,active=True)
        add(old,oi,1,other)
        assert totals(old,True)['count']==4
        Order.objects.filter(event=old,status='p',testmode=False).update(status='c')
        assert totals(old,True)['count']==0
        assert totals(new)['count']==1

def test_plugin_disabled_signal(data):
    org,old,new,*_=data
    with scope(organizer=org):
        new.plugins='';new.save()
        from django.test import RequestFactory
        assert all(receiver!=combined_dashboard for receiver,_ in event_dashboard_top.send(new,request=RequestFactory().get('/')))
        assert historical_sales not in dict(organizer_ticket_sales_adjustment.send(new, request=RequestFactory().get('/')))


def test_organizer_adjustment_uses_only_legacy_new_year_admissions(data):
    org, old, new, team, req, add, sub, old_item, new_item = data
    with scope(organizer=org):
        add(old, old_item, 1, sub, status=Order.STATUS_PENDING)
        add(old, old_item, 1, sub, testmode=True)
        add(old, old_item, 1, sub, canceled=True)
        other_item = old.items.create(name='Other ticket', default_price=55, admission=True)
        add(old, other_item, 1, sub)
        other_date = old.subevents.create(name='Other date', date_from=sub.date_from, active=True)
        add(old, old_item, 1, other_date)

        assert dict(organizer_ticket_sales_adjustment.send(new, request=req))[historical_sales] == {
            'count': 4, 'amount': Decimal('220'), 'reserved_capacity': 4,
        }
        OrderPosition.objects.filter(order__event=old, subevent=sub, item=old_item).update(canceled=True)
        assert dict(organizer_ticket_sales_adjustment.send(new, request=req))[historical_sales] == {
            'count': 0, 'amount': Decimal('0.00'), 'reserved_capacity': 4,
        }


def test_organizer_adjustment_rejects_unreadable_or_mismatched_source(data):
    org, old, new, team, req, *_ = data
    with scope(organizer=org):
        new.currency = 'USD'
        assert dict(organizer_ticket_sales_adjustment.send(new, request=req))[historical_sales] is None

        new.currency = 'EUR'
        team.limit_events.remove(old)
        req.user = User.objects.get(pk=req.user.pk)
        assert dict(organizer_ticket_sales_adjustment.send(new, request=req))[historical_sales] is None

def test_dashboard_http_route(data, client):
    org,old,new,team,req,*_=data
    client.force_login(req.user)
    response=client.get('/control/event/nexum-productions/novorocna-tanciaren/')
    assert response.status_code==200
    assert 'Novoročná tančiareň – spoločný predaj' in response.content.decode()
    assert 'Zaplatené platné vstupenky spolu: 5' in response.content.decode()
    assert '?subevent=35' in response.content.decode()


def test_organizer_totals_include_new_year_history(data, client):
    org, old, new, team, req, _, _, _, ticket = data
    with scope(organizer=org):
        new.quotas.create(name='Standalone capacity', size=146).items.add(ticket)
    client.force_login(req.user)

    def sales_cells():
        response = client.get('/control/organizer/nexum-productions/')
        assert response.status_code == 200
        doc = BeautifulSoup(response.content.decode(response.charset), 'lxml')
        rows = doc.select('tbody tr')
        # The historical Latino occurrence must not appear separately from its standalone event.
        assert [row.select_one('a').get_text(strip=True) for row in rows] == ['New Year']
        row = rows[0]
        assert row.select_one('.ticket-sales .event-start').get_text(strip=True) == new.get_short_date_from_display()
        return (
            row.select_one('.ticket-sales strong').get_text(strip=True),
            row.select_one('.ticket-sales-value').get_text(strip=True),
        )

    assert sales_cells() == ('5 / 150', money_filter(275, 'EUR'))
    with scope(organizer=org):
        team.limit_events.remove(old)
    assert sales_cells() == ('1 / 146', money_filter(55, 'EUR'))

def test_dashboard_http_permission_no_leak(data,client):
    org,old,new,team,req,*_=data
    with scopes_disabled():
        team.limit_events.remove(old)
    client.force_login(req.user)
    response=client.get('/control/event/nexum-productions/novorocna-tanciaren/')
    assert response.status_code==200
    assert 'Zaplatené platné vstupenky spolu:' not in response.content.decode()

def test_dashboard_does_not_mutate_orders_or_qr(data,client):
    org,old,new,team,req,*_=data
    with scopes_disabled():
        before=list(Order.objects.order_by('pk').values())
        positions=list(OrderPosition.all.order_by('pk').values())
    client.force_login(req.user)
    response=client.get('/control/event/nexum-productions/novorocna-tanciaren/')
    assert response.status_code==200
    with scopes_disabled():
        assert before==list(Order.objects.order_by('pk').values())
        assert positions==list(OrderPosition.all.order_by('pk').values())
