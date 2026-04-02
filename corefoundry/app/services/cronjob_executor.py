"""Cronjob executor service for making HTTP requests."""

import logging
import time
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from corefoundry.app.db.models import Cronjob, CronjobLog

logger = logging.getLogger(__name__)


class CronjobExecutor:
    """Service for executing cronjobs and logging results."""
    
    def __init__(self, timeout: int = 30):
        """Initialize executor with timeout in seconds."""
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    
    async def execute_cronjob(self, cronjob: Cronjob, db: Session) -> bool:
        """
        Execute a single cronjob and log the result.
        
        Args:
            cronjob: The Cronjob model instance to execute
            db: Database session
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        start_time = time.time()
        status_code = None
        error_message = None
        response_body = None
        
        try:
            logger.info(f"Executing cronjob {cronjob.id} ({cronjob.name}): {cronjob.method} {cronjob.url}")
            
            # Prepare request parameters
            kwargs = {
                "method": cronjob.method.upper(),
                "url": cronjob.url,
            }
            
            # Add headers if present
            if cronjob.headers:
                kwargs["headers"] = cronjob.headers
            
            # Add body for methods that support it
            if cronjob.method.upper() in ["POST", "PUT", "PATCH"] and cronjob.body:
                kwargs["json"] = cronjob.body
            
            # Make the HTTP request
            response = await self.client.request(**kwargs)
            status_code = response.status_code
            
            # Store response body (limit to 10KB to avoid bloat)
            response_text = response.text[:10000] if response.text else None
            response_body = response_text
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update cronjob last run info
            cronjob.last_run_at = datetime.utcnow()
            cronjob.last_status_code = status_code
            cronjob.last_error = None if 200 <= status_code < 300 else f"HTTP {status_code}"
            
            # Create log entry
            log_entry = CronjobLog(
                cronjob_id=cronjob.id,
                executed_at=datetime.utcnow(),
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=None if 200 <= status_code < 300 else f"HTTP {status_code}",
                response_body=response_body
            )
            db.add(log_entry)
            db.commit()
            
            success = 200 <= status_code < 300
            if success:
                logger.info(f"Cronjob {cronjob.id} completed successfully: {status_code} in {response_time_ms}ms")
            else:
                logger.warning(f"Cronjob {cronjob.id} completed with error: {status_code} in {response_time_ms}ms")
            
            return success
            
        except httpx.TimeoutException as e:
            error_message = f"Request timeout after {self.timeout}s"
            logger.error(f"Cronjob {cronjob.id} timed out: {error_message}")
            
        except httpx.RequestError as e:
            error_message = f"Request error: {str(e)}"
            logger.error(f"Cronjob {cronjob.id} request error: {error_message}")
            
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Cronjob {cronjob.id} unexpected error: {error_message}", exc_info=True)
        
        # Handle errors
        response_time_ms = int((time.time() - start_time) * 1000)
        
        cronjob.last_run_at = datetime.utcnow()
        cronjob.last_status_code = status_code
        cronjob.last_error = error_message
        
        log_entry = CronjobLog(
            cronjob_id=cronjob.id,
            executed_at=datetime.utcnow(),
            status_code=status_code,
            response_time_ms=response_time_ms,
            error_message=error_message,
            response_body=None
        )
        db.add(log_entry)
        db.commit()
        
        return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
