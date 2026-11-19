import pytest
from decimal import Decimal
from django_scopes import scopes_disabled
from pretix.base.models import Order, OrderPosition
from pretix.control.views.dashboards import base_widgets
from test_real_pretix import data

@pytest.fixture
def latino(data):
    org,old,new,team,req,add,sub,oi,ni=data
    with scopes_disabled():
        team.can_change_event_settings=True;team.save()
        dt=sub.date_from
        lat=old.subevents.create(id=36,name='Latino December',date_from=dt,active=True)
        christmas=old.subevents.create(id=38,name='Christmas',date_from=dt,active=True)
        add(old,oi,3,lat);add(old,oi,2,christmas)
        add(old,oi,1,lat,status='n')
        add(old,oi,1,lat,testmode=True)
        add(old,oi,1,lat,canceled=True)
        # A mixed order must not contribute its excluded position or whole total.
        mixed=add(old,oi,1,lat)
        OrderPosition.objects.create(order=mixed,item=oi,subevent=sub,price=999,positionid=2)
        mixed.total=1054;mixed.save()
        yield data,lat,christmas

def test_latino_cards_exclude_separated_and_invalid(latino):
    data,lat,xmas=latino;org,old,new,team,req,*_=data
    with scopes_disabled():
        cards={w.get('lazy'):w for w in base_widgets(old)}
        assert '>5<' in cards['attendees-ordered']['content']
        assert '>4<' in cards['attendees-paid']['content']
        assert '220.00' in cards['total-revenue']['content']
        assert 'Hodnota zaplatených položiek Latino' in cards['total-revenue']['content']
        assert len(base_widgets(old,lazy=True))==4
        assert all(w['content'] is None for w in base_widgets(old,lazy=True))

def test_explicit_historical_term_keeps_original_counts(latino):
    data,lat,xmas=latino;org,old,new,team,req,add,sub,*_=data
    with scopes_disabled():
        cards={w.get('lazy'):w for w in base_widgets(old,subevent=sub)}
        assert '>5<' in cards['attendees-paid']['content']
        assert '1,219.00' in cards['total-revenue']['content']
        assert 'Hodnota zaplatených' not in cards['total-revenue']['content']

def test_default_dates_history_refresh_and_dashboard(latino,client):
    data,lat,xmas=latino;org,old,new,team,req,*_=data
    client.force_login(req.user)
    url='/control/event/nexum-productions/tanciaren/subevents/'
    for _ in range(2):
        r=client.get(url);assert r.status_code==200
        assert {s.pk for s in r.context['subevents']}=={36}
    r=client.get(url+'?nexum_history=1');assert r.status_code==200
    assert {s.pk for s in r.context['subevents']}=={35,36,38}
    assert b'name="nexum_history" value="1"' in r.content
    r=client.get(url+'?subevent=35');assert r.status_code==200
    assert {s.pk for s in r.context['subevents']}=={35}
    assert not r.context['nexum_history'] and r.context['nexum_selected']
    assert b'name="nexum_history" value="1"' not in r.content
    r=client.get('/control/event/nexum-productions/tanciaren/');assert r.status_code==200
    assert b'nexum-latino-scope' in r.content
    r=client.get('/control/event/nexum-productions/novorocna-tanciaren/');assert r.status_code==200
    assert 'Novoročná tančiareň – spoločný predaj' in r.content.decode()
    assert b'nexum-latino-scope' not in r.content

def test_no_orders_positions_or_qr_changed(latino,client):
    data,*_=latino;req=data[4]
    with scopes_disabled():
        before=list(Order.objects.order_by('pk').values());positions=list(OrderPosition.all.order_by('pk').values())
    client.force_login(req.user)
    for url in ['/control/event/nexum-productions/tanciaren/','/control/event/nexum-productions/tanciaren/subevents/','/control/event/nexum-productions/tanciaren/subevents/?nexum_history=1','/control/event/nexum-productions/novorocna-tanciaren/']:
        assert client.get(url).status_code==200
    with scopes_disabled():
        assert before==list(Order.objects.order_by('pk').values())
        assert positions==list(OrderPosition.all.order_by('pk').values())

def test_other_organizer_is_not_filtered(latino):
    data,*_=latino;org,old,*_=data
    with scopes_disabled():
        org.slug='unrelated';org.save();old.organizer=org
        cards={w.get('lazy'):w for w in base_widgets(old)}
        assert 'Hodnota zaplatených' not in cards['total-revenue']['content']

def test_bulk_all_matches_visible_scope(latino):
    from django.test import RequestFactory
    from pretix.control.views.subevents import SubEventQueryMixin
    data,*_=latino;old=data[1]
    with scopes_disabled():
        for payload,expected in [({'__ALL':'on'},{36}),({'__ALL':'on','subevent':['36']},{36}),({'__ALL':'on','nexum_history':'1'},{35,36,38}),({'subevent':['35']},{35})]:
            v=SubEventQueryMixin();v.request=RequestFactory().post('/',payload);v.request.event=old
            assert set(v.get_queryset().values_list('pk',flat=True))==expected
