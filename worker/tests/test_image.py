from io import BytesIO

from PIL import Image

from image import ImageProcessor


def test_create_variant_resizes_image_to_requested_width():
    source = Image.new("RGB", (800, 400), color="red")
    buffer = BytesIO()
    source.save(buffer, format="PNG")

    processor = ImageProcessor()
    output = processor.create_variant(buffer.getvalue(), width=200, output_format="jpeg")

    with Image.open(BytesIO(output)) as resized:
        assert resized.width == 200


def test_create_variant_keeps_image_non_empty():
    source = Image.new("RGB", (100, 50), color="blue")
    buffer = BytesIO()
    source.save(buffer, format="PNG")

    processor = ImageProcessor()
    output = processor.create_variant(buffer.getvalue(), width=64, output_format="png")
    assert len(output) > 0


def test_create_variant_supports_rgba_input_for_jpeg_output():
    source = Image.new("RGBA", (240, 120), color=(10, 20, 30, 120))
    buffer = BytesIO()
    source.save(buffer, format="PNG")

    processor = ImageProcessor()
    output = processor.create_variant(buffer.getvalue(), width=120, output_format="jpeg")

    with Image.open(BytesIO(output)) as converted:
        assert converted.mode == "RGB"
        assert converted.width == 120
