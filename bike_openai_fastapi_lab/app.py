from typing import Literal
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from facts import build_facts
from generation import GenerationError, MODEL, generate_article, template_article

app = FastAPI(title='10/14 자전거 데이터 기사 실습', version='1.0.0',
              description='CSV → Python facts → OpenAI 기사. template는 AI 미호출 사전 점검입니다.')


class ArticleRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['template', 'openai'] = 'template'


@app.get('/', include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / 'index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'live_api_verified': False}


@app.post('/articles', summary='검증 facts와 기사 초안 만들기')
def articles(request: ArticleRequest):
    try:
        facts = build_facts()
    except (OSError, ValueError, KeyError):
        raise HTTPException(422, 'CSV를 읽거나 검증하지 못했습니다. 파일과 필수 열을 확인하세요.') from None
    try:
        article = template_article(facts) if request.mode == 'template' else generate_article(facts)
    except GenerationError as error:
        raise HTTPException(error.status, error.message) from None
    return {'mode': request.mode, 'ai_generated': request.mode == 'openai',
            'model': MODEL if request.mode == 'openai' else None,
            'review_required': True, 'facts': facts, 'article': article}
