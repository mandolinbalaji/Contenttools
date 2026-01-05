#!/usr/bin/env python3
"""
Convert Anytune practice session files to LRC lyrics format.

This script parses Anytune's proprietary format and extracts timing markers,
converting them to the widely-supported LRC format for music players.
"""

import argparse
import json
import plistlib
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AnytuneMarker:
    """Represents a single timing marker from Anytune."""

    def __init__(self, timestamp: float, text: str):
        self.timestamp = timestamp
        self.text = text

    def to_lrc_line(self) -> str:
        """Convert marker to LRC format line: [mm:ss.xx]text"""
        minutes = int(self.timestamp // 60)
        seconds = self.timestamp % 60
        return f"[{minutes:02d}:{seconds:05.2f}]{self.text}"


class AnytuneParser:
    """Parse Anytune files and extract marker information."""

    @staticmethod
    def parse_file(filepath: Path) -> Tuple[Dict[str, str], List[AnytuneMarker]]:
        """
        Parse an Anytune file and return metadata and markers.

        Args:
            filepath: Path to the Anytune file

        Returns:
            Tuple of (metadata dict, list of AnytuneMarker objects)

        Raises:
            ValueError: If file format is invalid or unsupported
        """
        # Anytune files are typically plist or JSON depending on version
        try:
            with open(filepath, "rb") as f:
                data = plistlib.load(f)
        except Exception:
            # Try JSON format
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                raise ValueError(f"Unable to parse Anytune file: {e}") from e

        metadata = AnytuneParser._extract_metadata(data)
        markers = AnytuneParser._extract_markers(data)

        return metadata, markers

    @staticmethod
    def _extract_metadata(data: dict) -> Dict[str, str]:
        """Extract song metadata from Anytune data."""
        metadata = {}
        # Common metadata fields in Anytune files
        if "title" in data:
            metadata["ti"] = data["title"]
        if "artist" in data:
            metadata["ar"] = data["artist"]
        if "album" in data:
            metadata["al"] = data["album"]
        return metadata

    @staticmethod
    def _extract_markers(data: dict) -> List[AnytuneMarker]:
        """Extract timing markers from Anytune data."""
        markers = []
        marker_data = data.get("markers", data.get("annotations", []))

        for marker in marker_data:
            timestamp = marker.get("time", marker.get("timestamp", 0))
            text = marker.get("text", marker.get("label", ""))
            if text:  # Only include markers with text
                markers.append(AnytuneMarker(timestamp, text))

        # Sort by timestamp
        markers.sort(key=lambda m: m.timestamp)
        return markers


class LRCWriter:
    """Write LRC format files."""

    @staticmethod
    def write_lrc(
        filepath: Path,
        metadata: Dict[str, str],
        markers: List[AnytuneMarker],
        encoding: str = "utf-8",
        include_metadata: bool = True,
    ) -> None:
        """
        Write markers to LRC file.

        Args:
            filepath: Output file path
            metadata: Song metadata (artist, title, album)
            markers: List of timing markers
            encoding: File encoding
            include_metadata: Whether to include metadata header
        """
        with open(filepath, "w", encoding=encoding) as f:
            # Write metadata header
            if include_metadata:
                if "ar" in metadata:
                    f.write(f"[ar:{metadata['ar']}]\n")
                if "ti" in metadata:
                    f.write(f"[ti:{metadata['ti']}]\n")
                if "al" in metadata:
                    f.write(f"[al:{metadata['al']}]\n")
                f.write("[by:Created with AnytuneToLRC]\n")
                f.write("\n")

            # Write timing markers
            for marker in markers:
                f.write(marker.to_lrc_line() + "\n")


def main():
    """Main entry point for the converter."""
    parser = argparse.ArgumentParser(
        description="Convert Anytune files to LRC lyrics format"
    )
    parser.add_argument("input", type=Path, help="Input Anytune file")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output LRC file (default: input.lrc)"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["simple", "enhanced"],
        default="enhanced",
        help="LRC format: simple (markers only) or enhanced (with metadata)",
    )
    parser.add_argument(
        "--encoding", default="utf-8", help="Output file encoding (default: utf-8)"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    output_path = args.output or args.input.with_suffix(".lrc")

    try:
        # Parse Anytune file
        print(f"Parsing {args.input}...")
        metadata, markers = AnytuneParser.parse_file(args.input)

        if not markers:
            print("Warning: No markers found in input file", file=sys.stderr)

        # Write LRC file
        print(f"Writing {len(markers)} markers to {output_path}...")
        LRCWriter.write_lrc(
            output_path,
            metadata,
            markers,
            encoding=args.encoding,
            include_metadata=(args.format == "enhanced"),
        )

        print("Conversion complete!")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
