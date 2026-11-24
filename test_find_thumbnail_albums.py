import unittest

from find_thumbnail_albums import find_small_images, find_thumbnail_matches


def asset(asset_id, filename, width, height):
    return {
        "id": asset_id,
        "originalFileName": filename,
        "width": width,
        "height": height,
    }


class ThumbnailMatchingTests(unittest.TestCase):
    def test_matches_suffix_thumbnail_to_unique_non_thumbnail(self):
        assets = [
            asset("thumb", "Holiday.preview.jpg", 320, 240),
            asset("original", "holiday.JPG", 3000, 2000),
        ]

        self.assertEqual(find_thumbnail_matches(assets), {"thumb": "original"})

    def test_does_not_call_ambiguous_stem_a_clear_match(self):
        assets = [
            asset("thumb", "holiday_thumb.jpg", 320, 240),
            asset("original-a", "holiday.jpg", 3000, 2000),
            asset("original-b", "holiday.png", 3000, 2000),
        ]

        self.assertEqual(find_thumbnail_matches(assets), {"thumb": None})

    def test_detects_small_dimensions_without_matching_unrelated_names(self):
        assets = [
            asset("small", "avatar.jpg", 512, 512),
            asset("unrelated", "landscape.jpg", 3000, 2000),
        ]

        self.assertEqual(find_thumbnail_matches(assets), {"small": None})

    def test_small_dimensions_can_match_same_stem_original(self):
        assets = [
            asset("small", "photo.jpg", 320, 240),
            asset("original", "photo.png", 3000, 2000),
        ]

        self.assertEqual(find_thumbnail_matches(assets), {"small": "original"})

    def test_small_image_limit_is_exclusive(self):
        assets = [
            {"id": "below", "fileSizeInByte": 999_999},
            {"id": "at-limit", "fileSizeInByte": 1_000_000},
        ]

        self.assertEqual(find_small_images(assets), {"below"})


if __name__ == "__main__":
    unittest.main()
