# 3개 모델 비교 도구 (원본 / 학습본 / gpt-4.1-mini)

같은 질문을 3개 모델에 넣고, 답을 나란히 보여주는 비교표(compare_report.html)를 만듭니다.

## 파일
| 파일 | 하는 일 |
|---|---|
| compare.py | 실행 코드 |
| prompts.txt | 비교할 질문 (빈 줄로 구분, 자유롭게 수정) |
| .env.example | API 키 적는 양식 → `.env`로 복사해서 사용 |
| .gitignore | `.env`와 결과 파일이 깃허브에 올라가지 않게 막음 |
| requirements.txt | 필요한 패키지 |

## 처음 한 번 (설치)
```powershell
cd 폴더경로\compare3
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
`.env`에 두 키를 붙여 넣고 저장합니다.
- UNSLOTH_API_KEY: Studio → 왼쪽 아래 프로필/설정 → API Keys → 이름 입력 → Create (한 번만 보여줌)
- OPENAI_API_KEY: OpenAI 플랫폼에서 발급한 키

## 매번 (비교 실행)
Studio(검은 창)가 켜져 있어야 합니다.
```powershell
.\.venv\Scripts\Activate.ps1

# 1) Studio 채팅에서 "원본 Qwen2.5-3B-Instruct"를 선택(불러오기)한 뒤
python compare.py studio --label 원본

# 2) Studio 채팅에서 "Fine-tuned" 탭의 학습 모델로 바꾼 뒤
python compare.py studio --label 학습본

# 3) gpt-4.1-mini
python compare.py openai

# 4) 비교표 만들기 (브라우저가 자동으로 열림)
python compare.py report
```

## 팁
- 같은 라벨로 다시 실행하면 최신 결과로 비교표가 바뀝니다.
- 처음부터 다시 하려면 `results.jsonl`을 지우세요.
- 비교 조건을 같게 하려고 3개 모두 temperature 0.3, 최대 500토큰으로 고정했습니다.
- 초록/빨강 배지(질문 시작·한 줄 정리·줄 수)는 자동 확인이라 참고용입니다. 최종 판단은 사람이 합니다.
