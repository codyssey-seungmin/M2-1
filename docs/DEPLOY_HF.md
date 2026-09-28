# Hugging Face Space 배포 가이드

> **현재 상태 (2026-09-28): 앱 평가 기능을 포함해 배포 완료 · 동작 확인.** https://yellowmug-mindily.hf.space
> 코드를 고친 뒤 다시 올릴 때는 저장소 루트의 `push_to_huggingface.cmd` 를 실행하면 됩니다.

기존 Render 설정은 유료 플랜(1c-2g + 2GB 디스크)을 전제로 해 막혀 있었습니다. **무료 등급으로 영구 HTTPS URL을 얻을 수 있는 Hugging Face Spaces**로 전환했습니다.

| 항목 | 값 |
|---|---|
| SDK | Docker |
| 포트 | 7860 |
| 하드웨어 | CPU basic (무료) |
| URL 형식 | `https://yellowmug-mindily.hf.space` |
| 모델 캐시 | 빌드 시 이미지에 동봉 → 첫 요청 지연 없음 |

---

## 1. Space 만들기 (최초 1회)

1. https://huggingface.co/new-space 접속
2. 설정
   - **Space name**: `mindily`
   - **License**: MIT
   - **SDK**: **Docker** → *Blank*
   - **Hardware**: CPU basic (무료)
   - **Visibility**: Public
3. **Create Space**

## 2. 환경변수와 Secret 등록

Space 페이지 → **Settings** → *Variables and secrets*

| 이름 | 종류 | 값 |
|---|---|---|
| `CODYSSEY_API_KEY` | **Secret** | 코디세이에서 발급받은 API 키 |
| `CODYSSEY_API_BASE` | Variable | 코디세이에서 안내받은 `/v1` 엔드포인트 |
| `CODYSSEY_MODEL` | Variable | 코디세이에서 지정한 모델명 (예: `gpt-5-mini`) |
| `MINDILY_SURVEY_WEBHOOK_URL` | **Secret** | 배포된 Google Apps Script 웹 앱의 `/exec` URL |

> 코디세이 관련 세 값은 안내받은 것을 그대로 넣습니다. Google Sheets 평가를 사용하려면 `MINDILY_SURVEY_WEBHOOK_URL`도 필요합니다. 웹 앱 URL과 API 키는 GitHub 파일이나 화면 캡처에 노출하지 않습니다. OpenAI 호환 규격이므로 다른 공급자로 바꿀 때도 이 세 값만 교체하면 됩니다.
> 키를 등록하지 않아도 서비스는 동작합니다. 코치 문장이 규칙 기반으로 폴백되고, `/api/llm/status`가 `mode: deterministic_fallback`을 반환합니다.

## 3. 배포

GitHub `codyssey-seungmin/M2-1`과 Hugging Face `yellowmug/mindily`는 별도 Git 저장소입니다. GitHub의 변경은 Space에 자동 반영되지 않습니다. 기존 Space 이력을 보존하려면 Space 저장소를 별도 폴더에 clone하고 변경 파일을 복사한 뒤 일반 커밋과 push를 사용합니다. force push는 사용하지 않습니다. 인증에는 계정 비밀번호 대신 쓰기 권한의 Hugging Face 토큰을 사용하며 토큰은 명령어·문서·캡처에 넣지 않습니다.

자동 배포 스크립트를 사용하는 경우:

```bash
# 최초 1회: HF 로그인
pip install huggingface_hub
huggingface-cli login

# 배포
chmod +x deploy_space.sh
./deploy_space.sh yellowmug
```

스크립트가 하는 일:
1. Space 저장소를 임시 폴더로 clone
2. 배포에 필요한 파일만 복사 (`Dockerfile`, `requirements.txt`, `*.py`, `dist/`)
3. `SPACE_README.md`를 Space용 `README.md`로 복사 — **Space는 YAML 프런트매터가 필요**하기 때문
4. 커밋 후 push → Space에서 빌드 자동 시작

최초 빌드는 약 **10~15분**(PyTorch 설치 + 모델 다운로드)이 걸립니다. Space 페이지의 **Logs** 탭에서 진행 상황을 볼 수 있습니다.

## 4. 배포 확인

```bash
curl https://yellowmug-mindily.hf.space/api/health
curl https://yellowmug-mindily.hf.space/api/llm/status
```

기대 결과:

```json
{
  "status": "ready",
  "model": "GGARA02/kcelectra-korean-emotion",
  "revision": "2eaf89d8d2cbfd902b93e5ec989db2ec103806fb",
  "generation": {
    "llm_enabled": true,
    "provider": "codyssey (OpenAI-compatible)",
    "mode": "llm_grounded",
    "sends_diary_text": false
  }
}
```

휴대폰에서 URL을 열어 실제 분석까지 확인하고, 화면을 캡처해 `evidence/`에 저장합니다.

---

## 알아둘 점

### 데이터 저장 위치가 나뉩니다
무료 등급 Space는 영구 디스크가 없어 **재시작하면 SQLite의 선호 기억과 기존 피드백 데이터가 초기화**될 수 있습니다. 현재 앱 평가 화면의 응답은 외부 Google Sheets에 저장되므로 Space 재시작의 영향을 받지 않습니다. 일기와 기록은 각 사용자 브라우저에 저장됩니다.

Google Sheets는 필요한 팀원에게만 공유하고, 과제 평가·분석이 끝나면 정한 보존 기준에 따라 정리합니다. 기존 SQLite 집계를 사용하는 경우에만 재시작 전에 별도로 내려받습니다.

기존 SQLite 피드백을 계속 운영할 때만 별도의 내보내기 또는 Persistent Storage 설정이 필요합니다. 현재 Google Sheets 앱 평가에는 해당하지 않습니다.

### 절전 모드
무료 Space는 48시간 미사용 시 절전합니다. 발표·테스트 **10분 전에 URL을 한 번 열어** 깨워 두세요.

### 삭제한 파일
| 파일 | 이유 |
|---|---|
| `render.yaml` | 유료 플랜 전제, HF Spaces로 대체 |
| `START_QUICK_TUNNEL.cmd`, `docs/QUICK_TUNNEL.md` | 임시 터널은 영구 URL 확보로 불필요 |
| `.openai/hosting.json` | 정적 호스팅 설정, 현재 구조와 무관 |
