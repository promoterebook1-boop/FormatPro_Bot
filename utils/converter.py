import logging
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

logger = logging.getLogger(__name__)

class ImageConverter:
    def __init__(self, max_size_mb: int = 20):
        self.max_size_mb = max_size_mb
    
    async def convert(
        self,
        input_path: Path,
        output_path: Path,
        target_format: str,
        quality: int = 90,
        resize: Optional[Tuple[int, int]] = None
    ) -> Tuple[bool, str]:
        try:
            if not input_path.exists():
                return False, f"Input file not found: {input_path}"
            
            file_size_mb = input_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_size_mb:
                return False, f"File too large ({file_size_mb:.1f}MB). Max: {self.max_size_mb}MB"
            
            try:
                img = Image.open(input_path)
            except Exception as e:
                return False, f"Failed to open image: {str(e)}"
            
            if resize:
                img = img.resize(resize, Image.Resampling.LANCZOS)
            
            if target_format.lower() in ["jpg", "jpeg"] and img.mode in ["RGBA", "P", "LA"]:
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
                else:
                    background.paste(img)
                img = background
            
            if target_format.lower() == "bmp" and img.mode in ["RGBA", "LA"]:
                img = img.convert("RGB")
            
            if target_format.lower() == "ico":
                if img.size[0] > 256 or img.size[1] > 256:
                    img = img.resize((256, 256), Image.Resampling.LANCZOS)
            
            save_kwargs = {}
            format_upper = target_format.upper()
            
            if target_format.lower() in ["jpg", "jpeg"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            elif target_format.lower() == "webp":
                save_kwargs["quality"] = quality
                save_kwargs["method"] = 6
            elif target_format.lower() == "png":
                save_kwargs["optimize"] = True
                save_kwargs["compress_level"] = 6
            
            img.save(output_path, format=format_upper, **save_kwargs)
            
            if not output_path.exists() or output_path.stat().st_size == 0:
                return False, "Conversion failed - output file is empty"
            
            return True, f"Successfully converted to {format_upper}"
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return False, f"Conversion error: {str(e)}"
