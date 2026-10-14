"""키는 학생이 세션 환경변수로만 설정한다. 이 모듈은 키를 저장하지 않는다."""
import json
import os
from openai import OpenAI, APIError, APITimeoutError, AuthenticationError, RateLimitError

DEFAULT_MODEL = 'gpt-5.4-mini-2026-03-17'
MODEL = os.environ.get('OPENAI_MODEL', DEFAULT_MODEL).strip() or DEFAULT_MODEL


class GenerationError(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


def template_article(facts: dict) -> str:
    peak = facts['hourly'][facts['peak_hours'][0]]
    return (f"[사전 점검용 고정 문장 · AI 미호출]\n"
            f"{facts['period_start']}~{facts['period_end']} 자료에서 "
            f"비운영 {facts['excluded_non_operating_rows']}행을 제외하고 계산했다. "
            f"{peak['hour']}시 평균 대여 건수는 "
            f"{peak['rental_total']:,} ÷ {peak['observations']} = "
            f"{peak['mean_rentals']:,.2f}건이다. "
            "이는 고유 이용자 수가 아니며, 시간대별 차이의 원인은 이 계산만으로 알 수 없다. "
            f"출처: UCI Seoul Bike Sharing Demand ({facts['source']})")


def generate_article(facts: dict) -> str:
    key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not key:
        raise GenerationError(503, 'OPENAI_API_KEY가 없습니다. 먼저 template로 점검하세요.')
    try:
        # 자동 재시도 없음: Execute를 다시 누르면 새 유료 요청이 될 수 있다.
        with OpenAI(api_key=key, base_url='https://api.openai.com/v1',
                    timeout=30.0, max_retries=0) as client:
            # 기본 모델은 none을 공식 지원한다. 다른 모델은 고유 기본 설정을 쓴다.
            options = {'reasoning': {'effort': 'none'}} if MODEL == DEFAULT_MODEL else {}
            response = client.responses.create(
                model=MODEL,
                instructions=(
                    '당신은 데이터 기사 작성 보조자다. 제공된 facts만 이용해 한국어 기사 초안을 작성한다. '
                    '제목 1줄과 본문 2문단, 450자 이내. 수치 계산은 하지 말고 facts의 값을 그대로 쓴다. '
                    '출처 UCI Seoul Bike Sharing Demand와 facts의 DOI를 표시한다. '
                    '기간과 비운영 제외 조건, 18시 합계·관측 수·평균을 반드시 밝힌다. '
                    '대여 건수를 이용자 수로 바꾸지 않는다. 원인, 인과관계, 현재 현황, 인터뷰를 만들지 않는다. '
                    '독자에게 관찰 결과라는 한계를 알린다.'),
                input=json.dumps(facts, ensure_ascii=False),
                max_output_tokens=700,
                store=False,
                **options,
            )
        if response.status != 'completed':
            raise GenerationError(502, '모델 응답이 완료되지 않았습니다. 출력 제한 등을 확인하세요.')
        article = response.output_text.strip()
        if not article or len(article) > 4000:
            raise GenerationError(502, '유효한 기사 본문을 받지 못했습니다.')
        return article
    except AuthenticationError:
        raise GenerationError(502, 'OpenAI 인증 실패: 본인 키와 프로젝트 권한을 확인하세요.') from None
    except RateLimitError:
        raise GenerationError(429, 'OpenAI 사용량·잔액·요청 제한을 확인하세요. 자동 재시도하지 않습니다.') from None
    except APITimeoutError:
        raise GenerationError(504, 'OpenAI 응답 대기 시간이 초과됐습니다. 재시도 전 사용 내역을 확인하세요.') from None
    except APIError:
        raise GenerationError(502, 'OpenAI 요청 실패: 네트워크와 모델 접근 권한을 확인하세요.') from None
