import io
import pdfplumber
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from typing import Optional


def extract_qr_from_pdf_bytes(pdf_bytes: bytes) -> Optional[str]:
    """
    Extract and decode the QR code from a PDF byte stream.

    Args:
        pdf_bytes: The PDF file content as bytes.

    Returns:
        The decoded QR code content, or None if not found.
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=300)
                img_bytes = img.original.convert("RGB").tobytes("raw", "RGB")
                np_img = np.frombuffer(img_bytes, dtype=np.uint8).reshape((img.original.height, img.original.width, 3))
                
                # Decode QR from the image
                decoded_objects = decode(np_img)
                for obj in decoded_objects:
                    return obj.data.decode("utf-8")
    except Exception as e:
        print(f"Failed to extract QR code: {e}")

    return None
