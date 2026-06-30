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
        quality: int = 90
    ) -> Tuple[bool, str]:
        try:
            if not input_path.exists():
                return False, "File not found"
            
            img = Image.open(input_path)
            
            if target_format.lower() in ["jpg", "jpeg"] and img.mode in ["RGBA", "P"]:
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
                else:
                    background.paste(img)
                img = background
            
            save_kwargs = {}
            if target_format.lower() in ["jpg", "jpeg"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            
            img.save(output_path, format=target_format.upper(), **save_kwargs)
            
            if not output_path.exists():
                return False, "Conversion failed"
            
            return True, "Success"
            
        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return False, str(e)
