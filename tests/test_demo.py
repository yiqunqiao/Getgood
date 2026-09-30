import pytest
from fastapi.testclient import TestClient
import backend.app as module
from backend.grader import run_tests

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'DATA',tmp_path)
    with TestClient(module.app) as c:
        c.headers['X-GetGood-Token']=c.get('/api/session').json()['token']
        yield c

def example(client,task,kind='good'):
    return {'task_id':task,**client.get(f'/api/demo/{task}/{kind}').json()}

def test_three_act_story_and_regression(client):
    first='t1_refund'
    bad=client.post('/api/submit',json=example(client,first,'bad')).json()
    assert not bad['success'] and bad['judgement']['missed']
    client.post('/api/hint/'+first)
    client.post('/api/hint/'+first)
    guided=client.post('/api/submit',json=example(client,first)).json()
    assert guided['success'] and guided['hints_used']==2
    assert guided['level']=='Needs guidance'
    second=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert second['success'] and second['level']=='Independent'
    third=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert third['success'] and third['level']=='Verified across scenarios'
    bad=client.post('/api/submit',json=example(client,'t3_legit_refund','bad')).json()
    assert bad['reference']['status']=='failed' and not bad['success']
    assert bad['level']=='Independent'
    assert len(client.get('/api/progress').json()['history'])==5

def test_invalid_tests_are_not_evidence(client):
    payload=example(client,'t1_refund')
    for code in ['def invalid(', 'x = 1', 'def test_error(env):\n    raise ValueError("broken test")', 'import pytest\n@pytest.mark.skip\ndef test_skipped():\n    pass']:
        payload['tests']=code
        result=client.post('/api/submit',json=payload).json()
        assert result['reference']['status']=='error'
        assert not any(v['caught'] for v in result['variants'].values())

def test_boundary_and_false_positive(client):
    payload=example(client,'t3_legit_refund')
    payload['boundaries']['concurrent']='verified'
    result=client.post('/api/submit',json=payload).json()
    assert not result['success'] and result['boundaries']['concurrent']=='unsupported'
    payload=example(client,'t3_legit_refund')
    payload['judgements']=[{'type':'duplicate','line':7}]
    result=client.post('/api/submit',json=payload).json()
    assert not result['success'] and result['judgement']['false_positive']

def test_timeout():
    result=run_tests('t1_refund','reference','def test_loop():\n    while True:\n        pass',timeout=.5)
    assert result['status']=='timeout'

def test_public_api_and_token(client):
    tasks=client.get('/api/tasks').json()
    assert len(tasks)==3 and 'known_risks' not in tasks[0]
    assert 'variants' not in tasks[0]['boundaries'][0]
    assert client.post('/api/hint/t2_coupon').status_code==400
    assert client.get('/').status_code==200
    assert client.get('/static/style.css').status_code==200
    client.headers.pop('X-GetGood-Token')
    assert client.post('/api/reset').status_code==403


def test_comparison_preserves_growth_and_promotion(client):
    client.post('/api/hint/t1_refund')
    client.post('/api/submit',json=example(client,'t1_refund'))
    client.post('/api/submit',json=example(client,'t2_coupon'))
    before=client.get('/api/progress').json()
    raw=(module.DATA/'progress.json').read_bytes()
    for kind in ['bad','good']:
        result=client.post('/api/compare',json=example(client,'t3_legit_refund',kind)).json()
        assert result['recorded'] is False
        assert result['success']==(kind=='good')
        assert result['level']==result['previous_level']=='Independent'
        assert (module.DATA/'progress.json').read_bytes()==raw
        assert client.get('/api/progress').json()==before
    result=client.post('/api/submit',json=example(client,'t3_legit_refund')).json()
    assert result['previous_level']=='Independent'
    assert result['level']=='Verified across scenarios'
    assert len(client.get('/api/progress').json()['history'])==3


def test_risk_locations_and_boundary_history(client):
    for task in ['t1_refund','t2_coupon']:
        payload=example(client,task)
        payload['judgements'][0]['line']=1
        payload['boundaries']['concurrent']='need_mentor'
        result=client.post('/api/submit',json=payload).json()
        assert result['success'] and result['judgement']['correct']
        entry=client.get('/api/progress').json()['history'][-1]
        assert entry['boundary_claims']['concurrent']=='need_mentor'
        assert entry['result']['boundaries']['concurrent']=='need_mentor'
        assert entry['previous_level'] and entry['level_reason']
        payload['judgements'][0]['line']=2
        wrong=client.post('/api/compare',json=payload).json()
        assert wrong['judgement']['missed'] and wrong['judgement']['false_positive']
        payload['judgements'][0]={'line':1,'type':'precision'}
        assert not client.post('/api/compare',json=payload).json()['judgement']['correct']
    assert all('risk_locations' not in t for t in client.get('/api/tasks').json())


def test_guided_success_without_hints_does_not_promote(client):
    result=client.post('/api/submit',json=example(client,'t1_refund')).json()
    assert result['success']
    assert result['hints_used']==0
    assert result['previous_level']==result['level']=='Needs guidance'
    assert client.get('/api/progress').json()['history'][0]['independent'] is False
    transfer=client.post('/api/submit',json=example(client,'t2_coupon')).json()
    assert transfer['success'] and transfer['level']=='Independent'


def test_consequence_is_checked_without_revealing_answer(client):
    payload=example(client,'t1_refund')
    payload['consequence']='unrelated'
    result=client.post('/api/compare',json=payload).json()
    assert not result['success']
    assert result['judgement']['correct']
    assert result['consequence']=={'correct':False,'selected':'unrelated','expected':None}
    assert 'expected_consequence' not in client.get('/api/tasks').json()[0]
    assert client.get('/api/progress').json()['history']==[]


def test_corrupt_local_progress_uses_empty_state(client):
    module.DATA.mkdir(exist_ok=True)
    (module.DATA/'progress.json').write_text('{broken')
    assert client.get('/api/progress').json()=={'level':'Needs guidance','history':[],'hints':{}}
