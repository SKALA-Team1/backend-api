"""
LangSmith 연동 테스트 스크립트
"""
import os
import sys

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# LangSmith 환경변수 확인
print("=" * 50)
print("LangSmith 환경변수 확인")
print("=" * 50)
print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"LANGCHAIN_API_KEY: {os.getenv('LANGCHAIN_API_KEY', '')[:20]}...")
print()

# OpenAI 직접 호출 (LangSmith 추적됨)
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

print("=" * 50)
print("GPT 호출 테스트")
print("=" * 50)

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'LangSmith test successful!' in Korean."}
    ],
    max_tokens=50
)

print(f"응답: {response.choices[0].message.content}")
print()

# LangChain을 통한 호출 (LangSmith 자동 추적)
print("=" * 50)
print("LangChain을 통한 GPT 호출")
print("=" * 50)

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0.7)

    messages = [
        SystemMessage(content="You are an English teacher for Korean IT professionals."),
        HumanMessage(content="Give me one useful phrase for a code review meeting.")
    ]

    response = llm.invoke(messages)
    print(f"LangChain 응답: {response.content}")
    print()
    print("✅ LangSmith 대시보드에서 확인하세요:")
    print("   https://smith.langchain.com")

except ImportError as e:
    print(f"LangChain 미설치: {e}")
    print("pip install langchain-openai 실행 필요")

print()
print("=" * 50)
print("테스트 완료!")
print("=" * 50)
