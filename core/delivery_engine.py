import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any, Callable, Awaitable
from abc import ABC, abstractmethod
import httpx
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DeliveryConfig:
    """Configuration for the delivery engine."""
    providers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    region_routing: Dict[str, List[str]] = field(default_factory=dict)
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    default_region: str = "global"
    webhook_secret: Optional[str] = None


class Channel(ABC):
    """Abstract base class for delivery channels."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    async def send(self, to: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message via this channel.
        Returns a dict with at least 'status' and 'message_id'.
        """
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate that the channel credentials work."""
        pass


class WhatsAppWhapiChannel(Channel):
    """WhatsApp via Whapi (https://whapi.cloud)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.whapi.cloud")
        self.timeout = config.get("timeout", 30)
        self._http = httpx.AsyncClient(timeout=self.timeout)

    async def send(self, to: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send via Whapi message endpoint."""
        if not self.api_key:
            raise ValueError("Whapi API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": to,
            "body": message,
            "type": "text",
        }
        # Optionally add template or media
        if kwargs.get("type") == "template":
            payload["type"] = "template"
            payload["template"] = kwargs.get("template_data", {})

        url = f"{self.base_url}/messages"
        try:
            response = await self._http.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {
                "status": "sent",
                "message_id": data.get("id") or data.get("message_id"),
                "channel": self.name,
                "provider": "whapi",
                "raw": data,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Whapi HTTP error: {e.response.status_code} {e.response.text}")
            raise RuntimeError(f"Whapi send failed: {e}") from e
        except Exception as e:
            logger.error(f"Whapi send error: {e}")
            raise

    async def validate_credentials(self) -> bool:
        """Check if API key is valid by querying account info."""
        if not self.api_key:
            return False
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = await self._http.get(f"{self.base_url}/account", headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


class WhatsAppMetaChannel(Channel):
    """WhatsApp via Meta Cloud API (Business Platform)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.phone_number_id = config.get("phone_number_id")
        self.access_token = config.get("access_token")
        self.base_url = config.get("base_url", "https://graph.facebook.com/v19.0")
        self.timeout = config.get("timeout", 30)
        self._http = httpx.AsyncClient(timeout=self.timeout)

    async def send(self, to: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send via WhatsApp Business API."""
        if not self.phone_number_id or not self.access_token:
            raise ValueError("Meta WhatsApp missing phone_number_id or access_token")

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        # Prepend country code if not present? Assume 'to' is full number.
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
        }
        if kwargs.get("type") == "template":
            payload["type"] = "template"
            payload["template"] = kwargs.get("template_data", {})
        else:
            payload["type"] = "text"
            payload["text"] = {"body": message}

        to_formatted = to.lstrip("+")
        payload["to"] = to_formatted
        try:
            logger.info(f"Meta API payload to={to_formatted} text={message[:80]}")
            response = await self._http.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            msg_id = data.get("messages", [{}])[0].get("id")
            logger.info(f"Meta API response: {data}")
            return {
                "status": "sent",
                "message_id": msg_id,
                "channel": self.name,
                "provider": "meta",
                "raw": data,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Meta WhatsApp HTTP error: {e.response.status_code} body={e.response.text} to={to}")
            raise RuntimeError(f"Meta WhatsApp send failed: {e}") from e
        except Exception as e:
            logger.error(f"Meta WhatsApp send error: {e}")
            raise

    async def validate_credentials(self) -> bool:
        """Validate by fetching phone number info."""
        if not self.phone_number_id or not self.access_token:
            return False
        url = f"{self.base_url}/{self.phone_number_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = await self._http.get(url, headers=headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


class TwilioChannel(Channel):
    """SMS via Twilio."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.account_sid = config.get("account_sid")
        self.auth_token = config.get("auth_token")
        self.from_number = config.get("from_number")
        self.base_url = config.get("base_url", "https://api.twilio.com/2010-04-01")
        self.timeout = config.get("timeout", 30)
        self._http = httpx.AsyncClient(timeout=self.timeout)

    async def send(self, to: str, message: str, **kwargs) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        if not self.account_sid or not self.auth_token or not self.from_number:
            raise ValueError("Twilio missing account_sid, auth_token, or from_number")

        url = f"{self.base_url}/Accounts/{self.account_sid}/Messages.json"
        auth = (self.account_sid, self.auth_token)
        data = {
            "To": to,
            "From": self.from_number,
            "Body": message,
        }
        # Optionally add media URLs
        if kwargs.get("media_url"):
            data["MediaUrl"] = kwargs["media_url"]

        try:
            response = await self._http.post(url, data=data, auth=auth)
            response.raise_for_status()
            resp_json = response.json()
            return {
                "status": "sent",
                "message_id": resp_json.get("sid"),
                "channel": self.name,
                "provider": "twilio",
                "raw": resp_json,
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"Twilio HTTP error: {e.response.status_code} {e.response.text}")
            raise RuntimeError(f"Twilio send failed: {e}") from e
        except Exception as e:
            logger.error(f"Twilio send error: {e}")
            raise

    async def validate_credentials(self) -> bool:
        """Validate by fetching account info."""
        if not self.account_sid or not self.auth_token:
            return False
        url = f"{self.base_url}/Accounts/{self.account_sid}"
        auth = (self.account_sid, self.auth_token)
        try:
            resp = await self._http.get(url, auth=auth, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


class DeliveryEngine:
    """
    Multi-channel delivery system with region-based routing and webhook support.
    """

    def __init__(self, config: DeliveryConfig):
        self.config = config
        self.channels: Dict[str, Channel] = {}
        self._initialize_channels()
        self._pending_retries: Dict[str, asyncio.Task] = {}
        self._shutdown = False

    def _initialize_channels(self):
        """Instantiate channel objects from config."""
        for name, provider_config in self.config.providers.items():
            provider_type = provider_config.get("type")
            if provider_type == "whatsapp_whapi":
                self.channels[name] = WhatsAppWhapiChannel(provider_config)
            elif provider_type == "whatsapp_meta":
                self.channels[name] = WhatsAppMetaChannel(provider_config)
            elif provider_type == "twilio":
                self.channels[name] = TwilioChannel(provider_config)
            else:
                logger.warning(f"Unknown provider type '{provider_type}' for channel '{name}'")
        logger.info(f"Initialized {len(self.channels)} channels: {list(self.channels.keys())}")

    async def send(
        self,
        to: str,
        message: str,
        region: Optional[str] = None,
        channel_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a message through the appropriate channel.

        Args:
            to: Recipient identifier (phone number, etc.)
            message: Message content.
            region: Region for routing (e.g., 'uae', 'global').
            channel_name: Directly specify channel; overrides routing.
            metadata: Additional metadata for logging/tracking.
            kwargs: Additional arguments passed to channel send.

        Returns:
            Dict with delivery result.
        """
        if self._shutdown:
            raise RuntimeError("Engine is shutting down")

        if not channel_name:
            region = region or self.config.default_region
            channel_name = self._route_channel(region)

        if channel_name not in self.channels:
            raise ValueError(f"Channel '{channel_name}' not configured")

        channel = self.channels[channel_name]
        logger.info(f"Sending via {channel_name} to {to} (region={region})")

        # Attempt with retries
        last_exception = None
        for attempt in range(1, self.config.retry_max_attempts + 1):
            try:
                result = await channel.send(to, message, **kwargs)
                result["channel_name"] = channel_name
                result["region"] = region
                result["metadata"] = metadata or {}
                result["attempt"] = attempt
                logger.info(f"Successfully sent via {channel_name} (attempt {attempt})")
                return result
            except Exception as e:
                last_exception = e
                delay = min(
                    self.config.retry_base_delay * (2 ** (attempt - 1)),
                    self.config.retry_max_delay,
                )
                logger.warning(
                    f"Send failed (attempt {attempt}/{self.config.retry_max_attempts}) "
                    f"via {channel_name}: {e}. Retrying in {delay:.2f}s"
                )
                if attempt < self.config.retry_max_attempts:
                    await asyncio.sleep(delay)

        # All retries exhausted
        error_msg = f"All {self.config.retry_max_attempts} attempts failed for {channel_name}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from last_exception

    def _route_channel(self, region: str) -> str:
        """Determine which channel to use based on region routing."""
        region_lower = region.lower()
        routing = self.config.region_routing
        # Direct match
        if region_lower in routing:
            candidates = routing[region_lower]
        else:
            # Fallback to default region routing
            default_routing = routing.get(self.config.default_region, [])
            if not default_routing:
                # If no default, just pick first configured channel
                if self.channels:
                    return next(iter(self.channels))
                else:
                    raise RuntimeError("No channels configured")
            candidates = default_routing

        # Filter to available channels
        available = [ch for ch in candidates if ch in self.channels]
        if not available:
            # fallback to any available
            available = list(self.channels.keys())
            if not available:
                raise RuntimeError("No channels available")
        # For now, pick first (could implement load balancing)
        return available[0]

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        source_type: str = "whatsapp",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process an incoming webhook to trigger a delivery.
        This is a simple example: expects a 'to' and 'message' in payload.

        Args:
            payload: Webhook payload (parsed JSON).
            headers: Optional headers (for verification).
            source_type: Type of webhook (whatsapp, twilio, etc.).
            region: Optional region override.

        Returns:
            Delivery result.
        """
        # Optionally verify webhook signature
        if self.config.webhook_secret:
            # Implement signature verification if needed
            pass

        # Extract recipient and message - customize based on source_type
        if source_type == "whatsapp":
            # Example for WhatsApp webhook: 'from' and 'text'
            to = payload.get("from") or payload.get("sender")
            message = payload.get("text") or payload.get("body")
            # Also could extract region from payload
        elif source_type == "twilio":
            to = payload.get("From")
            message = payload.get("Body")
        else:
            to = payload.get("recipient") or payload.get("to")
            message = payload.get("message") or payload.get("body")

        if not to or not message:
            raise ValueError("Webhook payload missing 'to' or 'message'")

        # Optionally use a different channel based on source_type
        channel_name = None
        if source_type == "whatsapp":
            # Could route to WhatsApp channel
            channel_name = self._route_channel(region or "uae")
        elif source_type == "twilio":
            # Could route to SMS channel
            channel_name = self._route_channel(region or "global")

        result = await self.send(to, message, region=region, channel_name=channel_name)
        return result

    async def shutdown(self):
        """Graceful shutdown: close HTTP clients and cancel pending retries."""
        self._shutdown = True
        for channel in self.channels.values():
            if hasattr(channel, "_http"):
                await channel._http.aclose()
        logger.info("DeliveryEngine shut down")