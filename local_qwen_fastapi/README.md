# 내 PC에서 Qwen 실행하기

Windows 11 · RTX 5070 Laptop GPU · 전용 VRAM 8GB · VS Code · FastAPI

공식 문서 확인: 2026-10-15. **사용자 PC에서 모델을 실행하거나 속도를 측정한 자료는 아닙니다.**

## 구성

- **Ollama**: 내려받은 모델 실행
- **Qwen2.5**: 한국어 뉴스 초안 생성
- **FastAPI**: 기존 Python 앱과 모델 연결
- **VS Code**: 코드 작성·실행

이번 단계는 **이미 학습된 모델을 사용하는 추론**입니다. 파인튜닝은 하지 않습니다. Ollama Windows 설치판에는 NVIDIA 실행용 의존성이 포함됩니다. 이 경로에서는 WSL·Docker·PyTorch·CUDA Toolkit을 별도로 준비하지 않습니다.

## 1. GPU·드라이버 확인

전원을 연결하고 PowerShell에서 실행하세요.

```powershell
nvidia-smi
```

GPU 이름·드라이버 버전·메모리 사용량을 확인하세요. 인식되지 않으면 노트북 제조사 또는 [NVIDIA 공식 드라이버](https://www.nvidia.com/en-us/drivers/)에서 해당 RTX 5070 Laptop용 드라이버를 확인하세요. 구형 GPU 공통 최소 버전을 50시리즈 설치 기준으로 사용하지 마세요.

**시스템 RAM 약 64GB와 GPU 전용 VRAM 8GB는 다릅니다.** 공유 GPU 메모리가 전용 VRAM처럼 같은 속도를 제공하지는 않습니다.

[공식 GPU 지원 목록](https://docs.ollama.com/gpu)

## 2. Ollama 설치

[Windows 설치 파일](https://ollama.com/download/windows)을 내려받아 설치하세요. 설치 후 VS Code와 터미널을 다시 여세요.

```powershell
ollama --version
```

Ollama 앱은 뒤에서 실행되며 로컬 API의 기본 포트는 **11434**입니다. 이미 앱이 실행 중이면 `ollama serve`를 다시 실행하지 마세요.

설치와 모델 다운로드에는 인터넷이 필요합니다. 모델을 받은 뒤 이 예제의 로컬 생성에는 OpenAI API Key가 필요하지 않습니다.

[Windows 공식 설치 안내](https://docs.ollama.com/windows) · [로컬 API 인증 안내](https://docs.ollama.com/api/authentication)

## 3. 모델 다운로드

먼저 작은 모델로 실행 상태를 확인하세요.

```powershell
ollama pull qwen2.5:3b
ollama list
ollama run qwen2.5:3b
```

대화창에 짧은 한국어 질문을 입력하세요. 종료는 `/bye`입니다.

- **3B**: Q4_K_M, 다운로드 약 **1.9GB**
- **7B**: Q4_K_M, 다운로드 약 **4.7GB**
- 다운로드 크기와 실행 중 VRAM 사용량은 다릅니다.
- 7B 비교는 3B 실행을 확인한 다음 진행하세요. 다른 GPU 앱과 긴 입력은 VRAM 여유를 줄입니다.

```powershell
ollama pull qwen2.5:7b
```

**라이선스 확인:** 3B는 Qwen Research License, 7B는 Apache 2.0입니다. 무료 다운로드와 모든 용도의 자유로운 사용은 같은 의미가 아닙니다. 수업·배포 조건에 맞게 각 모델의 라이선스를 확인하세요.

[3B 모델·라이선스](https://ollama.com/library/qwen2.5:3b) · [7B 모델·라이선스](https://ollama.com/library/qwen2.5:7b)

## 4. GPU 적재 확인

모델 응답 직후 다른 PowerShell 창에서 확인하세요.

```powershell
ollama ps
nvidia-smi
```

`ollama ps`의 **PROCESSOR** 열:

- `100% GPU`: 모델 전체 GPU 적재
- `100% CPU`: 시스템 RAM에 적재
- `CPU/GPU` 혼합: 두 곳에 나누어 적재

**100% GPU는 GPU 사용률이 항상 100%라는 뜻이 아닙니다.** 실행 중 모델이 없다면 `ollama ps`가 비어 있을 수 있습니다.

CPU로만 실행되면 Ollama와 드라이버를 업데이트하고 다시 시작하세요. 다른 GPU 앱을 종료하고 작은 모델로 확인하세요.

[GPU 적재·메모리 공식 설명](https://docs.ollama.com/faq)

## 5. VS Code 환경

압축을 풀고 `local_qwen_fastapi` 폴더를 VS Code에서 여세요. **Python 3.12가 이미 설치된 경우** 아래 명령을 사용하세요. 없다면 [Python 공식 Windows 다운로드](https://www.python.org/downloads/windows/)에서 지원 중인 Python을 설치하고 해당 버전 번호로 바꾸세요. 기존 프로젝트 환경은 덮어쓰지 마세요.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

VS Code에서 `Ctrl+Shift+P` → `Python: Select Interpreter` → `.venv`를 선택하세요. Microsoft의 Python 확장이 없으면 VS Code 확장 화면에서 설치하세요.

가상환경 활성화 명령 없이 실행 파일을 직접 사용합니다. PowerShell 실행 정책 변경은 필요하지 않습니다.

## 6. FastAPI 실행

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

브라우저에서 **http://127.0.0.1:8000/docs** 를 여세요.

`POST /articles` → `Try it out` → 다음 항목을 자신의 실제 자료로 입력하세요.

- `topic`: 뉴스 주제
- `source`: 원자료 이름·기관·URL
- `facts`: 검토한 사실, 대상·기간·단위·계산값·한계

기존 앱에서 만든 Fact Sheet의 필요한 부분을 `facts`에 넣으세요. CSV 전체를 붙여넣지 마세요. 입력은 짧게, 핵심 근거 중심으로 작성하세요.

`Execute`를 누르고 `article`의 한국어 초안을 확인하세요.

이 연결 예제는 `num_ctx=4096`, 출력 상한 `num_predict=512`, 모델 유지 `keep_alive=10m`입니다. 출력이 길어 잘리면 `truncated`가 `true`로 표시됩니다. 토큰 수는 글자 수와 다릅니다.

**초안은 원자료 및 Fact Sheet와 대조하세요.** 수치·날짜·단위·출처·원인 단정을 확인하고 수정하세요. 이 예제는 연결·속도 확인용이며 자동 검증, 승인, DB 저장 기능은 포함하지 않습니다.

[Ollama 채팅 API](https://docs.ollama.com/api/chat)

## 7. 7B로 비교

FastAPI 터미널에서 `Ctrl+C`로 종료한 뒤 실행하세요.

```powershell
ollama stop qwen2.5:3b
$env:OLLAMA_MODEL="qwen2.5:7b"
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

3B로 돌아가기:

```powershell
$env:OLLAMA_MODEL="qwen2.5:3b"
```

환경변수를 바꾼 뒤 FastAPI를 다시 실행하세요. 실행 중 프로세스에는 변경이 바로 적용되지 않습니다.

## 8. 시간 비교

동일한 Fact Sheet로 짧은 원고를 3회 생성하세요.

- **1회차**: 모델 로딩이 포함될 수 있음
- **2·3회차**: 메모리에 올라온 상태의 반복 실행
- `elapsed_seconds`: 요청부터 응답까지의 시간
- `load_seconds`: 모델 로딩 시간
- `output_tokens_per_second`: 출력 생성 구간의 초당 토큰 수

속도와 함께 **근거 일치·한국어 표현·수정량**을 비교하세요. 로컬 모델이 항상 OpenAI API보다 빠르거나 좋은 것은 아닙니다. 노트북 전력·발열, 입력 길이, GPU 적재 상태에 따라 달라집니다.

다운로드 시간도 별도입니다. 가령 실제 다운로드 속도 10MB/s라면 1.9GB는 약 3분, 4.7GB는 약 8분에 해당하며 설치·검증 시간은 추가됩니다. 이는 계산 예시이며 측정값이 아닙니다.

## 오류 확인

- 명령 인식 안 됨: Ollama 설치 후 VS Code·PowerShell 다시 열기
- `503`: Ollama 앱 실행 여부 확인
- `502`, 모델 없음: 동일 모델 이름으로 `ollama pull` 실행
- `504`: GPU 적재·입력 길이·다른 실행 프로그램 확인
- `422`: 비어 있거나 너무 긴 입력 확인
- `11434` 포트 충돌: 이미 실행된 Ollama 앱 확인, 중복 `serve` 종료
- CPU 혼합 적재·메모리 부족: 3B 및 짧은 입력으로 재확인

로그: 파일 탐색기 주소창에 `%LOCALAPPDATA%\Ollama` 입력 → `server.log` 확인.

## 로컬 범위

- 이 예제는 **127.0.0.1**로만 연결합니다.
- 11434 포트를 인터넷이나 학원 LAN에 공개하지 마세요.
- 클라우드 모델, 웹 검색, 외부 API를 연결하면 별도 외부 전송이 발생할 수 있습니다.
- 로컬 전용으로 제한하려면 Windows 사용자 환경변수 `OLLAMA_NO_CLOUD=1`을 설정하고 Ollama 앱을 완전히 종료 후 다시 실행하세요. 방화벽 변경은 필요하지 않습니다.

## 예제 검사

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

테스트는 **모의 응답**으로 앱 상태·필수 입력·응답 처리·연결 오류 4가지를 검사합니다. 모델 다운로드나 GPU가 없어도 실행됩니다. 실제 모델 성능·한국어 품질 검사는 아닙니다.

제작 환경의 Python 3.12/Linux에서 4개 검사 통과. Windows 명령 및 GPU 추론은 사용자 환경에서 확인해야 합니다. 제작 환경에서 Starlette/httpx 테스트 호환성 관련 deprecation 경고 1건이 있었으며 검사는 통과했습니다.

## 다음 연결

현재 단계: Fact Sheet → 로컬 LLM → 뉴스 초안 → 사람 검토

다음 단계: 필요한 문서를 검색하는 RAG → LangChain 연결 → 필요할 때 파인튜닝
