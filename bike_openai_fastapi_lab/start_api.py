"""학생이 직접 실행하는 선택 단계. 키를 파일/명령 기록에 남기지 않는다."""
import getpass
import os
import warnings
import uvicorn


def read_key():
    # 터미널이 비표시 입력을 지원하지 않으면 일반 입력으로 폴백하지 않는다.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            return getpass.getpass('본인 OpenAI API 키 (화면에 표시되지 않음, Enter=오프라인): ').strip()
        except (getpass.GetPassWarning, EOFError):
            raise SystemExit('비표시 입력을 지원하는 VS Code 터미널에서 다시 실행하세요.') from None


if __name__ == '__main__':
    if not os.environ.get('OPENAI_API_KEY'):
        key = read_key()
        if key:
            os.environ['OPENAI_API_KEY'] = key
    uvicorn.run('app:app', host='127.0.0.1', port=8000)
