"""Command-line entry point for VisionTrafficAI video processing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from app.config import get_settings
from app.processor import TrafficVideoProcessor
from app.utils import configure_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command-line video and display options."""
    parser = argparse.ArgumentParser(description="Estimate traffic density and recommend adaptive signal timing.")
    parser.add_argument("--video", type=Path, help="Input video path (default: videos/traffic.mp4)")
    parser.add_argument("--display", action="store_true", help="Show live annotated video; press q to stop")
    return parser.parse_args()


def main() -> int:
    """Run the complete processing workflow with graceful error reporting."""
    arguments = parse_arguments()
    settings = get_settings()
    if arguments.display:
        settings = settings.model_copy(update={"display_window": True})
    configure_logging(settings)
    try:
        TrafficVideoProcessor(settings).process(arguments.video)
        return 0
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error("{}", exc)
        return 1
    except KeyboardInterrupt:
        logger.warning("Processing interrupted")
        return 130
    except Exception:
        logger.exception("Unexpected processing failure")
        return 1


if __name__ == "__main__":
    sys.exit(main())
