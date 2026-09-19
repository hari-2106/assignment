"""CLI entrypoint: run the agent end to end against data/accounts_to_score.csv.

    python agent/run.py

Writes agent/output/worklist.csv and monitoring/latest_report.json.
"""

from __future__ import annotations

from agent.graph import build_graph


def main() -> None:
    app = build_graph()
    result = app.invoke({})

    if result.get("abort_reason"):
        print(f"Run aborted: {result['abort_reason']}")
        return

    worklist = result["worklist"]
    print(f"Scored {len(worklist)} accounts")
    print(worklist["tier"].value_counts().to_string())
    print()
    print(f"Accounts needing manual review: {int(worklist['needs_review'].sum())}")
    print(f"Outreach drafts generated: {len(result.get('drafts', {}))}")
    print()
    print("Monitoring report:")
    for check_name, check_result in result["monitoring_report"].items():
        if isinstance(check_result, dict) and "status" in check_result:
            print(f"  {check_name}: {check_result['status']}")
        else:
            print(f"  {check_name}: {check_result}")
    print()
    print(f"Worklist written to agent/output/worklist.csv")
    print(f"Monitoring report written to monitoring/latest_report.json")


if __name__ == "__main__":
    main()
