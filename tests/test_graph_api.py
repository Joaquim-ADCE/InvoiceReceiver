import pytest
from ProcessingData.API.graph_api import get_access_token, send_email
from unittest.mock import patch
from datetime import datetime, timedelta


def test_get_access_token_cached():
    future_time = datetime.utcnow() + timedelta(minutes=30)
    with patch('ProcessingData.API.graph_api._token_cache') as mock_cache:
        mock_cache.__getitem__.side_effect = {
            "access_token": "cached_token",
            "expires_at": future_time
        }.get
        
        token = get_access_token()
        assert token == "cached_token"


def test_get_access_token_new():
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600
        }
        
        token = get_access_token()
        assert token == "new_token"


def test_send_email_success():
    with patch('ProcessingData.API.graph_api.get_access_token') as mock_token:
        with patch('requests.post') as mock_post:
            mock_token.return_value = "fake_token"
            mock_post.return_value.status_code = 202
            
            result = send_email("Test Subject", "Test Message")
            assert result is True


def test_send_email_failure():
    with patch('ProcessingData.API.graph_api.get_access_token') as mock_token:
        with patch('requests.post') as mock_post:
            mock_token.return_value = "fake_token"
            mock_post.return_value.status_code = 400
            
            result = send_email("Test Subject", "Test Message")
            assert result is False 
