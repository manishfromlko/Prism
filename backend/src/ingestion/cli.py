import argparse

from .pipeline import IngestionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Kubeflow workspace ingestion pipeline."
    )
    parser.add_argument("--root", required=True, help="Path to the workspace root directory")
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Run mode for ingestion",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the run without persisting new ingestion state",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    pipeline = IngestionPipeline(root_path=args.root, mode=args.mode, dry_run=args.dry_run)
    pipeline.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
