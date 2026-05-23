import io
import json
import logging
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.server import create_app
from src.common.logging import configure_logging, correlation_id_ctx


def test_correlation_id_middleware_generates_id():
    """Verify that a unique correlation ID is generated when none is provided in the headers."""
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    correlation_id = response.headers["X-Correlation-ID"]
    
    # Assert it is a valid UUID
    assert uuid.UUID(correlation_id)


def test_correlation_id_middleware_retains_provided_id():
    """Verify that an existing X-Correlation-ID header is retained and returned in the response."""
    app = create_app()
    client = TestClient(app)
    custom_id = "test-correlation-id-1234"

    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_id


def test_correlation_id_middleware_retains_provided_request_id():
    """Verify that an existing X-Request-ID header is used when X-Correlation-ID is missing."""
    app = create_app()
    client = TestClient(app)
    custom_id = "test-request-id-5678"

    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_id


def test_correlation_id_injected_into_structured_logs():
    """Verify that logs generated during request handling contain the correct request_id."""
    app = create_app()
    
    # Setup custom logger stream to capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    
    # Configure custom logging format matching structured output
    from src.common.logging import StructuredFormatter, CorrelationIdFilter
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(StructuredFormatter())
    
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
    
    client = TestClient(app)
    custom_id = str(uuid.uuid4())

    try:
        response = client.get("/health", headers={"X-Correlation-ID": custom_id})
        assert response.status_code == 200
        
        # Parse logs
        log_output = log_capture.getvalue().strip()
        assert log_output != ""
        
        # Check if the log contains our custom request_id
        found_in_logs = False
        for line in log_output.splitlines():
            if line:
                log_entry = json.loads(line)
                if log_entry.get("request_id") == custom_id:
                    found_in_logs = True
                    break
        assert found_in_logs, f"Expected correlation ID {custom_id} in log output: {log_output}"
        
    finally:
        # Restore handlers and level
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)
