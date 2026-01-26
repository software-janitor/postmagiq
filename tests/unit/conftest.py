"""Unit test configuration.

Sets up environment variables required for API module imports.
"""

import os

# Set test environment variables before any imports
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
