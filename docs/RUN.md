# 실행과 배포 안내

Python 3.12 기준. 저장소 폴더에서 실행합니다.
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000 --no-access-log
```
http://127.0.0.1:8000 을 엽니다. 설치 후에는 START.cmd를 두 번 클릭합니다. 처음에는 모델 다운로드 시간이 필요합니다.
`MINDILY_OFFLINE=1`은 지정한 `HF_HOME` 캐시에 토크나이저와 모델 가중치가 모두 있을 때만 사용합니다. 캐시가 일부만 있을 때는 서버 시작이 실패하므로 처음 실행에서는 설정하지 마세요.
dist/index.html만 직접 열면 실제 분석 API를 사용할 수 없습니다.

일반 사용자는 주소만 열면 되도록 구성했고, 현재 https://yellowmug-mindily.hf.space 에서 상시 동작합니다.
동의한 앱 평가는 Google Apps Script를 거쳐 Google Sheets에 저장되고, 동의한 선호 활동은 SQLite 파일로 `data/`에 30일간 저장됩니다. 무료 Space 재시작 시 SQLite 선호 기억은 초기화될 수 있지만 Google Sheets 평가는 유지됩니다.
`python test_packaging.py`는 Dockerfile에 서버가 import하는 로컬 모듈이 모두 포함됐는지 검사합니다. 실제 Docker 이미지 빌드는 Docker가 설치된 환경에서 별도로 확인해야 합니다.
```sh
docker build -t mindily .
docker run --rm -p 8000:8000 -v mindily-data:/app/data mindily
```
모델 다운로드 공간·메모리·HTTPS·요청 제한·로그 정책을 확인한 뒤 배포합니다. GitHub Pages만으로 Python 모델을 실행할 수 없습니다.

## 외부 배포 (Hugging Face Spaces)

이 저장소는 Docker SDK 기반 Space로 배포합니다. Render 설정(`render.yaml`)은 유료 플랜을 전제로 해 삭제했습니다.

| 항목 | 값 |
|---|---|
| 주소 | https://yellowmug-mindily.hf.space |
| 관리 | https://huggingface.co/spaces/yellowmug/mindily |
| SDK · 포트 | Docker · 7860 |
| 하드웨어 | CPU basic (무료) |
| 모델 | 빌드 시 이미지에 동봉 → 첫 요청 지연 없음 |
| 앱 평가 | Google Apps Script → Google Sheets |

올리는 방법은 두 가지입니다.

1. **`push_to_huggingface.cmd` 더블클릭** — `_space_upload/` 폴더를 Space와 비교해 바뀐 파일만 올리고, 필요 없는 파일은 지웁니다. 로그인은 계정 비밀번호가 아니라 **쓰기(write) 토큰**을 씁니다.
2. Space의 **Files → Upload files** 로 `_space_upload/`의 파일을 폴더 없이 전부 올립니다.

GitHub 저장소와 Hugging Face Space는 별도 저장소입니다. GitHub에 푸시한 것만으로 배포 앱이 바뀌지 않으므로 Space에도 커밋을 올려야 합니다. Space에는 `CODYSSEY_API_KEY`, `MINDILY_SURVEY_WEBHOOK_URL`을 Secret으로 등록하고 `CODYSSEY_API_BASE`, `CODYSSEY_MODEL`을 Variable로 등록합니다.

올린 뒤 확인합니다.

```sh
curl https://yellowmug-mindily.hf.space/api/health      # status: ready, 모델·리비전
curl https://yellowmug-mindily.hf.space/api/llm/status  # llm_grounded 여부와 last_error
```

자세한 절차와 환경 변수는 [배포 가이드](DEPLOY_HF.md), 처음 하는 경우에는 [배포 시작하기](../배포_시작하기.md)를 참고합니다.

Vercel에는 현재 Python API 전체를 그대로 올리기 어렵습니다. Python Function의 압축 해제 후 크기 상한이 500MB이고 파일 저장이 영속적이지 않아, PyTorch 모델과 SQLite를 쓰는 이 구조에는 맞지 않습니다.

## 검증
requirements-dev.txt 설치 후 서버를 8010 포트에서 실행하고 python test_api.py를 실행합니다.
실제 가상 예문 검증 결과는 evidence/api-check.json입니다.

## 데이터 처리
분석 시 글이 이 앱의 서버로 전송되며 서버 코드는 원문을 저장하지 않습니다. 운영 호스팅의 로그 정책은 별도 확인이 필요합니다.
현재 브라우저 localStorage에 최대 30개 기록을 저장합니다. 같은 브라우저 사용자 간 분리와 기기 간 동기화는 미구현입니다.
일기 원문도 localStorage 기록에 포함됩니다. 공용 기기에서 사용하면 같은 브라우저의 다른 사람이 읽을 수 있으므로 마음 기록 화면의 삭제 버튼으로 기록을 지워야 합니다.
새 앱 평가는 디자인·감정 도움·계속 사용할 의향 1~5점, 필수 개선 의견, 자동 참여 코드, 중복 방지용 제출 ID를 Google Sheets에 저장합니다. 이름·이메일·일기 원문은 평가에 포함하지 않습니다. 참여 코드는 같은 브라우저의 반복 평가를 묶고, 제출 ID는 같은 평가 요청의 중복 행을 막습니다. 기존 `/api/feedback`의 SQLite 저장은 과거 기능과 호환을 위해 남아 있지만 현재 앱 평가 화면의 수집 경로는 아닙니다.

동의한 선호 활동 한 가지는 `data/memory.sqlite3`에 저장됩니다. 저장소의 토큰 해시로 선호를 조회·삭제하며 브라우저 토큰을 잃으면 즉시 조회·삭제할 수 없습니다. 30일 지난 선호는 다음 기억 요청 때 정리됩니다. 감정 정리하기 내용은 브라우저 localStorage에 저장됩니다. 자세한 설문 운영 방법은 [Google Sheets 평가 수집 안내](GOOGLE_SHEETS_SURVEY.md)를 참고합니다.
