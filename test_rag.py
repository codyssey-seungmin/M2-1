"""Verify retrieval grounding, source preservation, and non-medical fallback wording."""
from unittest.mock import patch
from fastapi.testclient import TestClient

from server import app


client = TestClient(app)
payload = {'emotion': '불안', 'stress': 4, 'minutes': 20}
search = client.post('/api/rag/search', json=payload)
assert search.status_code == 200
sources = search.json()['sources']
assert sources and all(item['source_url'].startswith('https://') for item in sources)
assert all(item['retrieval']['method'] == 'bm25' for item in sources)
assert all(item['retrieval']['matched_terms'] for item in sources)

# 질의가 바뀌면 검색 결과도 실제로 달라져야 한다.
sad_sources = client.post('/api/rag/search', json={
    'emotion': '슬픔', 'stress': 2, 'minutes': 20}).json()['sources']
assert [item['id'] for item in sources] != [item['id'] for item in sad_sources]
with patch.dict('os.environ', {'CODYSSEY_API_KEY': ''}):
    answer = client.post('/api/rag/answer', json=payload)
body = answer.json()
assert answer.status_code == 200
assert body['generation'] == 'deterministic_fallback'
assert body['fallback_reason'] == 'not_configured'
assert body['llm_enabled'] is False
assert body['sources'] and body['sources'][0]['title'] in body['answer']
assert '진단' not in body['answer']
print('RAG retrieval, source grounding, and transparent fallback: OK')
