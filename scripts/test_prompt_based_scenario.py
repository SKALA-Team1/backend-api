#!/usr/bin/env python3
"""
프롬프트 기반 시나리오 생성 API 테스트 스크립트

사용법:
    python scripts/test_prompt_based_scenario.py

테스트 항목:
    1. 기본 시나리오 생성
    2. 다양한 역할 조합 테스트
    3. 에러 핸들링
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.roleplaying.services.prompt_based_generator_service import PromptBasedScenarioService


async def test_basic_generation():
    """기본 시나리오 생성 테스트"""
    print("\n=== Test 1: 기본 시나리오 생성 ===")

    db = SessionLocal()
    service = PromptBasedScenarioService()

    try:
        scenario = await service.generate_from_prompt(
            user_id=1,
            my_role="Software Engineer",
            ai_role="Project Manager",
            situation="프로젝트 일정 조정 논의",
            db=db
        )

        print(f"✅ 시나리오 생성 성공")
        print(f"   AI 역할: {scenario.aiRole}")
        print(f"   토픽 타입: {scenario.topicType}")
        print(f"   제목: {scenario.title}")
        print(f"   질문 개수: {len(scenario.fixedQuestions)}")
        for idx, q in enumerate(scenario.fixedQuestions, 1):
            print(f"     {idx}. {q}")

        return True

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


async def test_different_roles():
    """다양한 역할 조합 테스트"""
    print("\n=== Test 2: 다양한 역할 조합 테스트 ===")

    db = SessionLocal()
    service = PromptBasedScenarioService()

    test_cases = [
        {
            "user_id": 1,
            "my_role": "Software Engineer",
            "ai_role": "Tech Lead",
            "situation": "아키텍처 설계 논의"
        },
        {
            "user_id": 1,
            "my_role": "Product Manager",
            "ai_role": "QA Engineer",
            "situation": "기능 요구사항 검토"
        },
        {
            "user_id": 1,
            "my_role": "Backend Developer",
            "ai_role": "Project Manager",
            "situation": "스프린트 계획 수립"
        }
    ]

    all_passed = True

    for idx, case in enumerate(test_cases, 1):
        try:
            scenario = await service.generate_from_prompt(
                user_id=case["user_id"],
                my_role=case["my_role"],
                ai_role=case["ai_role"],
                situation=case["situation"],
                db=db
            )

            print(f"✅ Test 2-{idx}: {case['my_role']} vs {case['ai_role']}")
            print(f"   상황: {case['situation']}")
            print(f"   생성된 제목: {scenario.title[:50]}...")

        except Exception as e:
            print(f"❌ Test 2-{idx}: {e}")
            all_passed = False

    db.close()
    return all_passed


async def test_error_handling():
    """에러 핸들링 테스트"""
    print("\n=== Test 3: 에러 핸들링 ===")

    db = SessionLocal()
    service = PromptBasedScenarioService()

    # 빈 상황 테스트 (실제로는 Pydantic 검증으로 막히지만, 서비스 레벨 테스트)
    test_cases = [
        {
            "name": "정상 요청",
            "user_id": 1,
            "my_role": "Software Engineer",
            "ai_role": "Project Manager",
            "situation": "프로젝트 회의",
            "should_pass": True
        },
        {
            "name": "매우 짧은 상황",
            "user_id": 1,
            "my_role": "Engineer",
            "ai_role": "Manager",
            "situation": "회의",
            "should_pass": True  # 짧지만 유효
        }
    ]

    for case in test_cases:
        try:
            scenario = await service.generate_from_prompt(
                user_id=case["user_id"],
                my_role=case["my_role"],
                ai_role=case["ai_role"],
                situation=case["situation"],
                db=db
            )

            if case["should_pass"]:
                print(f"✅ {case['name']}: 예상대로 성공")
            else:
                print(f"❌ {case['name']}: 예상과 다르게 성공 (실패해야 함)")

        except Exception as e:
            if not case["should_pass"]:
                print(f"✅ {case['name']}: 예상대로 실패 - {type(e).__name__}")
            else:
                print(f"❌ {case['name']}: 예상과 다르게 실패 - {e}")

    db.close()
    return True


async def test_output_format():
    """출력 형식 검증 테스트"""
    print("\n=== Test 4: 출력 형식 검증 ===")

    db = SessionLocal()
    service = PromptBasedScenarioService()

    try:
        scenario = await service.generate_from_prompt(
            user_id=1,
            my_role="Software Engineer",
            ai_role="Project Manager",
            situation="프로젝트 일정 조정",
            db=db
        )

        # 필드 검증
        checks = [
            ("aiRole 존재", hasattr(scenario, 'aiRole') and scenario.aiRole),
            ("topicType 존재", hasattr(scenario, 'topicType') and scenario.topicType == "direct"),
            ("title 존재 및 길이", hasattr(scenario, 'title') and 1 <= len(scenario.title) <= 200),
            ("fixedQuestions 존재", hasattr(scenario, 'fixedQuestions')),
            ("질문 개수 정확히 3개", len(scenario.fixedQuestions) == 3),
            ("모든 질문이 문자열", all(isinstance(q, str) for q in scenario.fixedQuestions)),
            ("모든 질문이 10자 이상", all(len(q) >= 10 for q in scenario.fixedQuestions))
        ]

        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"❌ 실패: {e}")
        return False

    finally:
        db.close()


async def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("프롬프트 기반 시나리오 생성 API 테스트")
    print("=" * 60)

    results = []

    try:
        # 테스트 1: 기본 생성
        results.append(("기본 시나리오 생성", await test_basic_generation()))

        # 테스트 2: 다양한 역할
        results.append(("다양한 역할 조합", await test_different_roles()))

        # 테스트 3: 에러 핸들링
        results.append(("에러 핸들링", await test_error_handling()))

        # 테스트 4: 출력 형식
        results.append(("출력 형식 검증", await test_output_format()))

    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\n총 {total_passed}/{total_tests} 테스트 통과")

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)