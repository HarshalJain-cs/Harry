"""
JARVIS OCR Engine - Optical Character Recognition.

Extracts text from screen captures and images.
"""

import os
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Try different OCR backends
OCR_BACKEND = None

try:
    from paddleocr import PaddleOCR
    OCR_BACKEND = "paddleocr"
except ImportError:
    pass

if not OCR_BACKEND:
    try:
        import pytesseract
        OCR_BACKEND = "tesseract"
    except ImportError:
        pass

from tools.registry import tool, ToolResult


@dataclass
class TextRegion:
    """A detected text region."""
    text: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float


class OCREngine:
    """
    Extract text from images using OCR.
    
    Supports:
    - PaddleOCR (preferred, GPU accelerated)
    - Tesseract (fallback)
    """
    
    def __init__(self, backend: Optional[str] = None):
        """
        Initialize OCR engine.
        
        Args:
            backend: OCR backend to use (paddleocr, tesseract)
        """
        self.backend = backend or OCR_BACKEND
        self.engine = None
        
        if self.backend == "paddleocr":
            self.engine = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                show_log=False,
                use_gpu=False,  # Set True if GPU available
            )
        elif self.backend == "tesseract":
            # Tesseract doesn't need initialization
            pass
        else:
            raise RuntimeError("No OCR backend available. Install paddleocr or pytesseract")
    
    def extract_text(
        self,
        image: Any,
        language: str = "en",
    ) -> str:
        """
        Extract all text from an image.
        
        Args:
            image: Image as numpy array, PIL Image, or file path
            language: Language code
            
        Returns:
            Extracted text as string
        """
        regions = self.extract_regions(image, language)
        return '\n'.join(r.text for r in regions)
    
    def extract_regions(
        self,
        image: Any,
        language: str = "en",
    ) -> List[TextRegion]:
        """
        Extract text with bounding boxes.
        
        Args:
            image: Image source
            language: Language code
            
        Returns:
            List of TextRegion objects
        """
        # Convert image to proper format
        if isinstance(image, str):
            if PIL_AVAILABLE:
                image = np.array(Image.open(image))
            elif CV2_AVAILABLE:
                image = cv2.imread(image)
        elif PIL_AVAILABLE and isinstance(image, Image.Image):
            image = np.array(image)
        
        if self.backend == "paddleocr":
            return self._extract_paddle(image)
        elif self.backend == "tesseract":
            return self._extract_tesseract(image, language)
        else:
            return []
    
    def _extract_paddle(self, image: np.ndarray) -> List[TextRegion]:
        """Extract using PaddleOCR."""
        result = self.engine.ocr(image, cls=True)
        
        regions = []
        if result and result[0]:
            for line in result[0]:
                bbox_points = line[0]
                text = line[1][0]
                confidence = line[1][1]
                
                # Convert polygon to bbox
                x_coords = [p[0] for p in bbox_points]
                y_coords = [p[1] for p in bbox_points]
                bbox = (
                    int(min(x_coords)),
                    int(min(y_coords)),
                    int(max(x_coords)),
                    int(max(y_coords)),
                )
                
                regions.append(TextRegion(
                    text=text,
                    bbox=bbox,
                    confidence=confidence,
                ))
        
        return regions
    
    def _extract_tesseract(
        self,
        image: np.ndarray,
        language: str,
    ) -> List[TextRegion]:
        """Extract using Tesseract."""
        import pytesseract
        
        # Get detailed data
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT,
        )
        
        regions = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            if not text:
                continue
            
            conf = int(data['conf'][i])
            if conf < 30:  # Skip low confidence
                continue
            
            x, y = data['left'][i], data['top'][i]
            w, h = data['width'][i], data['height'][i]
            
            regions.append(TextRegion(
                text=text,
                bbox=(x, y, x + w, y + h),
                confidence=conf / 100.0,
            ))
        
        return regions
    
    def find_text(
        self,
        image: Any,
        target: str,
        threshold: float = 0.6,
    ) -> Optional[TextRegion]:
        """
        Find specific text in image.
        
        Args:
            image: Image source
            target: Text to find
            threshold: Minimum confidence
            
        Returns:
            TextRegion if found, None otherwise
        """
        regions = self.extract_regions(image)
        target_lower = target.lower()
        
        for region in regions:
            if (target_lower in region.text.lower() and 
                region.confidence >= threshold):
                return region
        
        return None


# Tool registrations
@tool(
    name="read_screen_text",
    description="Read all text visible on screen",
    category="vision",
    examples=["read screen", "what text is on screen"],
)
def read_screen_text(monitor: int = 0) -> ToolResult:
    """Read text from screen."""
    try:
        from .screen import ScreenCapture
        
        capture = ScreenCapture()
        screenshot = capture.capture_full(monitor)
        
        ocr = OCREngine()
        text = ocr.extract_text(screenshot)
        
        if not text.strip():
            return ToolResult(success=True, output="No text detected on screen")
        
        # Truncate if too long
        if len(text) > 3000:
            text = text[:3000] + "\n... (truncated)"
        
        return ToolResult(success=True, output=text)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="read_image_text",
    description="Extract text from an image file",
    category="vision",
)
def read_image_text(image_path: str) -> ToolResult:
    """Read text from image file."""
    try:
        if not os.path.exists(image_path):
            return ToolResult(success=False, error=f"File not found: {image_path}")
        
        ocr = OCREngine()
        text = ocr.extract_text(image_path)
        
        if not text.strip():
            return ToolResult(success=True, output="No text detected in image")
        
        return ToolResult(success=True, output=text)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool(
    name="find_on_screen",
    description="Find specific text on screen",
    category="vision",
    examples=["find 'Submit' button on screen"],
)
def find_on_screen(text: str) -> ToolResult:
    """Find text on screen."""
    try:
        from .screen import ScreenCapture
        
        capture = ScreenCapture()
        screenshot = capture.capture_full()
        
        ocr = OCREngine()
        region = ocr.find_text(screenshot, text)
        
        if not region:
            return ToolResult(success=False, error=f"Text not found: {text}")
        
        # Calculate center point
        center_x = (region.bbox[0] + region.bbox[2]) // 2
        center_y = (region.bbox[1] + region.bbox[3]) // 2
        
        return ToolResult(
            success=True,
            output={
                "text": region.text,
                "position": (center_x, center_y),
                "bbox": region.bbox,
                "confidence": region.confidence,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


if __name__ == "__main__":
    print("Testing OCR Engine...")
    print(f"Backend: {OCR_BACKEND}")
    
    if OCR_BACKEND:
        try:
            ocr = OCREngine()
            print("OCR initialized successfully")
            
            # Test with a simple image if available
            # In production, would test with actual screenshots
        except Exception as e:
            print(f"OCR init failed: {e}")
    else:
        print("No OCR backend available")
    
    print("\nTests complete!")
