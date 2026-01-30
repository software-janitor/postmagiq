"""Social media platform services for OAuth and publishing.

Handles OAuth flows and content publishing for LinkedIn, X, and Threads.
"""

import os
from urllib.parse import urlencode

import httpx

# =============================================================================
# Configuration
# =============================================================================

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/v1/social/callback/linkedin"
)

X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_REDIRECT_URI = os.getenv(
    "X_REDIRECT_URI", "http://localhost:8000/v1/social/callback/x"
)

THREADS_APP_ID = os.getenv("THREADS_APP_ID", "")
THREADS_APP_SECRET = os.getenv("THREADS_APP_SECRET", "")
THREADS_REDIRECT_URI = os.getenv(
    "THREADS_REDIRECT_URI", "http://localhost:8000/v1/social/callback/threads"
)


# =============================================================================
# LinkedIn Service
# =============================================================================


class LinkedInService:
    """LinkedIn OAuth and publishing service."""

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_URL = "https://api.linkedin.com/v2"

    def get_authorization_url(self, state: str) -> str:
        """Generate LinkedIn OAuth authorization URL."""
        params = {
            "response_type": "code",
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "state": state,
            "scope": "openid profile email w_member_social",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": LINKEDIN_REDIRECT_URI,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh an access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": LINKEDIN_CLIENT_ID,
                    "client_secret": LINKEDIN_CLIENT_SECRET,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_profile(self, access_token: str) -> dict:
        """Get user profile from LinkedIn."""
        async with httpx.AsyncClient() as client:
            # Get user info from userinfo endpoint (OpenID Connect)
            response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            return {
                "id": data.get("sub"),
                "username": data.get("email", "").split("@")[0],
                "name": data.get("name"),
                "email": data.get("email"),
            }

    async def publish(self, access_token: str, person_id: str, text: str) -> dict:
        """Publish a post to LinkedIn.

        Args:
            access_token: OAuth access token
            person_id: LinkedIn person URN (sub from userinfo)
            text: Post content

        Returns:
            dict with post_id and post_url
        """
        async with httpx.AsyncClient() as client:
            payload = {
                "author": f"urn:li:person:{person_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response = await client.post(
                f"{self.API_URL}/ugcPosts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract post ID from response
            post_id = data.get("id", "")
            # LinkedIn post URLs are typically in format:
            # https://www.linkedin.com/feed/update/{activity_id}
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"

            return {"post_id": post_id, "post_url": post_url}


# =============================================================================
# X (Twitter) Service
# =============================================================================


class XService:
    """X (Twitter) OAuth 1.0a and publishing service."""

    REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
    AUTH_URL = "https://api.twitter.com/oauth/authorize"
    ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
    API_URL = "https://api.twitter.com/2"

    async def get_authorization_url(self, state: str) -> tuple[str, str, str]:
        """Get OAuth 1.0a authorization URL.

        Returns:
            Tuple of (auth_url, request_token, request_secret)
        """
        # OAuth 1.0a requires signing - use authlib or tweepy in production
        # This is a simplified placeholder
        from authlib.integrations.httpx_client import OAuth1Client

        async with OAuth1Client(
            client_id=X_API_KEY,
            client_secret=X_API_SECRET,
        ) as client:
            request_token = await client.fetch_request_token(
                self.REQUEST_TOKEN_URL,
                params={"oauth_callback": f"{X_REDIRECT_URI}?state={state}"},
            )
            auth_url = f"{self.AUTH_URL}?oauth_token={request_token['oauth_token']}"
            return (
                auth_url,
                request_token["oauth_token"],
                request_token["oauth_token_secret"],
            )

    async def exchange_code(
        self, oauth_token: str, oauth_token_secret: str, oauth_verifier: str
    ) -> dict:
        """Exchange OAuth 1.0a verifier for access token."""
        from authlib.integrations.httpx_client import OAuth1Client

        async with OAuth1Client(
            client_id=X_API_KEY,
            client_secret=X_API_SECRET,
            token=oauth_token,
            token_secret=oauth_token_secret,
        ) as client:
            token = await client.fetch_access_token(
                self.ACCESS_TOKEN_URL,
                verifier=oauth_verifier,
            )
            return {
                "access_token": token["oauth_token"],
                "access_token_secret": token["oauth_token_secret"],
                "user_id": token.get("user_id"),
                "screen_name": token.get("screen_name"),
            }

    async def get_profile(self, access_token: str, access_token_secret: str) -> dict:
        """Get user profile from X."""
        from authlib.integrations.httpx_client import OAuth1Client

        async with OAuth1Client(
            client_id=X_API_KEY,
            client_secret=X_API_SECRET,
            token=access_token,
            token_secret=access_token_secret,
        ) as client:
            response = await client.get(
                f"{self.API_URL}/users/me",
                params={"user.fields": "id,name,username"},
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            return {
                "id": data.get("id"),
                "username": data.get("username"),
                "name": data.get("name"),
            }

    async def publish(
        self, access_token: str, access_token_secret: str, text: str
    ) -> dict:
        """Publish a tweet to X.

        Args:
            access_token: OAuth access token
            access_token_secret: OAuth access token secret
            text: Tweet content (max 280 chars for free tier)

        Returns:
            dict with post_id and post_url
        """
        from authlib.integrations.httpx_client import OAuth1Client

        async with OAuth1Client(
            client_id=X_API_KEY,
            client_secret=X_API_SECRET,
            token=access_token,
            token_secret=access_token_secret,
        ) as client:
            response = await client.post(
                f"{self.API_URL}/tweets",
                json={"text": text},
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            tweet_id = data.get("id")
            post_url = f"https://x.com/i/status/{tweet_id}"

            return {"post_id": tweet_id, "post_url": post_url}


# =============================================================================
# Threads Service
# =============================================================================


class ThreadsService:
    """Threads OAuth and publishing service."""

    AUTH_URL = "https://threads.net/oauth/authorize"
    TOKEN_URL = "https://graph.threads.net/oauth/access_token"
    API_URL = "https://graph.threads.net/v1.0"

    def get_authorization_url(self, state: str) -> str:
        """Generate Threads OAuth authorization URL."""
        params = {
            "client_id": THREADS_APP_ID,
            "redirect_uri": THREADS_REDIRECT_URI,
            "scope": "threads_basic,threads_content_publish",
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            # Short-lived token
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": THREADS_APP_ID,
                    "client_secret": THREADS_APP_SECRET,
                    "grant_type": "authorization_code",
                    "redirect_uri": THREADS_REDIRECT_URI,
                    "code": code,
                },
            )
            response.raise_for_status()
            short_lived = response.json()

            # Exchange for long-lived token
            response = await client.get(
                f"{self.API_URL}/access_token",
                params={
                    "grant_type": "th_exchange_token",
                    "client_secret": THREADS_APP_SECRET,
                    "access_token": short_lived["access_token"],
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_profile(self, access_token: str) -> dict:
        """Get user profile from Threads."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_URL}/me",
                params={
                    "fields": "id,username,name,threads_profile_picture_url",
                    "access_token": access_token,
                },
            )
            response.raise_for_status()
            data = response.json()
            return {
                "id": data.get("id"),
                "username": data.get("username"),
                "name": data.get("name"),
            }

    async def publish(self, access_token: str, user_id: str, text: str) -> dict:
        """Publish a post to Threads.

        Threads requires a two-step process:
        1. Create a media container
        2. Publish the container

        Args:
            access_token: OAuth access token
            user_id: Threads user ID
            text: Post content

        Returns:
            dict with post_id and post_url
        """
        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            container_response = await client.post(
                f"{self.API_URL}/{user_id}/threads",
                params={
                    "media_type": "TEXT",
                    "text": text,
                    "access_token": access_token,
                },
            )
            container_response.raise_for_status()
            container_id = container_response.json().get("id")

            # Step 2: Publish the container
            publish_response = await client.post(
                f"{self.API_URL}/{user_id}/threads_publish",
                params={
                    "creation_id": container_id,
                    "access_token": access_token,
                },
            )
            publish_response.raise_for_status()
            data = publish_response.json()

            post_id = data.get("id")
            # Threads post URL format
            post_url = f"https://threads.net/t/{post_id}"

            return {"post_id": post_id, "post_url": post_url}


# =============================================================================
# Service Instances
# =============================================================================

linkedin_service = LinkedInService()
x_service = XService()
threads_service = ThreadsService()
