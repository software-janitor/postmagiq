"""CLI for evaluation queries.

Usage:
    python -m runner.history.eval --query agent_comparison
    python -m runner.history.eval --query cost_by_agent
    python -m runner.history.eval --query quality_trend
    python -m runner.history.eval --query post_iterations --story post_03
    python -m runner.history.eval --query weekly_summary
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from runner.history.queries import HistoryQueries


def print_agent_comparison(results: list, days: int) -> None:
    """Print agent performance comparison."""
    if not results:
        print(f"No audit data found in the last {days} days.")
        return

    print(f"\nAgent Performance (last {days} days)")
    print("=" * 70)
    print(
        f"{'Agent':<12} {'Overall':>8} {'Hook':>8} {'Specifics':>10} "
        f"{'Voice':>8} {'Samples':>8}"
    )
    print("-" * 70)

    for r in results:
        print(
            f"{r.agent:<12} {r.avg_score:>8.1f} "
            f"{r.avg_hook or 0:>8.1f} {r.avg_specifics or 0:>10.1f} "
            f"{r.avg_voice or 0:>8.1f} {r.sample_size:>8}"
        )


def print_cost_breakdown(results: list) -> None:
    """Print cost breakdown by agent."""
    if not results:
        print("No invocation data found.")
        return

    total_cost = sum(r.total_cost for r in results)
    total_tokens = sum(r.total_tokens for r in results)

    print("\nCost Breakdown by Agent")
    print("=" * 70)
    print(
        f"{'Agent':<12} {'Invocations':>12} {'Tokens':>12} "
        f"{'Cost':>10} {'Avg':>10} {'%':>6}"
    )
    print("-" * 70)

    for r in results:
        pct = (r.total_cost / total_cost * 100) if total_cost > 0 else 0
        print(
            f"{r.agent:<12} {r.invocations:>12,} {r.total_tokens:>12,} "
            f"${r.total_cost:>9.2f} ${r.avg_cost:>9.4f} {pct:>5.1f}%"
        )

    print("-" * 70)
    print(f"{'TOTAL':<12} {'-':>12} {total_tokens:>12,} ${total_cost:>9.2f}")


def print_weekly_summary(results: list) -> None:
    """Print weekly summary."""
    if not results:
        print("No completed runs found.")
        return

    print("\nWeekly Summary")
    print("=" * 60)
    print(f"{'Week':<10} {'Runs':>8} {'Avg Quality':>12} {'Cost':>10} {'Tokens':>12}")
    print("-" * 60)

    for r in results:
        quality = f"{r.avg_quality:.1f}" if r.avg_quality else "-"
        print(
            f"{r.week:<10} {r.runs:>8} {quality:>12} "
            f"${r.total_cost:>9.2f} {r.total_tokens:>12,}"
        )


def print_post_iterations(results: list, story: str) -> None:
    """Print post iteration history."""
    if not results:
        print(f"No iterations found for story: {story}")
        return

    print(f"\nIteration History: {story}")
    print("=" * 80)
    print(f"{'Iter':>5} {'Run ID':<24} {'Score':>8} {'Cost':>10} {'Improvements':<25}")
    print("-" * 80)

    for r in results:
        improvements = (r.improvements or "-")[:25]
        score = f"{r.final_score:.1f}" if r.final_score else "-"
        print(
            f"{r.iteration:>5} {r.run_id:<24} {score:>8} "
            f"${r.total_cost:>9.2f} {improvements:<25}"
        )


def export_to_csv(data: list, output_path: Path, fieldnames: list[str]) -> None:
    """Export data to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in data:
            if hasattr(item, "model_dump"):
                writer.writerow(item.model_dump())
            else:
                writer.writerow(item)
    print(f"Exported to: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluation queries for workflow runs")
    parser.add_argument(
        "--query",
        required=True,
        choices=[
            "agent_comparison",
            "cost_by_agent",
            "quality_trend",
            "post_iterations",
            "weekly_summary",
            "best_agent",
        ],
        help="Query to run",
    )
    parser.add_argument("--story", help="Story name for post_iterations query")
    parser.add_argument("--state", help="State name for best_agent query")
    parser.add_argument("--days", type=int, default=30, help="Days to look back")
    parser.add_argument(
        "--weeks", type=int, default=12, help="Weeks for weekly_summary"
    )
    parser.add_argument("--export", help="Export results to CSV file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--db",
        help="Deprecated: legacy SQLite database path (ignored)",
    )

    args = parser.parse_args()

    if args.db:
        print("Warning: --db is deprecated; using DATABASE_URL", file=sys.stderr)

    queries = HistoryQueries()

    # Run requested query
    if args.query == "agent_comparison":
        results = queries.agent_performance(args.days)
        if args.json:
            print(json.dumps([r.model_dump() for r in results], indent=2))
        elif args.export:
            export_to_csv(
                results,
                Path(args.export),
                [
                    "agent",
                    "avg_score",
                    "avg_hook",
                    "avg_specifics",
                    "avg_voice",
                    "sample_size",
                ],
            )
        else:
            print_agent_comparison(results, args.days)

    elif args.query == "cost_by_agent":
        results = queries.cost_by_agent()
        if args.json:
            print(json.dumps([r.model_dump() for r in results], indent=2))
        elif args.export:
            export_to_csv(
                results,
                Path(args.export),
                ["agent", "invocations", "total_tokens", "total_cost", "avg_cost"],
            )
        else:
            print_cost_breakdown(results)

    elif args.query == "weekly_summary":
        results = queries.weekly_summary(args.weeks)
        if args.json:
            print(json.dumps([r.model_dump() for r in results], indent=2))
        elif args.export:
            export_to_csv(
                results,
                Path(args.export),
                ["week", "runs", "avg_quality", "total_cost", "total_tokens"],
            )
        else:
            print_weekly_summary(results)

    elif args.query == "post_iterations":
        if not args.story:
            print("Error: --story required for post_iterations query", file=sys.stderr)
            return 1
        results = queries.post_iterations(args.story)
        if args.json:
            print(json.dumps([r.model_dump() for r in results], indent=2))
        elif args.export:
            export_to_csv(
                results,
                Path(args.export),
                ["iteration", "run_id", "final_score", "total_cost", "improvements"],
            )
        else:
            print_post_iterations(results, args.story)

    elif args.query == "quality_trend":
        results = queries.quality_trend(args.days)
        if args.json:
            print(json.dumps(results, indent=2))
        elif args.export:
            export_to_csv(
                results, Path(args.export), ["day", "runs", "avg_score", "total_cost"]
            )
        else:
            print("\nQuality Trend (daily)")
            print("=" * 50)
            print(f"{'Day':<12} {'Runs':>6} {'Avg Score':>10} {'Cost':>10}")
            print("-" * 50)
            for r in results:
                score = f"{r['avg_score']:.1f}" if r["avg_score"] else "-"
                print(
                    f"{r['day']:<12} {r['runs']:>6} {score:>10} ${r['total_cost']:>9.2f}"
                )

    elif args.query == "best_agent":
        if not args.state:
            print("Error: --state required for best_agent query", file=sys.stderr)
            return 1
        results = queries.best_agent_for_task(args.state)
        if args.json:
            print(json.dumps([r.model_dump() for r in results], indent=2))
        else:
            print(f"\nBest Agent for {args.state}")
            print("=" * 50)
            for r in results:
                print(f"{r.agent}: {r.avg_score:.1f} (n={r.sample_size})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
