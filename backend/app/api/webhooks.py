"""
Webhook management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger
from typing import List
import time
import asyncio

from app.api.deps import get_db, get_current_active_user
from app.models.user import User
from app.schemas.webhook import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookListResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.services.webhooks import webhook_service

router = APIRouter()


@router.get("/", response_model=WebhookListResponse)
def list_webhooks(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all configured webhook URLs for the current user.

    Returns:
        List of webhook URLs with their indices and descriptions
    """
    webhook_urls = current_user.webhook_urls if current_user.webhook_urls else []

    webhooks = []
    for idx, webhook_data in enumerate(webhook_urls):
        # Handle both string URLs (legacy) and dict format (new)
        if isinstance(webhook_data, str):
            webhooks.append(WebhookResponse(index=idx, url=webhook_data, description=None))
        elif isinstance(webhook_data, dict):
            webhooks.append(WebhookResponse(
                index=idx,
                url=webhook_data.get("url", ""),
                description=webhook_data.get("description")
            ))

    return WebhookListResponse(webhooks=webhooks, total=len(webhooks))


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def add_webhook(
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a new webhook URL to the current user's configuration.

    Args:
        webhook_data: Webhook URL and optional description

    Returns:
        Created webhook with its index

    Raises:
        HTTPException: If webhook URL already exists
    """
    # Get current webhook URLs
    webhook_urls = current_user.webhook_urls if current_user.webhook_urls else []

    # Check if URL already exists
    url_str = str(webhook_data.url)
    for webhook in webhook_urls:
        existing_url = webhook.get("url") if isinstance(webhook, dict) else webhook
        if existing_url == url_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook URL already exists: {url_str}"
            )

    # Add new webhook
    new_webhook = {
        "url": url_str,
        "description": webhook_data.description
    }
    webhook_urls.append(new_webhook)

    # Update user model
    current_user.webhook_urls = webhook_urls
    db.commit()
    db.refresh(current_user)

    logger.info(f"Added webhook for user {current_user.id}: {url_str}")

    return WebhookResponse(
        index=len(webhook_urls) - 1,
        url=url_str,
        description=webhook_data.description
    )


@router.put("/{webhook_index}", response_model=WebhookResponse)
def update_webhook(
    webhook_index: int,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing webhook URL.

    Args:
        webhook_index: Index of webhook to update
        webhook_data: Updated webhook URL and/or description

    Returns:
        Updated webhook

    Raises:
        HTTPException: If webhook index is invalid
    """
    webhook_urls = current_user.webhook_urls if current_user.webhook_urls else []

    if webhook_index < 0 or webhook_index >= len(webhook_urls):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook index {webhook_index} not found"
        )

    # Get existing webhook
    existing_webhook = webhook_urls[webhook_index]
    if isinstance(existing_webhook, str):
        existing_webhook = {"url": existing_webhook, "description": None}

    # Update webhook
    if webhook_data.url:
        url_str = str(webhook_data.url)
        # Check if new URL conflicts with other webhooks
        for idx, webhook in enumerate(webhook_urls):
            if idx == webhook_index:
                continue
            other_url = webhook.get("url") if isinstance(webhook, dict) else webhook
            if other_url == url_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Webhook URL already exists at index {idx}: {url_str}"
                )
        existing_webhook["url"] = url_str

    if webhook_data.description is not None:
        existing_webhook["description"] = webhook_data.description

    webhook_urls[webhook_index] = existing_webhook

    # Update user model
    current_user.webhook_urls = webhook_urls
    db.commit()
    db.refresh(current_user)

    logger.info(f"Updated webhook {webhook_index} for user {current_user.id}")

    return WebhookResponse(
        index=webhook_index,
        url=existing_webhook["url"],
        description=existing_webhook.get("description")
    )


@router.delete("/{webhook_index}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_index: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a webhook URL from the current user's configuration.

    Args:
        webhook_index: Index of webhook to delete

    Raises:
        HTTPException: If webhook index is invalid
    """
    webhook_urls = current_user.webhook_urls if current_user.webhook_urls else []

    if webhook_index < 0 or webhook_index >= len(webhook_urls):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook index {webhook_index} not found"
        )

    # Remove webhook
    removed_webhook = webhook_urls.pop(webhook_index)
    removed_url = removed_webhook.get("url") if isinstance(removed_webhook, dict) else removed_webhook

    # Update user model
    current_user.webhook_urls = webhook_urls
    db.commit()
    db.refresh(current_user)

    logger.info(f"Deleted webhook {webhook_index} for user {current_user.id}: {removed_url}")


@router.post("/test", response_model=List[WebhookTestResponse])
async def test_webhooks(
    test_request: WebhookTestRequest = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send a test webhook notification to verify configuration.

    Args:
        test_request: Optional specific webhook URL to test (if not provided, tests all)

    Returns:
        List of test results for each webhook tested

    Raises:
        HTTPException: If no webhooks configured or specified URL not found
    """
    webhook_urls = current_user.webhook_urls if current_user.webhook_urls else []

    if not webhook_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No webhooks configured. Add a webhook URL first."
        )

    # Determine which webhooks to test
    urls_to_test = []
    if test_request and test_request.url:
        test_url_str = str(test_request.url)
        found = False
        for webhook in webhook_urls:
            webhook_url = webhook.get("url") if isinstance(webhook, dict) else webhook
            if webhook_url == test_url_str:
                urls_to_test.append(webhook_url)
                found = True
                break
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook URL not found: {test_url_str}"
            )
    else:
        # Test all webhooks
        for webhook in webhook_urls:
            webhook_url = webhook.get("url") if isinstance(webhook, dict) else webhook
            urls_to_test.append(webhook_url)

    # Send test webhook to each URL
    test_results = []

    test_payload = {
        "job_id": "test-job-id",
        "job_type": "test",
        "status": "SUCCESS",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": {
            "message": "This is a test webhook notification",
            "user_id": str(current_user.id),
            "user_email": current_user.email
        }
    }

    for url in urls_to_test:
        start_time = time.time()
        try:
            success = await webhook_service.send_webhook(
                webhook_url=url,
                event_type="job.test",
                payload=test_payload
            )
            response_time_ms = (time.time() - start_time) * 1000

            test_results.append(WebhookTestResponse(
                url=url,
                success=success,
                status_code=200 if success else None,
                response_time_ms=response_time_ms
            ))
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            test_results.append(WebhookTestResponse(
                url=url,
                success=False,
                error=str(e),
                response_time_ms=response_time_ms
            ))
            logger.error(f"Error testing webhook {url}: {e}")

    logger.info(f"Tested {len(test_results)} webhooks for user {current_user.id}")

    return test_results
