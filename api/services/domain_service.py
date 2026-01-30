"""Domain service for custom domain verification and DKIM setup.

Provides:
- Domain verification token generation and DNS verification
- DKIM keypair generation and DNS verification
- Custom domain management for white-label workspaces
"""

import dns.resolver
from datetime import datetime
from typing import Optional
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from sqlmodel import Session, select

from runner.db.models import (
    WhitelabelConfig,
    DomainVerificationStatus,
)


class DomainServiceError(Exception):
    """Base exception for domain service errors."""

    pass


class DomainNotFoundError(DomainServiceError):
    """Raised when a domain configuration is not found."""

    pass


class DomainAlreadyVerifiedError(DomainServiceError):
    """Raised when trying to verify an already verified domain."""

    pass


class DomainVerificationFailedError(DomainServiceError):
    """Raised when domain verification fails."""

    pass


class DKIMGenerationError(DomainServiceError):
    """Raised when DKIM key generation fails."""

    pass


# DNS record names for verification
VERIFICATION_TXT_PREFIX = "_quillexir-verify"
DKIM_TXT_PREFIX = "_domainkey"


class DomainService:
    """Service for managing custom domains and DKIM setup."""

    # ==========================================================================
    # Domain Verification
    # ==========================================================================

    def generate_verification_token(
        self,
        session: Session,
        workspace_id: UUID,
        custom_domain: str,
    ) -> str:
        """Generate a verification token for a custom domain.

        Creates or updates the whitelabel config with a new verification token.
        The token should be added as a DNS TXT record at:
        _quillexir-verify.{custom_domain}

        Args:
            session: Database session
            workspace_id: Workspace UUID
            custom_domain: The domain to verify (e.g., content.agency.com)

        Returns:
            str: The verification token to add to DNS

        Raises:
            DomainAlreadyVerifiedError: If domain is already verified
        """
        # Get or create whitelabel config
        config = self._get_or_create_config(session, workspace_id)

        # Check if already verified
        if config.domain_verified and config.custom_domain == custom_domain:
            raise DomainAlreadyVerifiedError(
                f"Domain {custom_domain} is already verified"
            )

        # Generate new token
        token = WhitelabelConfig.generate_verification_token()

        # Update config
        config.custom_domain = custom_domain
        config.domain_verification_token = token
        config.domain_verified = False
        config.domain_verification_status = DomainVerificationStatus.PENDING.value
        config.domain_verified_at = None

        session.add(config)
        session.commit()
        session.refresh(config)

        return token

    def verify_domain(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> bool:
        """Verify a custom domain by checking DNS TXT record.

        Looks for TXT record at _quillexir-verify.{domain} containing
        the verification token.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            bool: True if verification succeeded

        Raises:
            DomainNotFoundError: If no domain is configured
            DomainVerificationFailedError: If DNS verification fails
        """
        config = self._get_config(session, workspace_id)

        if not config or not config.custom_domain:
            raise DomainNotFoundError("No custom domain configured")

        if not config.domain_verification_token:
            raise DomainNotFoundError("No verification token generated")

        domain = config.custom_domain
        token = config.domain_verification_token
        txt_record_name = f"{VERIFICATION_TXT_PREFIX}.{domain}"

        # Check DNS TXT record
        verified = self._check_dns_txt_record(txt_record_name, token)

        if verified:
            config.domain_verified = True
            config.domain_verification_status = DomainVerificationStatus.VERIFIED.value
            config.domain_verified_at = datetime.utcnow()
        else:
            config.domain_verification_status = DomainVerificationStatus.FAILED.value

        session.add(config)
        session.commit()
        session.refresh(config)

        if not verified:
            raise DomainVerificationFailedError(
                f"DNS TXT record not found or does not match. "
                f"Expected TXT record at {txt_record_name} with value {token}"
            )

        return True

    def get_verification_status(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> dict:
        """Get the current domain verification status.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            dict: Status information including domain, verified status, and instructions
        """
        config = self._get_config(session, workspace_id)

        if not config:
            return {
                "configured": False,
                "custom_domain": None,
                "verified": False,
                "status": None,
                "verification_token": None,
                "instructions": None,
            }

        instructions = None
        if config.custom_domain and not config.domain_verified:
            txt_record_name = f"{VERIFICATION_TXT_PREFIX}.{config.custom_domain}"
            instructions = {
                "txt_record_name": txt_record_name,
                "txt_record_value": config.domain_verification_token,
                "cname_record": {
                    "name": config.custom_domain,
                    "value": "app.quillexir.com",
                },
            }

        return {
            "configured": True,
            "custom_domain": config.custom_domain,
            "verified": config.domain_verified,
            "status": config.domain_verification_status,
            "verified_at": config.domain_verified_at,
            "verification_token": config.domain_verification_token,
            "instructions": instructions,
        }

    def remove_custom_domain(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> bool:
        """Remove the custom domain from a workspace.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            bool: True if domain was removed, False if no domain was configured
        """
        config = self._get_config(session, workspace_id)

        if not config or not config.custom_domain:
            return False

        config.custom_domain = None
        config.domain_verified = False
        config.domain_verification_token = None
        config.domain_verification_status = DomainVerificationStatus.PENDING.value
        config.domain_verified_at = None

        session.add(config)
        session.commit()

        return True

    # ==========================================================================
    # DKIM Setup
    # ==========================================================================

    def generate_dkim_keypair(
        self,
        session: Session,
        workspace_id: UUID,
        email_domain: str,
    ) -> dict:
        """Generate a DKIM keypair for email authentication.

        Generates RSA 2048-bit keypair. The public key should be added as
        a DNS TXT record at {selector}._domainkey.{email_domain}.

        Args:
            session: Database session
            workspace_id: Workspace UUID
            email_domain: The email domain (e.g., mail.agency.com)

        Returns:
            dict: Contains selector, public_key (for DNS), and private_key_ref

        Raises:
            DKIMGenerationError: If key generation fails
        """
        try:
            # Generate RSA keypair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )

            # Get public key in PEM format
            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            # Get private key in PEM format
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")

            # Extract just the base64 portion for DNS (remove headers/footers)
            public_key_dns = self._format_public_key_for_dns(public_key_pem)

        except Exception as e:
            raise DKIMGenerationError(f"Failed to generate DKIM keypair: {str(e)}")

        # Get or create config
        config = self._get_or_create_config(session, workspace_id)

        # Generate selector
        selector = WhitelabelConfig.generate_dkim_selector()

        # Update config
        config.email_domain = email_domain
        config.dkim_selector = selector
        config.dkim_public_key = public_key_dns
        # In production, store private key in secure storage and save reference
        # For now, we store a placeholder reference
        config.dkim_private_key_ref = f"vault://dkim/{workspace_id}/{selector}"
        config.email_domain_verified = False

        session.add(config)
        session.commit()
        session.refresh(config)

        # Build DNS record name
        dns_record_name = f"{selector}.{DKIM_TXT_PREFIX}.{email_domain}"

        return {
            "selector": selector,
            "email_domain": email_domain,
            "dns_record_name": dns_record_name,
            "dns_record_value": f"v=DKIM1; k=rsa; p={public_key_dns}",
            "private_key": private_key_pem,  # Return once, should be stored securely
            "instructions": {
                "type": "TXT",
                "name": dns_record_name,
                "value": f"v=DKIM1; k=rsa; p={public_key_dns}",
            },
        }

    def verify_dkim_setup(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> bool:
        """Verify DKIM DNS record is properly configured.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            bool: True if DKIM record is verified

        Raises:
            DomainNotFoundError: If no email domain is configured
            DomainVerificationFailedError: If DKIM DNS verification fails
        """
        config = self._get_config(session, workspace_id)

        if not config or not config.email_domain:
            raise DomainNotFoundError("No email domain configured")

        if not config.dkim_selector or not config.dkim_public_key:
            raise DomainNotFoundError("No DKIM keys generated")

        dns_record_name = (
            f"{config.dkim_selector}.{DKIM_TXT_PREFIX}.{config.email_domain}"
        )

        # Check for the public key in DNS
        # DKIM records contain "p=..." with the public key
        expected_value = config.dkim_public_key

        try:
            answers = dns.resolver.resolve(dns_record_name, "TXT")
            for rdata in answers:
                txt_value = str(rdata).strip('"')
                if expected_value in txt_value:
                    config.email_domain_verified = True
                    session.add(config)
                    session.commit()
                    return True
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoNameservers,
        ):
            pass
        except Exception:
            pass

        raise DomainVerificationFailedError(
            f"DKIM DNS record not found or does not match. "
            f"Expected TXT record at {dns_record_name}"
        )

    def get_dkim_status(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> dict:
        """Get the current DKIM configuration status.

        Args:
            session: Database session
            workspace_id: Workspace UUID

        Returns:
            dict: Status information including email domain, selector, and verification status
        """
        config = self._get_config(session, workspace_id)

        if not config or not config.email_domain:
            return {
                "configured": False,
                "email_domain": None,
                "selector": None,
                "verified": False,
                "instructions": None,
            }

        instructions = None
        if config.dkim_selector and config.dkim_public_key:
            dns_record_name = (
                f"{config.dkim_selector}.{DKIM_TXT_PREFIX}.{config.email_domain}"
            )
            instructions = {
                "type": "TXT",
                "name": dns_record_name,
                "value": f"v=DKIM1; k=rsa; p={config.dkim_public_key}",
            }

        return {
            "configured": True,
            "email_domain": config.email_domain,
            "selector": config.dkim_selector,
            "verified": config.email_domain_verified,
            "instructions": instructions,
        }

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _get_config(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> Optional[WhitelabelConfig]:
        """Get whitelabel config for a workspace."""
        statement = select(WhitelabelConfig).where(
            WhitelabelConfig.workspace_id == workspace_id
        )
        return session.exec(statement).first()

    def _get_or_create_config(
        self,
        session: Session,
        workspace_id: UUID,
    ) -> WhitelabelConfig:
        """Get or create whitelabel config for a workspace."""
        config = self._get_config(session, workspace_id)

        if not config:
            config = WhitelabelConfig(workspace_id=workspace_id)
            session.add(config)
            session.commit()
            session.refresh(config)

        return config

    def _check_dns_txt_record(
        self,
        record_name: str,
        expected_value: str,
    ) -> bool:
        """Check if a DNS TXT record contains the expected value.

        Args:
            record_name: Full DNS record name (e.g., _quillexir-verify.domain.com)
            expected_value: The value to look for in TXT records

        Returns:
            bool: True if record found with expected value
        """
        try:
            answers = dns.resolver.resolve(record_name, "TXT")
            for rdata in answers:
                # TXT records may be quoted
                txt_value = str(rdata).strip('"')
                if txt_value == expected_value:
                    return True
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.resolver.NoNameservers,
        ):
            return False
        except Exception:
            return False

        return False

    def _format_public_key_for_dns(self, pem_key: str) -> str:
        """Format a PEM public key for DNS TXT record.

        Removes headers/footers and newlines to create a single-line base64 string.

        Args:
            pem_key: PEM-formatted public key

        Returns:
            str: Base64-encoded key suitable for DNS TXT record
        """
        # Remove PEM headers and footers
        lines = pem_key.strip().split("\n")
        key_lines = [line for line in lines if not line.startswith("-----")]
        return "".join(key_lines)


# ==========================================================================
# Utility Functions
# ==========================================================================


def get_workspace_by_custom_domain(
    session: Session,
    domain: str,
) -> Optional[UUID]:
    """Look up workspace ID by verified custom domain.

    Used by custom domain middleware to route requests.

    Args:
        session: Database session
        domain: The custom domain to look up

    Returns:
        UUID: Workspace ID if found, None otherwise
    """
    statement = select(WhitelabelConfig).where(
        WhitelabelConfig.custom_domain == domain,
        WhitelabelConfig.domain_verified,
        WhitelabelConfig.is_active,
    )
    config = session.exec(statement).first()

    if config:
        return config.workspace_id

    return None
