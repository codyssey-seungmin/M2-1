"""명시적인 위기 표현을 일반 코치 흐름보다 먼저 처리한다.

진단이나 위험도 판정을 시도하지 않는다. 오탐을 줄이기 위해 직접적인 자기 위해
표현만 탐지하며, 탐지된 원문은 별도로 저장하거나 외부 AI에 전달하지 않는다.
"""
import re


CRISIS_PATTERNS = (
    re.compile(r'죽고\s*싶'),
    re.compile(r'살고\s*싶지\s*않'),
    re.compile(r'자살\s*(?:하고|할|을|이)'),
    re.compile(r'자살(?:을)?\s*(?:생각|고민)'),
    re.compile(r'자해\s*(?:하고|할|를|가)'),
    re.compile(r'(?:내\s*)?목숨(?:을)?\s*끊'),
    re.compile(r'(?:삶|인생)(?:을)?\s*끝내'),
    re.compile(r'(?:나|내\s*몸)(?:를|을)?\s*해치'),
    re.compile(r'극단적\s*선택(?:을)?\s*(?:하고|할)'),
    re.compile(r'극단적\s*선택(?:을)?\s*(?:생각|고민)'),
    re.compile(r'(?:다른\s*사람|누군가|저\s*사람|그\s*사람).{0,8}(?:죽이고\s*싶|해치고\s*싶)'),
)


def has_crisis_signal(text: str) -> bool:
    normalized = re.sub(r'[\u200b-\u200d\ufeff]', '', text.lower())
    return any(pattern.search(normalized) for pattern in CRISIS_PATTERNS)


def crisis_support() -> dict:
    return {
        'triggered': True,
        'message': ('지금 이 순간 혼자 버티지 않아도 돼요. 자살예방상담전화 109는 '
                    '24시간 연결되며, 당장 자신이나 다른 사람을 해칠 위험이 있으면 '
                    '주변 사람에게 알리고 112 또는 119에 연락해 주세요.'),
        'contacts': [
            {'label': '자살예방상담전화', 'number': '109', 'availability': '24시간'},
            {'label': '경찰 긴급신고', 'number': '112', 'availability': '긴급 상황'},
            {'label': '소방·구급', 'number': '119', 'availability': '긴급 상황'},
        ],
        'source_title': '보건복지부 자살예방상담전화 109 안내',
        'source_url': ('https://www.mohw.go.kr/board.es?act=view&bid=0027&'
                       'list_no=1479607&mid=a10503010300'),
        'stored_separately': False,
        'sent_to_external_ai': False,
    }
