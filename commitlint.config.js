// 커밋 메시지가 팀 컨벤션(`type(scope): subject`)을 따르는지 검사합니다.
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
        [
            'feat', // 기능 추가
            'fix', // 버그 수정
            'docs', // 문서 변경
            'style', // 코드 포맷 변경
            'refactor', // 리팩토링
            'test', // 테스트 코드
            'chore', // 빌드, 설정 변경 등

            // ---- 확장 타입 ----
            'perf',         // ⚡ 성능 개선 (Performance)
            'build',        // 🏗️ 빌드 시스템 변경 (webpack, vite, gradle 등)
            'ci',           // 🤖 CI/CD 관련 수정 (GitHub Actions, Jenkins 등)
            'infra',        // 🛠️ 인프라 변경 (서버, DB, 배포 구조 등)
            'security',     // 🔒 보안 패치, 권한 변경
            'revert',       // ⏪ 이전 커밋 되돌리기
            'deps',         // 📦 의존성 추가/삭제/업데이트
            'merge',        // 🔀 브랜치 병합 커밋
            'hotfix',       // 🚑 긴급 수정
            'data',         // 🧮 데이터 관련 변경 (마이그레이션, 스키마 수정)
            'env',          // 🌐 환경 변수, .env 관련 수정
            'deploy',       // 🚀 배포 관련 설정
            'config',       // ⚙️ 환경/앱 설정 변경 (eslint, prettier 등)
        ],
    ],
    'subject-case': [0], // 대소문자 제한 없음
  },
};
