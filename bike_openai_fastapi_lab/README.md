# bike_openai_fastapi_lab · 실제 CSV에서 API 기사까지

> 목표: CSV를 Python으로 계산한 뒤 **검증한 facts만** OpenAI API에 보내 기사 초안을 받는다.
> 먼저 `template`로 무료 점검한다. **template 출력은 AI가 쓴 기사가 아니다.**

## 오늘의 결과물

- `facts.py`: CSV 읽기 → 비운영 행 제외 → 시간대별 합계·관측 수·평균
- `generation.py`: facts → OpenAI Responses API → 기사 초안
- `app.py`: `POST /articles` 요청 → facts와 article을 JSON으로 반환
- `index.html`: 무료 사전 점검 화면. 실제 요청은 `/docs`에서 직접 실행
- `evidence/template-response.json`: 실제 CSV로 얻은 **고정 문장 응답**
- `evidence/test-results.txt`: 유료 호출 없는 테스트 기록

흐름: 브라우저 `/docs` → 내 FastAPI → Python 계산 → OpenAI(선택) → 내 FastAPI → 브라우저.
ChatGPT 대화창에 CSV를 붙이는 방식이 아니다. 학습·파인튜닝도 하지 않는다.

## 1. 준비 · VS Code에서 폴더 열기

이 저장소의 `bike_openai_fastapi_lab` 폴더를 VS Code의 **파일 → 폴더 열기**로 연다. 아래 명령은 모두 `app.py`와 `requirements.txt`가 있는 이 폴더에서 실행한다.
저장소 루트에서 터미널을 열었다면 먼저 `cd bike_openai_fastapi_lab`을 실행한다.
Python 3.11 이상을 사용한다. 검증 환경은 Linux + Python 3.12이며 Windows 명령은 안내만 제공한다.
터미널은 **터미널 → 새 터미널**로 연다. 다음 명령을 한 줄씩 실행한다.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

터미널에 `Uvicorn running on http://127.0.0.1:8000`이 나오면 서버가 켜졌다.
터미널을 닫지 말고 브라우저에서 http://127.0.0.1:8000 을 연다.
VS Code 인터프리터 선택에서도 `.venv`를 선택한다. 라이브러리 설치에는 인터넷이 필요하다.

## 2. 무료 사전 점검 · 실제 CSV → facts

1. 첫 화면에서 **template 사전 점검 실행**을 누른다.
2. `200 OK`, `AI 미호출`을 확인한다. 고정 문장과 facts JSON을 읽는다.
3. http://127.0.0.1:8000/docs 를 연다.
4. 초록색 `POST /articles` → **Try it out** → 아래 요청 → **Execute**.

```json
{"mode": "template"}
```

반환값에서 `ai_generated: false`, `model: null`, `review_required: true`를 확인한다.
이 단계는 API 키 없이 실행된다. `/docs` 화면의 외부 UI 파일 로딩에는 인터넷이 필요할 수 있다.

### 계산 결과가 다음과 같은가?

- 전체: **8,760행**, 2017-12-01 ~ 2018-11-30
- 첫 세 대여 건수: **254, 204, 173** (합계 631, 평균 약 210.33)
- `Functioning Day == No` **295행 제외**, 운영 관측 **8,465행**
- 시간대별 평균이 가장 높은 시각: **18시**
- 18시: **548,568 ÷ 353 = 약 1,554.02건**

Colab의 1,554.0건(소수 첫째 자리)과 이 앱의 1,554.02건(소수 둘째 자리)은 같은 548,568 ÷ 353을 반올림해 표시한 것이다. 계산 조건이 달라진 것이 아니다.

한 행은 특정 날짜의 특정 시간 관측이다. 18시 평균의 분모는 8,465가 아니라 **18시 운영 관측 353개**다.
비운영 시간은 수요가 0이었다는 뜻으로 해석하지 않고 제외한다. 운영 시간에 관측된 0건은 유지한다.
대여 건수는 고유 이용자 수가 아니다. 이 과거 자료로 현재 이용 현황이나 퇴근이 원인이라고 단정하지 않는다.

## 3. 코드 읽기 · 어디에서 무엇을 하는가?

1. `facts.py`의 `csv.DictReader`: 첫 행을 열 이름으로 사용한다. 원본은 `latin1` 인코딩이다.
2. `if operating == 'No'`: 비운영 **행**을 제외한다. 달력 날짜 전체를 삭제하지 않는다.
3. `totals[hour] / counts[hour]`: 시간대별 분모로 평균을 계산한다.
4. `generation.py`의 `instructions`: 기사 형식·단위·금지할 추측을 지정한다.
5. `input=json.dumps(facts, ensure_ascii=False)`: 계산한 근거를 JSON 문자열로 보낸다.
6. `response.output_text`: 모델이 반환한 문장이다. 검증 완료를 뜻하지 않는다.
7. `app.py`의 `@app.post('/articles')`: 입력 JSON을 받아 결과 JSON을 돌려준다.

## 4. 실제 OpenAI 생성 · 본인 키로만 선택 실행

**이 패키지를 준비하면서 유료 API 호출은 하지 않았다.** 실제 생성·잔액·계정별 모델 접근은 학생 실행 시 확인한다.
OpenAI API는 ChatGPT 구독과 별도 과금이다. 학교의 키·결제 지침을 먼저 확인한다.
공유 키를 배포하거나 코드·Notion·GitHub·스크린샷에 키를 쓰지 않는다.
API 키 생성·결제 설정은 본인이 직접 한다. 이 예제는 키를 만들거나 저장하지 않는다.

1. 기존 서버 터미널에서 `Ctrl+C`로 종료한다.
2. 아래 명령으로 실행하고, **터미널의 비표시 입력창**에 본인 키를 직접 입력한다.
   키는 이 프로세스의 환경변수에만 들어가며 파일·명령 기록에 저장하지 않는다. 서버 종료 시 끝난다.

```powershell
# Windows
.\.venv\Scripts\python.exe start_api.py
```

```bash
# macOS / Linux
.venv/bin/python start_api.py
```

3. `/docs` → `POST /articles` → **Try it out**에서 다음으로 바꾼다.

```json
{"mode": "openai"}
```

4. **공개 UCI 데이터에서 계산한 facts와 지시문이 OpenAI로 전송되고 비용이 발생한다**는 점을 확인하고 Execute를 한 번 누른다.
5. 성공하면 `ai_generated: true`, 모델명, facts, article을 확인한다. `true`는 모델 경로를 썼다는 뜻이며 정확성 인증이 아니다.
6. 본문의 기간·18시 합계·353개 관측·평균·건수 단위를 facts와 직접 대조한다.
7. 끝나면 서버를 `Ctrl+C`로 종료한다. 개인 자료를 이 실습 CSV로 바꾸어 넣지 않는다.

기본 모델은 공식 문서에서 현재 종료 예정 표시가 없는 `gpt-5.4-mini-2026-03-17` snapshot이다.
기본 모델에는 `reasoning={"effort":"none"}`을 사용한다. 문서 확인은 본인 계정에서의 접근·생성 성공을 보장하지 않는다.
교사가 다른 모델을 지정했다면 서버 실행 전 `OPENAI_MODEL` 환경변수로 변경할 수 있다. 다른 모델의 파라미터·가격·출력 제한 호환성은 다시 확인해야 한다.
이전 예제의 `gpt-4.1-mini`나 `gpt-5-mini`는 공식 문서에 Deprecated 표기가 있어 새 기본값으로 쓰지 않는다.
공식 모델 안내: https://developers.openai.com/api/docs/models/gpt-5.4-mini
`max_output_tokens=700`, 30초 timeout, 자동 재시도 없음, `store=False`로 요청한다.
`store=False`는 응답 저장 옵션이며, 모든 형태의 서비스 로그·보존이 없다는 보장은 아니다.
반복 클릭과 수동 재시도는 추가 과금될 수 있다. timeout이라도 서버에서 요청이 처리됐을 수 있으므로 사용 내역을 먼저 확인한다.

## 5. 오류도 직접 확인하기

`/docs`에 `{"mode":"wrong"}`를 입력하면 **422**가 정상이다. 허용값 두 개 외에는 거절한다.

| 화면 코드 | 뜻 | 할 일 |
|---|---|---|
| 422 | 입력 모드/CSV 오류 | template/openai, CSV 경로·열·값 확인 |
| 503 | 키 없음 | template로 먼저 점검, 필요하면 start_api.py 재실행 |
| 502 + 인증 실패 | 키·권한 문제 | 본인이 키와 프로젝트 확인; 키를 메시지로 보내지 않기 |
| 429 | 사용량·잔액·요청 제한 | 계정 사용 내역 확인; 무작정 반복 실행하지 않기 |
| 504 | timeout | 과금 내역과 네트워크 확인 후 재시도 판단 |
| 502 + 응답 미완료 | 출력 제한/모델 응답 문제 | 부분 문장을 기사로 제출하지 않기 |

`ModuleNotFoundError`: `.venv`의 Python으로 설치와 실행을 모두 했는지 확인한다.
`Error loading ASGI app`: `app.py`가 있는 폴더에서 실행한다.
`Address already in use`: 이전 서버를 종료하거나 포트를 8001로 바꾸고 브라우저 주소도 맞춘다.
CSV를 UTF-8로 열어 오류가 나면 예제의 `encoding='latin1'`을 유지한다.

## 6. 제출 전 확인

- [ ] 무료 template 성공 화면과 facts를 설명할 수 있다.
- [ ] 합계/관측 수/평균의 차이를 설명한다.
- [ ] 실제 AI 호출 여부를 정확히 표기한다. 미실행이면 '미실행'이라고 쓴다.
- [ ] AI 본문과 facts의 숫자·기간·단위를 대조했다.
- [ ] 근거에 없는 원인·이용자 수 표현을 제거했다.
- [ ] 캡처와 제출 파일에 API 키가 없다.

최소 제출: facts 중 18시 결과 + 기사 초안(또는 template 점검 결과) + 수정한 문장 1개와 이유.
실제 호출이 안 되는 학생도 계산·API 요청 구조·검증 단계까지 먼저 완료한다.

## 7. 테스트 재실행

```powershell
# Windows
.\.venv\Scripts\python.exe -m pytest -q
```

```bash
# macOS / Linux
.venv/bin/python -m pytest -q
```

테스트는 실제 CSV와 FastAPI 요청·오류, SDK의 mock HTTP 응답을 확인한다.
mock 응답은 테스트 대역이며 실제 모델의 기사 품질을 검증하지 않는다.
최종 검증: 깨끗한 Linux Python 3.12 가상환경에서 **23개 통과**. Starlette의 httpx 테스트 클라이언트 deprecation 경고 1개가 있으며 실행 실패는 아니다. Windows와 유료 실호출은 미실행이다.
이 앱은 로컬 교육용이다. 인증·배포·다중 사용자 운영을 위한 서비스가 아니다.

## 출처

- 데이터: Seoul Bike Sharing Demand [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5F62R
- 라이선스: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . 동봉 CSV는 원본 그대로이며 계산·표현만 추가했다.
- 공식 Python SDK: https://github.com/openai/openai-python
- 모델: https://developers.openai.com/api/docs/models/gpt-5.4-mini
- Responses API: https://developers.openai.com/api/reference/python/resources/responses/methods/create

`bike_openai_fastapi_lab` 실습 범위: CSV·facts·FastAPI·OpenAI 호출·대조 검증. 이후 수업 자료는 이 패키지에 포함하지 않는다.
