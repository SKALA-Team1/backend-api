---
name: ✨ Feature Request
about: 새로운 기능을 제안합니다.
title: "feat: [요약된 기능명]"
labels: enhancement
assignees: ''
---

## 🧩 개요
무엇을 구현하려는 기능인가요?

## 🎯 목표
이 기능이 해결하려는 문제나 기대 효과를 간단히 적어주세요.

## ✅ 작업 항목
- [ ] 작업 1
- [ ] 작업 2

---

## 🌿 브랜치 생성 규칙
이 이슈를 처리하기 위해 새로운 브랜치를 생성할 때는 아래 규칙을 따르세요.

```bash
# 형식
feature/{이슈번호}-{작업명}

# 예시
feature/45-add-login
feature/102-update-user-profile
```
> ⚠️ 브랜치는 항상 `develop` 브랜치에서 분기하세요.
> ```
> git checkout develop
> git pull origin develop
> git checkout -b fix/{이슈번호}-{버그요약}
> ```
