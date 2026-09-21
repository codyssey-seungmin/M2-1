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
