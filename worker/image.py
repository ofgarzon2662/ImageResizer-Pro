from io import BytesIO

from PIL import Image


class ImageProcessor:
    def create_variant(self, image_bytes: bytes, width: int, output_format: str) -> bytes:
        with Image.open(BytesIO(image_bytes)) as source_image:
            source_image.load()
            resized = self._resize_to_width(source_image, width)
            output_buffer = BytesIO()
            save_format = "JPEG" if output_format == "jpeg" else output_format.upper()
            if save_format == "JPEG":
                resized = self._normalize_for_jpeg(resized)
            resized.save(output_buffer, format=save_format)
            return output_buffer.getvalue()

    def _resize_to_width(self, source_image: Image.Image, target_width: int) -> Image.Image:
        if source_image.width == target_width:
            return source_image.copy()

        ratio = target_width / source_image.width
        target_height = max(1, int(source_image.height * ratio))
        return source_image.resize((target_width, target_height), Image.Resampling.LANCZOS)

    def _normalize_for_jpeg(self, source_image: Image.Image) -> Image.Image:
        if source_image.mode in {"RGB", "L"}:
            return source_image
        if source_image.mode in {"RGBA", "LA"}:
            alpha_image = source_image.convert("RGBA")
            rgb_background = Image.new("RGB", alpha_image.size, (255, 255, 255))
            rgb_background.paste(alpha_image, mask=alpha_image.getchannel("A"))
            return rgb_background
        return source_image.convert("RGB")
