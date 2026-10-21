"""
같은 질문을 3개 모델에 넣고 나란히 비교하는 도구
  ① 원본 Qwen2.5-3B   (Unsloth Studio API)
  ② 파인튜닝 모델      (Unsloth Studio API)
  ③ gpt-4.1-mini       (OpenAI API)

사용법 (PowerShell, 이 폴더에서)
  python compare.py studio --label 원본      # Studio 채팅에서 원본 모델을 불러온 뒤
  python compare.py studio --label 학습본    # Studio 채팅에서 학습한 모델로 바꾼 뒤
  python compare.py openai                   # gpt-4.1-mini
  python compare.py report                   # 3칸 비교표(compare_report.html) 만들기
"""

import argparse
import html
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ── 설정 (필요하면 여기만 고치세요) ─────────────────────────────
STUDIO_URL = "http://127.0.0.1:8888/v1"   # Unsloth Studio 주소
OPENAI_MODEL = "gpt-4.1-mini"
TEMPERATURE = 0.3      # 낮을수록 매번 비슷한 답 (비교에 유리)
MAX_TOKENS = 500       # 답 길이 상한
HERE = Path(__file__).parent
PROMPTS_FILE = HERE / "prompts.txt"
RESULTS_FILE = HERE / "results.jsonl"
REPORT_FILE = HERE / "compare_report.html"
COLUMN_ORDER = ["원본", "학습본", "gpt-4.1-mini"]
# ──────────────────────────────────────────────────────────────

# 한글이 깨지지 않게
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

load_dotenv(HERE / ".env")


def load_prompts():
    """prompts.txt 읽기. 빈 줄로 질문을 구분합니다."""
    if not PROMPTS_FILE.exists():
        sys.exit(f"[오류] {PROMPTS_FILE.name} 파일이 없습니다.")
    text = PROMPTS_FILE.read_text(encoding="utf-8").replace("\r\n", "\n")
    prompts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not prompts:
        sys.exit("[오류] prompts.txt 에 질문이 없습니다.")
    return prompts


def save_result(label, model_id, prompt_no, prompt, answer, seconds):
    row = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "model": model_id,
        "no": prompt_no,
        "prompt": prompt,
        "answer": answer,
        "seconds": round(seconds, 1),
    }
    with RESULTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def ask_all(client, model_id, label):
    prompts = load_prompts()
    print(f"\n▶ [{label}] 모델: {model_id}  /  질문 {len(prompts)}개\n")
    for i, prompt in enumerate(prompts, 1):
        start = datetime.now()
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            answer = (res.choices[0].message.content or "").strip()
        except Exception as e:
            msg = str(e)
            if "No model loaded" in msg:
                sys.exit(
                    "\n[멈춤] Studio에 모델이 아직 불러와져 있지 않습니다. 둘 중 하나를 하세요.\n"
                    "  A) Studio → 설정 → API → 'Model auto-switch' 켜기 (추천)\n"
                    "  B) Studio 새 채팅에서 모델을 선택하고 '안녕'을 한 번 보내 로드한 뒤 다시 실행\n"
                    "  (오류 결과는 저장하지 않았습니다)"
                )
            print(f"--- 질문 {i} 오류 ---\n{msg}\n(이 질문은 저장하지 않고 넘어갑니다)\n")
            continue
        sec = (datetime.now() - start).total_seconds()
        save_result(label, model_id, i, prompt, answer, sec)
        print(f"--- 질문 {i} ({sec:.1f}초) ---\n{answer}\n")
    print(f"✅ 저장 완료: {RESULTS_FILE.name}")


def run_studio(label, model_arg=None):
    key = os.getenv("UNSLOTH_API_KEY")
    if not key:
        sys.exit("[오류] .env 에 UNSLOTH_API_KEY 가 없습니다. (Studio → 설정 → API Keys 에서 발급)")
    client = OpenAI(base_url=STUDIO_URL, api_key=key)
    try:
        models = [m.id for m in client.models.list().data]
    except Exception as e:
        sys.exit(
            f"[오류] Studio에 연결하지 못했습니다: {e}\n"
            "  - 검은 Studio 창이 켜져 있는지\n"
            "  - 주소가 http://127.0.0.1:8888 인지\n"
            "  - API 키가 맞는지 확인하세요."
        )
    if not models:
        sys.exit("[오류] Studio에 불러온 모델이 없습니다. Studio 채팅 화면에서 모델을 먼저 선택하세요.")
    model_id = models[0]
    if model_arg:
        model_id = model_arg
    elif len(models) > 1:
        print("불러온 모델이 여러 개입니다:")
        for n, m in enumerate(models, 1):
            print(f"  {n}. {m}")
        pick = input("사용할 번호를 입력하세요 [1]: ").strip() or "1"
        model_id = models[int(pick) - 1]
    ask_all(client, model_id, label)


def run_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("[오류] .env 에 OPENAI_API_KEY 가 없습니다.")
    ask_all(OpenAI(api_key=key), OPENAI_MODEL, "gpt-4.1-mini")


def quick_checks(answer):
    """채점표 중 자동으로 볼 수 있는 3가지"""
    lines = [l for l in answer.splitlines() if l.strip()]
    first = lines[0] if lines else ""
    return {
        "질문으로 시작": "?" in first,
        "한 줄 정리": "한 줄 정리" in answer,
        "줄 수": len(lines),
    }


def make_report():
    if not RESULTS_FILE.exists():
        sys.exit("[오류] results.jsonl 이 없습니다. 먼저 studio / openai 를 실행하세요.")
    rows = [json.loads(l) for l in RESULTS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]

    # 같은 (질문번호, 라벨)이 여러 번 있으면 가장 최근 것 사용
    latest = {}
    for r in rows:
        latest[(r["no"], r["label"])] = r
    labels = [l for l in COLUMN_ORDER if any(k[1] == l for k in latest)]
    labels += sorted({k[1] for k in latest} - set(labels))
    nos = sorted({k[0] for k in latest})

    def cell(r):
        if not r:
            return '<td class="empty">아직 실행 안 함</td>'
        c = quick_checks(r["answer"])
        badges = (
            f'<span class="b {"ok" if c["질문으로 시작"] else "no"}">질문 시작</span>'
            f'<span class="b {"ok" if c["한 줄 정리"] else "no"}">한 줄 정리</span>'
            f'<span class="b {"ok" if c["줄 수"] <= 7 else "no"}">{c["줄 수"]}줄</span>'
        )
        return (
            f'<td><div class="ans">{html.escape(r["answer"])}</div>'
            f'<div class="meta">{badges}<span class="t">{r["seconds"]}초 · {html.escape(r["model"])}</span></div></td>'
        )

    body = []
    for no in nos:
        prompt = next(latest[(no, l)]["prompt"] for l in labels if (no, l) in latest)
        body.append(f'<h2>질문 {no}</h2><pre class="q">{html.escape(prompt)}</pre>')
        body.append("<table><tr>" + "".join(f"<th>{html.escape(l)}</th>" for l in labels) + "</tr><tr>")
        body.append("".join(cell(latest.get((no, l))) for l in labels))
        body.append("</tr></table>")

    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>3개 모델 비교</title><style>
body{{font-family:"Malgun Gothic",sans-serif;margin:24px;background:#f7f7f5;color:#222}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:32px}}
.q{{background:#fff;border:1px solid #ddd;padding:10px;white-space:pre-wrap;border-radius:8px}}
table{{width:100%;border-collapse:separate;border-spacing:10px 0;table-layout:fixed}}
th{{background:#1d6f5f;color:#fff;padding:8px;border-radius:8px 8px 0 0}}
td{{background:#fff;border:1px solid #ddd;vertical-align:top;padding:12px;border-radius:0 0 8px 8px}}
.ans{{white-space:pre-wrap;line-height:1.6;min-height:120px}}
.meta{{margin-top:10px;font-size:12px}} .t{{color:#888;margin-left:6px}}
.b{{display:inline-block;padding:2px 6px;border-radius:10px;margin-right:4px}}
.ok{{background:#d8f3e8;color:#16664c}} .no{{background:#f6dede;color:#8a2a2a}}
.empty{{color:#aaa;text-align:center}}
</style></head><body>
<h1>같은 질문, 3개 모델 비교</h1>
<p>만든 시각: {datetime.now():%Y-%m-%d %H:%M} · 초록 배지 = 학습 목표 형식을 지킴 (자동 확인은 참고용, 최종 판단은 사람이)</p>
{''.join(body)}
</body></html>"""
    REPORT_FILE.write_text(page, encoding="utf-8")
    print(f"✅ 비교표 완성: {REPORT_FILE}")
    if os.name == "nt":
        os.startfile(REPORT_FILE)  # 윈도우에서 브라우저로 바로 열기


def main():
    p = argparse.ArgumentParser(description="원본 / 학습본 / gpt-4.1-mini 비교")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("studio", help="Studio에 불러온 모델로 질문하기")
    s.add_argument("--label", required=True, help="원본 또는 학습본")
    s.add_argument("--model", help="모델 이름 직접 지정 (예: unsloth/Qwen2.5-3B-Instruct-unsloth-bnb-4bit)")
    sub.add_parser("openai", help="gpt-4.1-mini로 질문하기")
    sub.add_parser("report", help="비교표 만들기")
    a = p.parse_args()
    if a.cmd == "studio":
        run_studio(a.label, a.model)
    elif a.cmd == "openai":
        run_openai()
    else:
        make_report()


if __name__ == "__main__":
    main()