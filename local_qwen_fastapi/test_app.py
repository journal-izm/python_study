import unittest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from app import app

class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
    def test_health(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
    def test_missing_facts(self):
        self.assertEqual(self.client.post('/articles', json={'topic':'날씨','source':'출처'}).status_code, 422)
    def test_generation_mock(self):
        response = httpx.Response(200, json={'message':{'content':'검사 전용 응답'}, 'eval_count':100,'eval_duration':2_000_000_000}, request=httpx.Request('POST','http://127.0.0.1:11434/api/chat'))
        with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=response)) as mocked:
            result = self.client.post('/articles', json={'topic':'테스트','source':'테스트용','facts':'외부 자료가 아닌 연결 검사입니다.'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['status'], 'DRAFT')
        self.assertEqual(result.json()['output_tokens_per_second'], 50)
        self.assertNotIn('think', mocked.call_args.kwargs['json'])
    def test_ollama_disconnected(self):
        with patch('httpx.AsyncClient.post', new=AsyncMock(side_effect=httpx.ConnectError('offline'))):
            result = self.client.post('/articles', json={'topic':'테스트','source':'테스트용','facts':'검사'})
        self.assertEqual(result.status_code, 503)

if __name__ == '__main__':
    unittest.main()
