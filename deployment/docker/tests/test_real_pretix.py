from decimal import Decimal
from datetime import datetime, timezone
import pytest
from django.test import RequestFactory
from django.contrib.sessions.backends.db import SessionStore
from django_scopes import scope, scopes_disabled
from pretix.base.models import Organizer, Event, User, Team, Order, OrderPosition
from pretix.control.signals import event_dashboard_top
from pretix_nexum_summary.signals import combined_dashboard, totals

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

def test_dashboard_http_route(data, client):
    org,old,new,team,req,*_=data
    client.force_login(req.user)
    response=client.get('/control/event/nexum-productions/novorocna-tanciaren/')
    assert response.status_code==200
    assert 'Novoročná tančiareň – spoločný predaj' in response.content.decode()
    assert 'Zaplatené platné vstupenky spolu: 5' in response.content.decode()
    assert '?subevent=35' in response.content.decode()

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
