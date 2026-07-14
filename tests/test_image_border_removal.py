import os  # Provide filesystem metadata and path operations for observable rewrite assertions.
import sys  # Provide access to imported scraper modules for logger resource cleanup.
import tempfile  # Provide isolated temporary directories for deterministic image fixtures.
import unittest  # Provide the repository-independent standard-library test framework.
from argparse import Namespace  # Provide a minimal argument object for merge-path integration validation.
from datetime import datetime  # Provide a start timestamp for merge-path integration validation.
from pathlib import Path  # Provide readable path construction for temporary fixtures.
from unittest.mock import patch  # Provide controlled save failures and traversal call observation.

from PIL import Image, ImageDraw  # Provide deterministic raster fixture generation and metadata inspection.

import main  # Import the production border-removal functions under test.


def tearDownModule() -> None:  # Close import-time logger resources after this test module completes.
    """
    Close logger files opened by production module imports during the test run.

    :return: None.
    """

    for module_name in ("AliExpress", "Amazon", "Gemini", "MercadoLivre", "Shein", "Shopee", "main"):  # Iterate modules that construct logger instances during import.
        imported_module = sys.modules.get(module_name)  # Resolve the already imported module without triggering another import.
        imported_logger = getattr(imported_module, "logger", None) if imported_module else None  # Resolve the module logger when one exists.

        if imported_logger is not None:  # Close only logger resources created by an imported production module.
            imported_logger.close()  # Release the logger file descriptor after all tests and assertions complete.


def create_bordered_image(image_path: Path, size: tuple[int, int], borders: tuple[int, int, int, int], image_mode: str = "RGB", border_color: tuple[int, ...] = (255, 255, 255), content_color: tuple[int, ...] = (30, 60, 90)) -> None:  # Build a deterministic bordered raster fixture.
    """
    Create a deterministic image with independently sized solid edge borders.

    :param image_path: Destination path for the generated image fixture.
    :param size: Width and height of the generated image.
    :param borders: Left, top, right, and bottom border widths.
    :param image_mode: Pillow mode used for the generated image.
    :param border_color: Pixel value used for edge border regions.
    :param content_color: Pixel value used for interior image content.
    :return: None.
    """

    width, height = size  # Unpack fixture dimensions for the interior rectangle calculation.
    left, top, right, bottom = borders  # Unpack independent edge border widths.
    image = Image.new(image_mode, size, border_color)  # Initialize the complete fixture with the requested border color.
    drawing = ImageDraw.Draw(image)  # Create a drawing context for the non-white image content.
    drawing.rectangle((left, top, width - right - 1, height - bottom - 1), fill=content_color)  # Fill the interior through its inclusive final pixel coordinates.
    image.save(image_path)  # Persist the deterministic fixture in the format selected by its path.
    image.close()  # Release fixture pixel resources after saving.


class ImageBorderRemovalTests(unittest.TestCase):  # Validate conservative detection, preservation, replacement, and traversal behavior.
    def setUp(self) -> None:  # Create an isolated directory before each test method.
        self.temporary_directory = tempfile.TemporaryDirectory()  # Allocate an isolated filesystem location for the current test.
        self.directory = Path(self.temporary_directory.name)  # Expose the temporary directory through convenient path operations.

    def tearDown(self) -> None:  # Remove the isolated directory after each test method.
        self.temporary_directory.cleanup()  # Delete every fixture and temporary artifact produced by the current test.

    def test_left_and_right_borders_are_cropped(self) -> None:  # Validate symmetric horizontal border removal.
        image_path = self.directory / "two-sides.png"  # Define the PNG fixture path.
        create_bordered_image(image_path, (100, 80), (4, 0, 4, 0))  # Create narrow solid-white strips on left and right edges.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Apply production border removal to the final image path.

        with Image.open(image_path) as result_image:  # Open the committed replacement for dimension validation.
            self.assertTrue(changed)  # Require an observable replacement for the valid border fixture.
            self.assertEqual((92, 80), result_image.size)  # Require removal of only the two four-pixel horizontal strips.

    def test_full_white_background_is_unchanged(self) -> None:  # Validate preservation of a legitimate full white background.
        image_path = self.directory / "white-background.png"  # Define the full-white fixture path.
        image = Image.new("RGB", (100, 80), (255, 255, 255))  # Create a legitimate image whose background reaches every edge.
        image.save(image_path)  # Persist the full-white image fixture.
        image.close()  # Release fixture pixel resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact source bytes to detect any unnecessary rewrite.
        original_timestamp = os.stat(image_path).st_mtime_ns  # Capture nanosecond modification time before processing.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the legitimate white-background fixture.

        self.assertFalse(changed)  # Require rejection of a white region that continues through the full image.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require byte-for-byte preservation when no border is valid.
        self.assertEqual(original_timestamp, os.stat(image_path).st_mtime_ns)  # Require preservation of file modification time without rewriting.

    def test_product_on_white_background_is_unchanged(self) -> None:  # Validate preservation of natural white margins around central image content.
        image_path = self.directory / "product-white-background.png"  # Define the product-on-white fixture path.
        image = Image.new("RGB", (100, 80), (255, 255, 255))  # Create a legitimate white photographic background reaching every edge.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for representative central product content.
        drawing.ellipse((25, 10, 74, 69), fill=(25, 55, 85))  # Draw a centered non-white product surrounded by natural white background.
        image.save(image_path)  # Persist the representative product photograph fixture.
        image.close()  # Release fixture pixel resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact source bytes before conservative analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze natural white margins through the production path.

        self.assertFalse(changed)  # Require rejection of white margins that are too large to be artificial borders.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact preservation of the legitimate white-background image.

    def test_narrow_natural_white_margin_is_unchanged(self) -> None:  # Validate conservative rejection of a border-like photographic background margin.
        image_path = self.directory / "narrow-white-background.png"  # Define the narrow natural-margin fixture path.
        image = Image.new("RGB", (100, 80), (255, 255, 255))  # Create a legitimate white photographic background reaching all edges.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for a product that nearly fills the frame.
        drawing.rectangle((4, 10, 99, 69), fill=(25, 55, 85))  # Leave a narrow left margin while retaining natural white background above and below the product.
        image.save(image_path)  # Persist the ambiguous narrow-margin product photograph fixture.
        image.close()  # Release fixture pixel resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact source bytes before conservative analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the border-like natural white margin through production logic.

        self.assertFalse(changed)  # Require rejection because the adjacent band still contains meaningful white background.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact preservation of the legitimate narrow white margin.

    def test_non_white_edges_are_unchanged(self) -> None:  # Validate no-op behavior for an image without white borders.
        image_path = self.directory / "no-border.png"  # Define the non-white fixture path.
        create_bordered_image(image_path, (100, 80), (0, 0, 0, 0))  # Create content that reaches all four edges.
        original_bytes = image_path.read_bytes()  # Capture exact bytes before border analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze an image with no eligible edge strip.

        self.assertFalse(changed)  # Require a no-op result when no border exists.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact byte preservation without re-encoding.

    def test_one_edge_is_cropped_independently(self) -> None:  # Validate independent detection without an opposite border.
        image_path = self.directory / "left-only.png"  # Define the one-edge fixture path.
        create_bordered_image(image_path, (100, 80), (4, 0, 0, 0))  # Create a valid border on only the left edge.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Apply production border removal.

        with Image.open(image_path) as result_image:  # Open the committed replacement for size validation.
            self.assertTrue(changed)  # Require detection of the isolated left border.
            self.assertEqual((96, 80), result_image.size)  # Require cropping only the four-pixel left edge.

    def test_asymmetric_four_edge_borders_are_cropped(self) -> None:  # Validate independent asymmetric edge widths.
        image_path = self.directory / "asymmetric.png"  # Define the asymmetric fixture path.
        create_bordered_image(image_path, (120, 100), (2, 3, 5, 4))  # Create distinct valid widths on every edge.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Apply production border removal.

        with Image.open(image_path) as result_image:  # Open the committed replacement for dimension validation.
            self.assertTrue(changed)  # Require detection of all four valid asymmetric strips.
            self.assertEqual((113, 93), result_image.size)  # Require removal of exactly the requested independent widths.

    def test_near_white_jpeg_border_is_detected(self) -> None:  # Validate threshold tolerance for JPEG compression artifacts.
        image_path = self.directory / "near-white.jpg"  # Define the JPEG fixture path.
        source_image = Image.new("RGB", (120, 90), (250, 250, 250))  # Initialize near-white border pixels below exact white.
        source_drawing = ImageDraw.Draw(source_image)  # Create a drawing context for clear non-white interior content.
        source_drawing.rectangle((5, 0, 114, 89), fill=(25, 55, 85))  # Leave five-pixel near-white strips on both horizontal edges.
        source_image.save(image_path, quality=85, subsampling=0)  # Encode JPEG artifacts while retaining a clear border-to-content transition.
        source_image.close()  # Release source JPEG fixture resources.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Apply threshold-based production border detection.

        with Image.open(image_path) as result_image:  # Open the committed JPEG replacement for size validation.
            self.assertTrue(changed)  # Require near-white JPEG border detection despite lossy compression.
            self.assertLess(result_image.width, 120)  # Require removal of at least one compressed near-white edge strip.
            self.assertEqual(90, result_image.height)  # Require vertical content dimensions to remain unchanged.

    def test_supported_static_raster_formats_preserve_format(self) -> None:  # Validate every eligible static Pillow format used by final traversal.
        format_cases = (("png", "PNG"), ("jpg", "JPEG"), ("jpeg", "JPEG"), ("webp", "WEBP"), ("bmp", "BMP"), ("tif", "TIFF"), ("tiff", "TIFF"), ("gif", "GIF"), ("avif", "AVIF"))  # Define eligible extensions and their expected Pillow format names.

        for extension, expected_format in format_cases:  # Exercise each eligible static raster format independently.
            with self.subTest(extension=extension):  # Report any format-specific failure with its extension context.
                image_path = self.directory / f"supported-{extension}.{extension}"  # Define a unique fixture path for the current format.
                create_bordered_image(image_path, (120, 90), (5, 0, 0, 0))  # Create a narrow left border with clear non-white content.

                changed = main.remove_small_white_border_from_image(str(image_path))  # Apply production detection and format-specific replacement.

                with Image.open(image_path) as result_image:  # Open the committed replacement for format and size validation.
                    self.assertTrue(changed)  # Require the valid border to be removed for every eligible static format.
                    self.assertEqual(expected_format, result_image.format)  # Require preservation of the source raster format.
                    self.assertLess(result_image.width, 120)  # Require removal of the detected left border.
                    self.assertEqual(90, result_image.height)  # Require preservation of the unaffected image axis.

    def test_large_white_region_is_rejected(self) -> None:  # Validate maximum border width safeguards.
        image_path = self.directory / "large-margin.png"  # Define the large-margin fixture path.
        create_bordered_image(image_path, (100, 80), (12, 0, 0, 0))  # Create a white edge region exceeding the pixel fraction limit.
        original_bytes = image_path.read_bytes()  # Capture exact bytes before analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the oversized white region.

        self.assertFalse(changed)  # Require rejection of the region as larger than a small border.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require no rewrite after oversized-region rejection.

    def test_border_without_strong_transition_is_rejected(self) -> None:  # Validate adjacent interior whiteness safeguards.
        image_path = self.directory / "weak-transition.png"  # Define the weak-transition fixture path.
        image = Image.new("RGB", (100, 80), (25, 55, 85))  # Initialize clearly non-white content beyond the transition band.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for edge and transition regions.
        drawing.rectangle((0, 0, 3, 79), fill=(255, 255, 255))  # Create a four-pixel qualifying white edge candidate.
        drawing.rectangle((4, 0, 9, 59), fill=(255, 255, 255))  # Keep seventy-five percent of the adjacent transition band white.
        image.save(image_path)  # Persist the weak-transition fixture.
        image.close()  # Release fixture resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact bytes before conservative analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze a candidate followed by predominantly white content.

        self.assertFalse(changed)  # Require rejection when the immediately adjacent interior remains mostly white.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require no rewrite after transition rejection.

    def test_internal_white_region_is_unchanged(self) -> None:  # Validate that only edge-touching regions can be cropped.
        image_path = self.directory / "internal-white.png"  # Define the internal-region fixture path.
        image = Image.new("RGB", (100, 80), (25, 55, 85))  # Initialize non-white pixels on all four image edges.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for an internal white region.
        drawing.rectangle((20, 15, 79, 64), fill=(255, 255, 255))  # Add a large white area that touches no image edge.
        image.save(image_path)  # Persist the internal-white fixture.
        image.close()  # Release fixture resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact bytes before edge analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the image for edge-connected candidates.

        self.assertFalse(changed)  # Require a no-op because the white area is entirely internal.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact source preservation without rewriting.

    def test_repeated_processing_is_idempotent(self) -> None:  # Validate that a second execution cannot shrink a valid result further.
        image_path = self.directory / "idempotent.png"  # Define the idempotency fixture path.
        create_bordered_image(image_path, (100, 80), (4, 3, 0, 0))  # Create two valid independent edge borders.

        first_changed = main.remove_small_white_border_from_image(str(image_path))  # Apply the first valid border removal.
        first_result_bytes = image_path.read_bytes()  # Capture exact committed bytes after the first transformation.
        second_changed = main.remove_small_white_border_from_image(str(image_path))  # Apply the same operation to the already cropped result.

        self.assertTrue(first_changed)  # Require the first execution to remove the valid borders.
        self.assertFalse(second_changed)  # Require the second execution to detect no remaining valid border.
        self.assertEqual(first_result_bytes, image_path.read_bytes())  # Require the second execution to avoid any re-encoding or shrinkage.

    def test_tiny_image_cannot_produce_invalid_dimensions(self) -> None:  # Validate conservative handling for dimensions below the analysis minimum.
        image_path = self.directory / "tiny.png"  # Define the tiny fixture path.
        create_bordered_image(image_path, (7, 7), (2, 2, 2, 2))  # Create a tiny image whose borders could consume most dimensions.
        original_bytes = image_path.read_bytes()  # Capture exact tiny-image bytes before processing.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the tiny image through the production entry point.

        with Image.open(image_path) as result_image:  # Open the preserved tiny fixture for dimension validation.
            self.assertFalse(changed)  # Require rejection because reliable transition analysis is impossible.
            self.assertEqual((7, 7), result_image.size)  # Require preservation of valid non-zero dimensions.
            self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact byte preservation for the rejected tiny image.

    def test_unsupported_file_is_ignored(self) -> None:  # Validate extension filtering for unexpected final-output files.
        unsupported_path = self.directory / "vector.svg"  # Define an unsupported vector path.
        unsupported_path.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>", encoding="utf-8")  # Persist deterministic unsupported content.

        eligible = main.is_border_removal_image_file(str(unsupported_path))  # Classify the unsupported final-output file.
        cropped_count = main.remove_small_white_borders_from_final_output(str(self.directory))  # Traverse the directory containing only the unsupported file.

        self.assertFalse(eligible)  # Require the unsupported vector extension to be ineligible.
        self.assertEqual(0, cropped_count)  # Require traversal to ignore unsupported content without failure.

    def test_corrupted_image_preserves_original_bytes(self) -> None:  # Validate per-image error isolation for unreadable raster files.
        image_path = self.directory / "corrupt.png"  # Define a corrupt file with an otherwise eligible extension.
        image_path.write_bytes(b"not-a-valid-png")  # Persist deterministic invalid image bytes.
        original_bytes = image_path.read_bytes()  # Capture original corrupt bytes before processing.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Attempt production processing on the corrupt raster path.

        self.assertFalse(changed)  # Require failure containment without claiming a committed crop.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require the unreadable original file to remain intact.

    def test_save_failure_preserves_original_and_removes_temporary_file(self) -> None:  # Validate safe replacement failure handling.
        image_path = self.directory / "save-failure.png"  # Define a valid bordered fixture path.
        create_bordered_image(image_path, (100, 80), (4, 0, 0, 0))  # Create a fixture that reaches the replacement save stage.
        original_bytes = image_path.read_bytes()  # Capture exact original bytes before the injected failure.

        with patch.object(Image.Image, "save", side_effect=OSError("injected save failure")):  # Inject a deterministic encoder failure after border detection.
            changed = main.remove_small_white_border_from_image(str(image_path))  # Attempt the production replacement under the injected failure.

        remaining_names = sorted(path.name for path in self.directory.iterdir())  # Enumerate remaining files after failure cleanup.
        self.assertFalse(changed)  # Require failure reporting without a committed replacement.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require the original image bytes to remain intact.
        self.assertEqual(["save-failure.png"], remaining_names)  # Require cleanup of every temporary replacement artifact.

    def test_atomic_replace_failure_preserves_original_and_removes_temporary_file(self) -> None:  # Validate cleanup after a committed-file replacement failure.
        image_path = self.directory / "replace-failure.png"  # Define a valid bordered fixture path.
        create_bordered_image(image_path, (100, 80), (4, 0, 0, 0))  # Create a fixture that reaches the atomic replacement stage.
        original_bytes = image_path.read_bytes()  # Capture exact original bytes before the injected failure.

        with patch.object(main.os, "replace", side_effect=OSError("injected replace failure")):  # Inject a deterministic atomic replacement failure.
            changed = main.remove_small_white_border_from_image(str(image_path))  # Attempt production replacement after a valid temporary save.

        remaining_names = sorted(path.name for path in self.directory.iterdir())  # Enumerate remaining files after replacement failure cleanup.
        self.assertFalse(changed)  # Require failure reporting without a committed replacement.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require the original image bytes to remain intact.
        self.assertEqual(["replace-failure.png"], remaining_names)  # Require cleanup of the validated but uncommitted temporary replacement.

    def test_metadata_mode_and_orientation_are_preserved(self) -> None:  # Validate relevant JPEG metadata and encoded orientation preservation.
        image_path = self.directory / "metadata.jpg"  # Define the metadata-bearing JPEG fixture path.
        image = Image.new("RGB", (100, 80), (255, 255, 255))  # Initialize a white canvas for a valid left border.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for non-white content.
        drawing.rectangle((4, 0, 99, 79), fill=(25, 55, 85))  # Create a four-pixel white left border with a strong transition.
        exif_data = Image.Exif()  # Create EXIF metadata for orientation preservation validation.
        exif_data[274] = 6  # Store a non-default EXIF orientation without transposing source pixels.
        image.save(image_path, quality=90, subsampling=0, exif=exif_data, icc_profile=b"test-icc-profile", dpi=(144, 144))  # Persist JPEG metadata and encoder characteristics.
        image.close()  # Release metadata fixture resources after saving.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Apply the production crop without EXIF transposition.

        with Image.open(image_path) as result_image:  # Open the committed replacement for metadata validation.
            self.assertTrue(changed)  # Require the valid left border to be removed.
            self.assertEqual((96, 80), result_image.size)  # Require cropping in encoded pixel coordinates without unexpected rotation.
            self.assertEqual("RGB", result_image.mode)  # Require preservation of the source image mode.
            self.assertEqual("JPEG", result_image.format)  # Require preservation of the source image format.
            self.assertEqual(6, result_image.getexif().get(274))  # Require preservation of the existing EXIF orientation tag.
            self.assertEqual(b"test-icc-profile", result_image.info.get("icc_profile"))  # Require preservation of the embedded ICC profile bytes.
            self.assertAlmostEqual(144.0, result_image.info.get("dpi", (0.0, 0.0))[0], delta=1.0)  # Require preservation of horizontal DPI within JPEG resolution precision.

    def test_transparent_edge_is_not_treated_as_white(self) -> None:  # Validate alpha-aware exclusion of transparent pixels.
        image_path = self.directory / "transparent-edge.png"  # Define the transparent-edge PNG fixture path.
        image = Image.new("RGBA", (100, 80), (25, 55, 85, 255))  # Initialize fully opaque non-white image content.
        drawing = ImageDraw.Draw(image)  # Create a drawing context for a transparent edge strip.
        drawing.rectangle((0, 0, 3, 79), fill=(255, 255, 255, 0))  # Add transparent pixels whose RGB channels are white.
        image.save(image_path)  # Persist the alpha-bearing fixture.
        image.close()  # Release fixture resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact source bytes before analysis.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the transparent edge through the production path.

        self.assertFalse(changed)  # Require transparent pixels to remain distinct from opaque white borders.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact preservation when no opaque white border is valid.

    def test_animated_image_is_not_reencoded(self) -> None:  # Validate animation preservation through conservative exclusion.
        image_path = self.directory / "animated.gif"  # Define the animated GIF fixture path.
        first_frame = Image.new("RGB", (40, 40), (255, 255, 255))  # Create the first animation frame.
        first_drawing = ImageDraw.Draw(first_frame)  # Create a drawing context for first-frame content.
        first_drawing.rectangle((2, 0, 39, 39), fill=(25, 55, 85))  # Add a valid-looking white border to the first frame.
        second_frame = Image.new("RGB", (40, 40), (85, 55, 25))  # Create a distinct second animation frame.
        first_frame.save(image_path, save_all=True, append_images=[second_frame], duration=100, loop=0)  # Persist the deterministic two-frame GIF animation.
        first_frame.close()  # Release first-frame resources after saving.
        second_frame.close()  # Release second-frame resources after saving.
        original_bytes = image_path.read_bytes()  # Capture exact animation bytes before processing.

        changed = main.remove_small_white_border_from_image(str(image_path))  # Analyze the animated image through the production path.

        self.assertFalse(changed)  # Require exclusion of animated files from single-frame cropping.
        self.assertEqual(original_bytes, image_path.read_bytes())  # Require exact animation preservation without re-encoding.

    def test_final_output_traversal_processes_each_eligible_path_once(self) -> None:  # Validate deterministic recursive traversal and reserved-file exclusion.
        product_directory = self.directory / "product"  # Define a representative finalized product directory.
        nested_directory = product_directory / "Product Data" / "images"  # Define a nested final asset directory after restructuring.
        nested_directory.mkdir(parents=True)  # Create the representative final output hierarchy.
        first_path = product_directory / "01.png"  # Define a root final image path.
        second_path = nested_directory / "02.jpg"  # Define a nested final image path.
        temporary_path = nested_directory / f"{main.BORDER_TEMPORARY_FILE_PREFIX}stale.png"  # Define a reserved temporary-style image path.
        create_bordered_image(first_path, (40, 40), (0, 0, 0, 0))  # Create the first eligible image without a border.
        create_bordered_image(second_path, (40, 40), (0, 0, 0, 0))  # Create the second eligible image without a border.
        create_bordered_image(temporary_path, (40, 40), (2, 0, 0, 0))  # Create a reserved temporary-style file that traversal must ignore.
        unsupported_path = nested_directory / "notes.txt"  # Define an unexpected non-image final-output file.
        unsupported_path.write_text("metadata", encoding="utf-8")  # Persist deterministic unsupported content.

        with patch.object(main, "remove_small_white_border_from_image", wraps=main.remove_small_white_border_from_image) as observed_removal:  # Observe production calls while retaining real behavior.
            cropped_count = main.remove_small_white_borders_from_final_output(str(self.directory))  # Traverse the representative final output exactly once.

        observed_paths = sorted(call.args[0] for call in observed_removal.call_args_list)  # Collect image paths received by the per-image production function.
        self.assertEqual(0, cropped_count)  # Require no crops because both eligible images have non-white edges.
        self.assertEqual(2, observed_removal.call_count)  # Require one call for each eligible final image and no duplicate calls.
        self.assertEqual(sorted([str(first_path), str(second_path)]), observed_paths)  # Require traversal of only the two intended final image paths.

    def test_restructure_integration_runs_border_removal_after_all_products(self) -> None:  # Validate terminal ordering for normal, sorting-only, and standalone restructure paths.
        output_directory = self.directory / "final-run"  # Define a representative final run directory.
        first_product = output_directory / "01. Product A"  # Define the first finalized product directory.
        second_product = output_directory / "02. Product B"  # Define the second finalized product directory.
        first_product.mkdir(parents=True)  # Create the first product directory and final run parent.
        second_product.mkdir()  # Create the second product directory in the same final run.
        context = {"timestamped_output_dir_for_sorting": None, "timestamped_output_dir": str(output_directory)}  # Build the real restructuring context shape.
        events: list[str] = []  # Track observable ordering of product restructuring and border traversal.

        def record_restructure(product_directory: str) -> None:  # Record one product restructure invocation without mutating fixtures.
            """
            Record a product restructuring event for integration ordering validation.

            :param product_directory: Product directory passed by the production integration function.
            :return: None.
            """

            events.append(f"restructure:{Path(product_directory).name}")  # Record the product name in production traversal order.

        def record_border_removal(final_output_directory: str) -> int:  # Record the terminal border traversal invocation.
            """
            Record a final-output border removal event for integration ordering validation.

            :param final_output_directory: Final run directory passed by the production integration function.
            :return: Zero because this integration test does not process fixture pixels.
            """

            events.append(f"borders:{Path(final_output_directory).name}")  # Record the terminal pass and its final run target.

            return 0  # Return a valid crop count to preserve the production function contract.

        with patch.object(main, "restructure_single_product_output_directory", side_effect=record_restructure):  # Observe every product restructuring call through the real orchestration function.
            with patch.object(main, "remove_small_white_borders_from_final_output", side_effect=record_border_removal):  # Observe the terminal border pass through its real integration point.
                main.restructure_product_outputs_before_finalize(context)  # Execute the production restructuring and border-removal orchestration.

        self.assertEqual(["restructure:01. Product A", "restructure:02. Product B", "borders:final-run"], events)  # Require border removal only after all product mutations finish.

    def test_merge_integration_runs_border_removal_after_normalization(self) -> None:  # Validate terminal ordering for the merge-only execution path.
        merged_directory = self.directory / "merged-run"  # Define a representative merged final output directory.
        merged_directory.mkdir()  # Create the merged directory required by the production validity guard.
        arguments = Namespace(merge_output_dirs=True)  # Build the exact merge-mode argument field consumed by production code.
        events: list[str] = []  # Track observable ordering of merge normalization and border traversal.

        def record_normalization(rename_plan: list[dict[str, str]]) -> list[str]:  # Record directory normalization without mutating fixtures.
            """
            Record a merge normalization event for integration ordering validation.

            :param rename_plan: Frozen rename plan passed by the production merge function.
            :return: Empty list because this integration test performs no directory renames.
            """

            events.append("normalize")  # Record completion of the final merge directory normalization phase.

            return []  # Return the production-compatible list of normalized directory paths.

        def record_merged_border_removal(final_output_directory: str) -> int:  # Record merge-path border traversal without processing pixels.
            """
            Record a merged-output border removal event for integration ordering validation.

            :param final_output_directory: Merged directory passed by the production integration function.
            :return: Zero because this integration test does not process fixture pixels.
            """

            events.append(f"borders:{Path(final_output_directory).name}")  # Record the border pass and merged final directory target.

            return 0  # Return a valid crop count to preserve the production function contract.

        with patch.object(main, "create_directory"):  # Prevent merge-mode setup from creating the repository Outputs directory.
            with patch.object(main, "run_merge_output_directories", return_value=str(merged_directory)):  # Supply the isolated merged final directory.
                with patch.object(main, "sort_output_directories_by_platform_and_product_name", return_value=[]):  # Supply a deterministic empty rename plan.
                    with patch.object(main, "normalize_output_directory_indexes", side_effect=record_normalization):  # Observe the final directory normalization phase.
                        with patch.object(main, "remove_small_white_borders_from_final_output", side_effect=record_merged_border_removal):  # Observe the merge terminal border pass.
                            activated = main.handle_merge_mode(arguments, datetime.now())  # Execute the real merge-only orchestration path.

        self.assertTrue(activated)  # Require the merge handler to report that its execution path ran.
        self.assertEqual(["normalize", "borders:merged-run"], events)  # Require border removal strictly after merge directory normalization.


if __name__ == "__main__":  # Allow direct execution through the standard-library test runner.
    unittest.main()  # Execute all deterministic image border removal tests.
