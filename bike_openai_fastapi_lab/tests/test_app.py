import csv
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI, APITimeoutError, AuthenticationError, RateLimitError, APIConnectionError
import app
import generation
from facts import build_facts, DATA_PATH

client = TestClient(app.app)


def test_real_csv():
    facts = build_facts()
    assert (facts['raw_rows'], facts['excluded_non_operating_rows'], facts['included_rows']) == (8760, 295, 8465)
    assert (facts['period_start'], facts['period_end']) == ('2017-12-01', '2018-11-30')
    assert facts['peak_hours'] == [18]
    assert facts['hourly'][18] == {'hour': 18, 'rental_total': 548568, 'observations': 353, 'mean_rentals': 1554.02}
    with DATA_PATH.open(encoding='latin1') as f:
        rows = list(csv.DictReader(f))
    assert [int(r['Rented Bike Count']) for r in rows[:3]] == [254, 204, 173]


def test_template_no_network():
    with patch('generation.OpenAI', side_effect=AssertionError('network forbidden')):
        response = client.post('/articles', json={'mode': 'template'})
    assert response.status_code == 200
    body = response.json()
    assert body['ai_generated'] is False and body['model'] is None
    assert 'AI 미호출' in body['article'] and '548,568' in body['article']


@pytest.mark.parametrize('body', [{'mode': 'wrong'}, {'mode': 'template', 'api_key': 'not-a-key'}])
def test_request_validation(body):
    assert client.post('/articles', json=body).status_code == 422


def test_missing_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    r = client.post('/articles', json={'mode': 'openai'})
    assert r.status_code == 503 and 'OPENAI_API_KEY' in r.json()['detail']


def test_missing_csv():
    with patch('app.build_facts', side_effect=FileNotFoundError('private/path')):
        r = client.post('/articles', json={'mode': 'template'})
    assert r.status_code == 422 and 'private/path' not in r.text


@pytest.mark.parametrize('content', [
    'bad,headers\n1,2\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n01/12/2017,24,3,Yes\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n01/12/2017,1,-1,Yes\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n01/12/2017,1,3,Maybe\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n01/12/2017,1,3,Yes\n01/12/2017,1,3,Yes\n',
    'Date,Hour,Rented Bike Count,Functioning Day\n01/12/2017,1,3,No\n',
])
def test_bad_csv(tmp_path, content):
    p = tmp_path/'bad.csv'
    p.write_text(content)
    with pytest.raises(ValueError):
        build_facts(p)


def test_openai_sdk_mock_transport(monkeypatch):
    """실제 SDK 직렬화 + mock HTTP 응답. 외부 호출/실제 모델 생성 아님."""
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    captured = []
    def handler(request):
        import json
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id': 'resp_mock', 'object': 'response', 'created_at': 0,
            'status': 'completed', 'model': generation.MODEL,
            'output': [{'id': 'msg_mock', 'type': 'message', 'role': 'assistant', 'status': 'completed',
                        'content': [{'type': 'output_text', 'text': '[테스트 대역] 기사 초안', 'annotations': []}]}]
        })
    sdk = OpenAI(api_key='test-placeholder', http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with patch('generation.OpenAI', return_value=sdk) as factory:
        response = client.post('/articles', json={'mode': 'openai'})
    assert response.status_code == 200
    assert response.json()['article'] == '[테스트 대역] 기사 초안'
    assert captured[0]['store'] is False
    assert captured[0]['reasoning'] == {'effort': 'none'}
    assert 'temperature' not in captured[0]
    assert captured[0]['max_output_tokens'] == 700
    assert captured[0]['model'] == generation.MODEL
    assert factory.call_args.kwargs['max_retries'] == 0
    assert factory.call_args.kwargs['timeout'] == 30.0


@pytest.mark.parametrize('kind,status', [('auth', 502), ('rate', 429), ('timeout', 504), ('connection', 502)])
def test_api_errors_sanitized(monkeypatch, kind, status):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    request = httpx.Request('POST', 'https://api.openai.com/v1/responses')
    errors = {
        'auth': AuthenticationError('secret upstream detail', response=httpx.Response(401, request=request), body=None),
        'rate': RateLimitError('secret upstream detail', response=httpx.Response(429, request=request), body=None),
        'timeout': APITimeoutError(request=request),
        'connection': APIConnectionError(request=request),
    }
    with patch('generation.OpenAI') as factory:
        factory.return_value.__enter__.return_value.responses.create.side_effect = errors[kind]
        r = client.post('/articles', json={'mode': 'openai'})
    assert r.status_code == status
    assert 'secret' not in r.text and 'test-placeholder' not in r.text


@pytest.mark.parametrize('status,text', [('incomplete', 'partial'), ('completed', ''), ('completed', 'x'*4001)])
def test_invalid_model_output(monkeypatch, status, text):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-placeholder')
    with patch('generation.OpenAI') as factory:
        factory.return_value.__enter__.return_value.responses.create.return_value = SimpleNamespace(status=status, output_text=text)
        assert client.post('/articles', json={'mode': 'openai'}).status_code == 502


def test_docs_and_home():
    assert client.get('/docs').status_code == 200
    assert client.get('/openapi.json').json()['paths']['/articles']['post']
    assert 'AI 미호출' in client.get('/').text
    assert client.get('/health').status_code == 200


def test_key_entry_stops_on_echo_fallback():
    import getpass
    import warnings
    from start_api import read_key
    def unsafe_prompt(*args, **kwargs):
        warnings.warn('echo fallback', getpass.GetPassWarning)
        raise AssertionError('must not proceed to echoed input')
    with patch('start_api.getpass.getpass', side_effect=unsafe_prompt):
        with pytest.raises(SystemExit, match='비표시 입력'):
            read_key()
