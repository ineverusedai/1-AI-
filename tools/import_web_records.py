"""녹화 도구가 꺼내 온 웹 페이지 기록(.json 안의 records)을 results/answers.csv, summary.csv 에 붙인다.

실행: python -m tools.import_web_records <녹화 기록 .json>
"""
import json
import sys

from common import results


def main() -> None:
    data = json.loads(open(sys.argv[1], encoding="utf-8").read())
    rec = data["records"]
    for row in rec["answers"]:
        results.log_answer(row)
    for row in rec["summary"]:
        row = dict(row)
        row["note"] = (row.get("note", "") + f"; 영상 {sys.argv[1].rsplit('/', 1)[-1].replace('.json', '.mp4')}").lstrip("; ")
        results.log_summary(row)
    print(f"results/ 에 답 {len(rec['answers'])}줄, 요약 {len(rec['summary'])}줄 추가")


if __name__ == "__main__":
    main()
