---
name: 🐞 Bug Report
about: 발견된 버그를 보고합니다.
title: "fix: [버그 요약]"
labels: bug
assignees: ''
---

## ⚠️ 버그 내용
무슨 문제가 발생했나요?

## 🧩 재현 단계
1. 
2. 
3. 

## ✅ 기대 동작
어떤 결과가 나와야 했나요?

---

## 🌿 브랜치 생성 규칙
이 버그를 수정하기 위해 브랜치를 생성할 때는 아래 규칙을 따르세요.

**형식**
```
fix/{이슈번호}-{버그요약}
```
**예시**
```
fix/87-login-token-error
fix/91-image-upload-404
```

> ⚠️ 브랜치는 항상 `develop` 브랜치에서 분기하세요.
> ```
> git checkout develop
> git pull origin develop
> git checkout -b fix/{이슈번호}-{버그요약}
> ```
