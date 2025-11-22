"""Tests for AnytuneToLRC converter."""

import json
import plistlib
from pathlib import Path
import pytest
from anytune_to_lrc import AnytuneMarker, AnytuneParser, LRCWriter


class TestAnytuneMarker:
    """Test AnytuneMarker class."""

    def test_to_lrc_line_simple(self):
        """Test basic LRC line formatting."""
        marker = AnytuneMarker(65.5, "Test marker")
        assert marker.to_lrc_line() == "[01:05.50]Test marker"

    def test_to_lrc_line_zero_time(self):
        """Test marker at time zero."""
        marker = AnytuneMarker(0.0, "Start")
        assert marker.to_lrc_line() == "[00:00.00]Start"

    def test_to_lrc_line_long_duration(self):
        """Test marker with long timestamp."""
        marker = AnytuneMarker(3665.25, "Long song")
        assert marker.to_lrc_line() == "[61:05.25]Long song"


class TestAnytuneParser:
    """Test AnytuneParser class."""

    def test_parse_json_format(self, tmp_path):
        """Test parsing JSON-format Anytune file."""
        test_file = tmp_path / "test.anytune"
        test_data = {
            "title": "Test Song",
            "artist": "Test Artist",
            "markers": [
                {"time": 10.5, "text": "Verse 1"},
                {"time": 30.0, "text": "Chorus"},
            ],
        }
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        metadata, markers = AnytuneParser.parse_file(test_file)

        assert metadata["ti"] == "Test Song"
        assert metadata["ar"] == "Test Artist"
        assert len(markers) == 2
        assert markers[0].timestamp == 10.5
        assert markers[0].text == "Verse 1"

    def test_parse_plist_format(self, tmp_path):
        """Test parsing plist-format Anytune file."""
        test_file = tmp_path / "test.anytune"
        test_data = {
            "title": "Test Song",
            "annotations": [
                {"timestamp": 5.0, "label": "Intro"},
            ],
        }
        with open(test_file, "wb") as f:
            plistlib.dump(test_data, f)

        metadata, markers = AnytuneParser.parse_file(test_file)

        assert metadata["ti"] == "Test Song"
        assert len(markers) == 1
        assert markers[0].timestamp == 5.0

    def test_markers_sorted_by_time(self, tmp_path):
        """Test that markers are sorted by timestamp."""
        test_file = tmp_path / "test.anytune"
        test_data = {
            "markers": [
                {"time": 30.0, "text": "Second"},
                {"time": 10.0, "text": "First"},
                {"time": 20.0, "text": "Middle"},
            ],
        }
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        _, markers = AnytuneParser.parse_file(test_file)

        assert markers[0].text == "First"
        assert markers[1].text == "Middle"
        assert markers[2].text == "Second"

    def test_empty_markers(self, tmp_path):
        """Test handling of file with no markers."""
        test_file = tmp_path / "test.anytune"
        test_data = {"title": "Test Song", "markers": []}
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        _, markers = AnytuneParser.parse_file(test_file)
        assert len(markers) == 0


class TestLRCWriter:
    """Test LRCWriter class."""

    def test_write_lrc_with_metadata(self, tmp_path):
        """Test writing LRC file with metadata."""
        output_file = tmp_path / "output.lrc"
        metadata = {"ar": "Artist", "ti": "Title", "al": "Album"}
        markers = [
            AnytuneMarker(10.0, "Line 1"),
            AnytuneMarker(20.0, "Line 2"),
        ]

        LRCWriter.write_lrc(output_file, metadata, markers, include_metadata=True)

        content = output_file.read_text(encoding="utf-8")
        assert "[ar:Artist]" in content
        assert "[ti:Title]" in content
        assert "[al:Album]" in content
        assert "[00:10.00]Line 1" in content
        assert "[00:20.00]Line 2" in content

    def test_write_lrc_simple_format(self, tmp_path):
        """Test writing LRC file without metadata."""
        output_file = tmp_path / "output.lrc"
        metadata = {"ar": "Artist", "ti": "Title"}
        markers = [AnytuneMarker(15.5, "Test")]

        LRCWriter.write_lrc(output_file, metadata, markers, include_metadata=False)

        content = output_file.read_text(encoding="utf-8")
        assert "[ar:Artist]" not in content
        assert "[ti:Title]" not in content
        assert "[00:15.50]Test" in content
