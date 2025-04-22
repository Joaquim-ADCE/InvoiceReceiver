import pytest
from ProcessingData.process_email import fetch_email_details, extract_qr_code_from_email
from unittest.mock import patch, MagicMock
import numpy as np


def test_fetch_email_details_success():
    with patch('ProcessingData.process_email.get_access_token') as mock_token:
        with patch('requests.get') as mock_get:
            mock_token.return_value = "fake_token"
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "sender": {"emailAddress": {"address": "test@example.com"}},
                "subject": "Test Subject",
                "body": {"content": "Test Body"},
                "attachments": [],
                "receivedDateTime": "2024-01-01T00:00:00Z",
                "hasAttachments": False
            }
            
            result = fetch_email_details("test_id")
            
            assert result is not None
            assert result["sender"] == "test@example.com"
            assert result["subject"] == "Test Subject"


def test_fetch_email_details_not_found():
    with patch('ProcessingData.process_email.get_access_token') as mock_token:
        with patch('requests.get') as mock_get:
            mock_token.return_value = "fake_token"
            mock_get.return_value.status_code = 404
            mock_get.return_value.json.return_value = {
                "error": {"code": "ErrorItemNotFound"}
            }
            
            result = fetch_email_details("test_id")
            assert result is None


def test_extract_qr_code_valid():
    """This function tests the extraction of QR code from PDF"""
    mock_attachment = {
        "filename": "test.pdf",
        "content": b"fake_pdf_content",
        "contentType": "application/pdf"
    }
    
    with patch('fitz.open') as mock_open:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.extract_image.return_value = {"image": b"fake_image"}
        mock_open.return_value = mock_doc
        
        with patch('cv2.imdecode') as mock_decode:
            mock_img = np.zeros((100, 100), dtype=np.uint8)
            mock_decode.return_value = mock_img
            
            with patch('cv2.QRCodeDetector') as mock_detector:
                mock_detector_instance = MagicMock()
                mock_detector_instance.detectAndDecode.return_value = (
                    "A:123*B:456*C:789*D:101112*E:131415*F:161718*G:192021*H:222324*I:252627*J:282930*K:313233*L:343536*M:373839*N:404142*O:434445*P:464748*Q:495051*R:525354*S:555657*T:585960*U:616263*V:646566*W:676869*X:707172*Y:737475*Z:767778*",  # dados do QR code
                    np.array([[0, 0], [0, 1], [1, 1], [1, 0]]),  # pontos detectados
                    None  # matriz binária
                )
                mock_detector.return_value = mock_detector_instance
                
                result = extract_qr_code_from_email([mock_attachment])
                assert result == "A:123*B:456*C:789*D:101112*E:131415*F:161718*G:192021*H:222324*I:252627*J:282930*K:313233*L:343536*M:373839*N:404142*O:434445*P:464748*Q:495051*R:525354*S:555657*T:585960*U:616263*V:646566*W:676869*X:707172*Y:737475*Z:767778*"

def test_extract_qr_code_no_qr():
    """This function tests when no QR code is found"""
    mock_attachment = {
        "filename": "test.pdf",
        "content": b"fake_pdf_content",
        "contentType": "application/pdf"
    }
    
    with patch('fitz.open') as mock_open:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.extract_image.return_value = {"image": b"fake_image"}
        mock_open.return_value = mock_doc
        
        with patch('cv2.imdecode') as mock_decode:
            mock_img = np.zeros((100, 100), dtype=np.uint8)
            mock_decode.return_value = mock_img
            
            with patch('cv2.QRCodeDetector') as mock_detector:
                mock_detector_instance = MagicMock()
                mock_detector_instance.detectAndDecode.return_value = ("", None, None)
                mock_detector.return_value = mock_detector_instance
                
                result = extract_qr_code_from_email([mock_attachment])
                assert result is None
