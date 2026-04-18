from __future__ import annotations

import argparse
from pathlib import Path

from app.ml_model import ModelTrainingError, train_model


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train Cred-ible risk model from a supported Excel or CSV dataset."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Dataset file path (absolute or relative to project root).",
    )
    args = parser.parse_args()
    dataset_path = Path(args.dataset) if args.dataset else None

    try:
        result = train_model(dataset_path=dataset_path)
    except ModelTrainingError as exc:
        raise SystemExit(f"Training failed: {exc}") from exc

    print("Model trained successfully.")
    print(f"Records used: {result.records_used}")
    print(f"Classes: {', '.join(result.classes)}")
    print(f"Metrics: {result.metrics}")
    print(f"Dataset used: {result.dataset_path}")
    print(f"Sheets fused: {', '.join(result.sheets_fused)}")
    print(f"Model artifact: {result.model_path}")
    print(f"Metrics file: {result.metrics_path}")


if __name__ == "__main__":
    main()
