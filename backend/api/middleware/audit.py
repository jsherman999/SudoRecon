"""Audit logging middleware."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.db.session import SessionLocal
from backend.models import AuditLog


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for audit purposes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log to audit trail."""
        start_time = time.time()

        # Get user from request (simplified - in production use proper auth)
        user = request.headers.get("X-User", "anonymous")

        # Call the endpoint
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log to database (only for state-changing operations)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            try:
                db = SessionLocal()

                # Extract resource info from path
                path_parts = request.url.path.split("/")
                resource_type = path_parts[3] if len(path_parts) > 3 else None
                resource_id = path_parts[4] if len(path_parts) > 4 else None

                audit_log = AuditLog(
                    user_id=None,  # TODO: Link to actual user
                    action=f"{request.method} {request.url.path}",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )

                db.add(audit_log)
                db.commit()
                db.close()
            except Exception as e:
                # Don't fail the request if audit logging fails
                print(f"Audit logging error: {e}")

        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)

        return response
