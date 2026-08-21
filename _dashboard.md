# 볼트 상태판

> 임계값은 Wiki.md의 "임계값 정본" 절에 있다. 이 문서는 정렬만 한다.

## 처리 대기 — /ingest 돌리면 해소
```dataview
TABLE WITHOUT ID length(rows) AS "raw 대기"
FROM "BellFollow/RAW" WHERE status = "raw" GROUP BY true
```

## 안 읽은 수집 자료 — 오래된 순
```dataview
TABLE captured, (date(today) - date(captured)).days AS 경과일
FROM "BellFollow/RAW" WHERE status = "inbox" SORT captured ASC
```

## 미해결 의문 — 오래된 순
```dataview
TABLE file.folder AS 카테고리, updated, (date(today) - date(updated)).days AS 방치일
FROM "BellFollow/Wiki" WHERE status = "open" SORT updated ASC
```

## 폐기 대기
```dataview
TABLE WITHOUT ID length(rows) AS "Trash 건수"
FROM "BellFollow/Trash" GROUP BY true
```
