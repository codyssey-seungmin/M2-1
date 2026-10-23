"""위기 표현이 일반 분석·추천·생성보다 먼저 안전 안내로 분기되는지 확인한다."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from safety import has_crisis_signal
from server import app


assert has_crisis_signal('요즘 죽고 싶다는 생각이 들어요.')
assert has_crisis_signal('내 삶을 끝내고 싶어.')
assert has_crisis_signal('자해를 하고 싶어요.')
assert has_crisis_signal('자살을 생각하고 있어요.')
assert has_crisis_signal('다른 사람을 해치고 싶어요.')
assert not has_crisis_signal('시험이 너무 힘들어 죽겠다는 농담을 했어요.')
assert not has_crisis_signal('자살 예방 교육 자료를 읽었어요.')

client = TestClient(app)
with patch('server.analyze') as analyze, \
     patch('server.recommend_healing') as recommend, \
     patch('server.answer_with_grounding') as generate:
    response = client.post('/api/agent/coach', json={
        'text': '더는 살고 싶지 않아요.',
        'self_reported_stress': 5,
        'context': 'diary',
    })

assert response.status_code == 200
body = response.json()
assert body['response_type'] == 'safety'
assert body['generation'] == 'not_run'
assert body['analysis'] is None and body['recommendation'] is None
assert body['tool_trace'] == [{'tool': 'crisis_safety', 'status': 'completed'}]
assert {contact['number'] for contact in body['safety']['contacts']} == {'109', '112', '119'}
assert body['safety']['stored_separately'] is False
assert body['safety']['sent_to_external_ai'] is False
analyze.assert_not_called()
recommend.assert_not_called()
generate.assert_not_called()

print('crisis signal routes to verified support before analysis, retrieval, or generation: OK')
