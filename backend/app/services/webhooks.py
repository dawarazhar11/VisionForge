"""
Webhook notification service for job completion events.
"""
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from app.config import settings


class WebhookService:
    """
    Service for sending webhook notifications.

    Sends HTTP POST requests to configured webhook URLs when jobs complete.
    """

    def __init__(self):
        self.timeout = 10.0  # Timeout for webhook requests in seconds
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds

    async def send_webhook(
        self,
        webhook_url: str,
        event_type: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a webhook notification.

        Args:
            webhook_url: The URL to send the webhook to
            event_type: Type of event (e.g., 'job.completed', 'job.failed')
            payload: The data to send in the webhook
            headers: Optional custom headers

        Returns:
            True if successful, False otherwise
        """
        webhook_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }

        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
            "X-Webhook-Event": event_type
        }

        if headers:
            default_headers.update(headers)

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook_url,
                        json=webhook_payload,
                        headers=default_headers
                    )

                    if response.status_code >= 200 and response.status_code < 300:
                        logger.info(
                            f"Webhook sent successfully to {webhook_url} "
                            f"(event: {event_type}, status: {response.status_code})"
                        )
                        return True
                    else:
                        logger.warning(
                            f"Webhook failed with status {response.status_code} "
                            f"for {webhook_url} (attempt {attempt + 1}/{self.max_retries})"
                        )

            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook timeout for {webhook_url} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Webhook request error for {webhook_url}: {e} "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error sending webhook to {webhook_url}: {e}"
                )
                return False

            # Exponential backoff for retries
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))

        logger.error(
            f"Webhook failed after {self.max_retries} attempts to {webhook_url}"
        )
        return False

    async def notify_job_completed(
        self,
        webhook_urls: List[str],
        job_id: str,
        job_type: str,
        status: str,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Notify about job completion.

        Args:
            webhook_urls: List of webhook URLs to notify
            job_id: ID of the completed job
            job_type: Type of job (render, train, etc.)
            status: Final status (SUCCESS, FAILED)
            result_data: Optional result data
            error_message: Optional error message if failed

        Returns:
            Dictionary mapping webhook URLs to success status
        """
        event_type = f"job.{status.lower()}"

        payload = {
            "job_id": job_id,
            "job_type": job_type,
            "status": status,
            "completed_at": datetime.utcnow().isoformat()
        }

        if result_data:
            payload["result"] = result_data

        if error_message:
            payload["error"] = error_message

        results = {}

        # Send to all webhook URLs concurrently
        tasks = [
            self.send_webhook(url, event_type, payload)
            for url in webhook_urls
        ]

        webhook_results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(webhook_urls, webhook_results):
            if isinstance(result, Exception):
                logger.error(f"Exception sending webhook to {url}: {result}")
                results[url] = False
            else:
                results[url] = result

        return results

    async def notify_job_progress(
        self,
        webhook_urls: List[str],
        job_id: str,
        job_type: str,
        progress: int,
        stage: str
    ) -> Dict[str, bool]:
        """
        Notify about job progress update.

        Args:
            webhook_urls: List of webhook URLs to notify
            job_id: ID of the job
            job_type: Type of job
            progress: Progress percentage (0-100)
            stage: Current stage description

        Returns:
            Dictionary mapping webhook URLs to success status
        """
        event_type = "job.progress"

        payload = {
            "job_id": job_id,
            "job_type": job_type,
            "progress": progress,
            "stage": stage,
            "updated_at": datetime.utcnow().isoformat()
        }

        results = {}

        tasks = [
            self.send_webhook(url, event_type, payload)
            for url in webhook_urls
        ]

        webhook_results = await asyncio.gather(*tasks, return_exceptions=True)

        for url, result in zip(webhook_urls, webhook_results):
            if isinstance(result, Exception):
                results[url] = False
            else:
                results[url] = result

        return results


# Global webhook service instance
webhook_service = WebhookService()
