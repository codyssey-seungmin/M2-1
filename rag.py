"""별도 지식 말뭉치를 BM25로 검색하고 그 근거만 생성형 AI에 전달한다."""
from collections import Counter
import json
import math
from pathlib import Path
import re

from healing_knowledge import ACTIVITIES
import llm


KNOWLEDGE_PATH = Path(__file__).resolve().parent / 'knowledge' / 'healing_sources.json'
TOKEN_PATTERN = re.compile(r'[가-힣A-Za-z0-9·]+')
CALMING_KINDS = {'호흡', '감각활동', '자연의 소리'}


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _load_documents() -> list[dict]:
    with KNOWLEDGE_PATH.open(encoding='utf-8') as handle:
        documents = json.load(handle)
    required = {'id', 'activity_id', 'title', 'kind', 'minutes', 'emotions',
                'keywords', 'content', 'source_title', 'source_url'}
    if not documents or any(not required <= set(document) for document in documents):
        raise ValueError('RAG 지식 문서 형식이 올바르지 않습니다.')
    return documents


def _document_text(document: dict) -> str:
    return ' '.join([
        document['title'], document['kind'], document['content'],
        *document['emotions'], *document['keywords'],
    ])


def search_knowledge(emotion: str, stress: int, minutes: int = 20,
                     preferred_kind: str | None = None, top_k: int = 3) -> list[dict]:
    """입력 조건을 질의로 만들고 BM25 점수와 제한적인 개인화 가중치로 검색한다."""
    documents = [document for document in _load_documents()
                 if document['minutes'] <= minutes]
    if not documents:
        return []

    stress_terms = ('긴장 걱정 진정 짧은 활동' if stress >= 4 else '휴식 집중 활동')
    preference_terms = f'{preferred_kind} {preferred_kind}' if preferred_kind else ''
    query = f'{emotion} 스트레스 {stress_terms} {preference_terms}'.strip()
    query_tokens = _tokens(query)
    tokenized = [_tokens(_document_text(document)) for document in documents]
    average_length = sum(map(len, tokenized)) / len(tokenized)
    document_frequency = Counter(token for tokens in tokenized for token in set(tokens))
    k1, b = 1.5, 0.75
    ranked = []

    for document, tokens in zip(documents, tokenized):
        frequencies = Counter(tokens)
        score = 0.0
        for token in query_tokens:
            frequency = frequencies[token]
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(documents) - document_frequency[token] + 0.5)
                / (document_frequency[token] + 0.5))
            denominator = frequency + k1 * (
                1 - b + b * len(tokens) / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / denominator

        # 감정·높은 스트레스·동의한 선호는 검색 결과를 재정렬하는 명시적 가중치다.
        if emotion in document['emotions']:
            score += 1.5
        if stress >= 4 and document['kind'] in CALMING_KINDS:
            score += 0.8
        if preferred_kind and document['kind'] == preferred_kind:
            # 명시적으로 동의해 저장한 선호는 시간 조건을 만족할 때 첫 추천이 되게 한다.
            score += 8.0

        matched = sorted(set(query_tokens) & set(tokens))
        ranked.append((score, document, matched))

    ranked.sort(key=lambda item: (item[0], -item[1]['minutes'], item[1]['id']), reverse=True)
    results = []
    for score, document, matched in ranked[:top_k]:
        results.append({
            **document,
            'retrieval': {
                'method': 'bm25',
                'score': round(score, 4),
                'matched_terms': matched,
                'query': query,
                'preference_boosted': bool(
                    preferred_kind and document['kind'] == preferred_kind),
            },
        })
    return results


def retrieve_activities(emotion: str, stress: int, minutes: int,
                        preferred_kind: str | None = None) -> list[dict]:
    """검색 순서대로 기존 UI 활동 카드 전체를 반환한다."""
    documents = search_knowledge(
        emotion, stress, minutes, preferred_kind, top_k=len(ACTIVITIES))
    activity_by_id = {activity['id']: activity for activity in ACTIVITIES}
    cards = []
    for document in documents:
        activity = activity_by_id.get(document['activity_id'])
        if not activity:
            continue
        card = {key: value for key, value in activity.items() if key != 'emotions'}
        card['retrieval'] = document['retrieval']
        cards.append(card)
    return cards


def retrieve_grounding(emotion: str, stress: int, minutes: int = 20,
                       preferred_kind: str | None = None) -> list[dict]:
    documents = search_knowledge(emotion, stress, minutes, preferred_kind, top_k=3)
    return [{
        'id': document['id'],
        'activity_id': document['activity_id'],
        'title': document['title'],
        'kind': document['kind'],
        'description': document['content'],
        'source_title': document['source_title'],
        'source_url': document['source_url'],
        'retrieval': document['retrieval'],
    } for document in documents]


def _fallback_answer(sources: list[dict]) -> dict:
    first = sources[0]
    return {
        'answer': f"지금은 ‘{first['title']}’부터 천천히 시도해 볼 수 있어요. {first['description']}",
        'generation': 'deterministic_fallback',
    }


def answer_with_grounding(emotion: str, stress: int, minutes: int = 20,
                          preferred_kind: str | None = None) -> dict:
    sources = retrieve_grounding(emotion, stress, minutes, preferred_kind)
    if not sources:
        return {
            'answer': '지금 바로 고를 수 있는 출처 있는 활동을 찾지 못했어요.',
            'sources': [], 'generation': 'no_source',
            'llm_enabled': llm.is_enabled(),
        }

    generated = llm.generate_coach_message(
        emotion, stress, sources, preferred_kind=preferred_kind)
    if generated and not generated.get('blocked'):
        result = generated
        fallback_reason = None
    else:
        result = _fallback_answer(sources)
        fallback_reason = ('safety_filter' if generated and generated.get('blocked')
                           else ('not_configured' if not llm.is_enabled() else 'call_failed'))

    return {
        **result,
        'sources': sources[:3],
        'grounding_policy': 'answer only from retrieved source cards',
        'llm_enabled': llm.is_enabled(),
        'fallback_reason': fallback_reason,
        'sends_diary_text': False,
        'personalization': {
            'applied': bool(preferred_kind),
            'preferred_kind': preferred_kind,
        },
    }
