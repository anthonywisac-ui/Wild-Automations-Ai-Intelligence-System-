import hashlib
import json
import ssl
from typing import Any, Dict, List, Optional, Union

ssl._create_default_https_context = ssl._create_unverified_context

from supabase import Client, create_client


class SupabaseDB:
    """Async Supabase database layer with MD5 deduplication."""

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        table_name: str,
        schema: str = "public",
        timeout: int = 30,
    ) -> None:
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.table_name = table_name
        self.schema = schema
        self.timeout = timeout
        # supabase-py 2.x: create_client takes only url + key
        self.client: Client = create_client(supabase_url, supabase_key)

    @staticmethod
    def _compute_hash(data: Dict[str, Any]) -> str:
        """
        Compute MD5 hash from a normalized JSON representation.

        Args:
            data: Dictionary to hash.

        Returns:
            MD5 hex digest string.
        """
        normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    async def _execute(self, fn, *args, **kwargs):
        """Run a synchronous supabase-py 2.x call in a thread executor."""
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
        except Exception as e:
            raise RuntimeError(f"Supabase operation failed: {e}") from e

    async def insert(
        self,
        raw_data: Dict[str, Any],
        normalized_data: Dict[str, Any],
        *,
        skip_if_exists: bool = True,
    ) -> Dict[str, Any]:
        """
        Insert a record, optionally skipping if a duplicate hash exists.

        Args:
            raw_data: Raw scraped data (stored as JSONB).
            normalized_data: Normalized structured data (stored as JSONB).
            skip_if_exists: If True, skip insertion when hash exists; else raise.

        Returns:
            Dict with status and data.
        """
        hash_val = self._compute_hash(normalized_data)

        # Check for existing hash
        if skip_if_exists:
            resp = await self._execute(
                self.client.table(self.table_name)
                .select("hash", count="exact")
                .eq("hash", hash_val)
                .limit(1)
                .execute
            )
            if resp.count and resp.count > 0:
                return {"status": "skipped", "hash": hash_val}

        payload = {
            "hash": hash_val,
            "raw_data": raw_data,
            "normalized_data": normalized_data,
        }
        resp = await self._execute(
            self.client.table(self.table_name).insert(payload).execute
        )
        return {"status": "inserted", "data": resp.data[0] if resp.data else None}

    async def upsert(
        self,
        raw_data: Dict[str, Any],
        normalized_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Upsert a record based on hash conflict.

        Args:
            raw_data: Raw scraped data.
            normalized_data: Normalized structured data.

        Returns:
            Dict with status and data.
        """
        hash_val = self._compute_hash(normalized_data)
        payload = {
            "hash": hash_val,
            "raw_data": raw_data,
            "normalized_data": normalized_data,
        }
        resp = await self._execute(
            self.client.table(self.table_name)
            .upsert(payload, on_conflict="hash")
            .execute
        )
        return {"status": "upserted", "data": resp.data[0] if resp.data else None}

    async def get_by_hash(self, hash_val: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record by its MD5 hash.

        Args:
            hash_val: MD5 hash string.

        Returns:
            Record dict or None if not found.
        """
        resp = await self._execute(
            self.client.table(self.table_name)
            .select("*")
            .eq("hash", hash_val)
            .limit(1)
            .execute
        )
        return resp.data[0] if resp.data else None

    async def get_by_id(self, id_: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record by its primary key.

        Args:
            id_: Primary key value.

        Returns:
            Record dict or None if not found.
        """
        resp = await self._execute(
            self.client.table(self.table_name)
            .select("*")
            .eq("id", id_)
            .limit(1)
            .execute
        )
        return resp.data[0] if resp.data else None

    # ──────────────────────────────────────────────────────────────────────────
    # Search
    # ──────────────────────────────────────────────────────────────────────────

    async def search(
        self,
        domain: str = "jobs",
        query: str = "",
        location: str = "",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Keyword search across bot_alerts via ilike on normalized_data.
        Returns up to `limit` records matching query + optional location.
        """
        filters = filters or {}
        try:
            q = (
                self.client.table(self.table_name)
                .select("id, normalized_data, raw_data")
                .limit(limit)
            )
            if query:
                q = q.ilike("normalized_data->>title", f"%{query}%")
            if location:
                q = q.ilike("normalized_data->>location", f"%{location}%")
            resp = await self._execute(q.execute)
            rows = resp.data or []
            out = []
            for row in rows:
                nd = row.get("normalized_data") or {}
                nd["id"] = row.get("id")
                nd["domain"] = domain
                out.append(nd)
            return out
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("db.search error: %s", exc)
            return []

    async def load_all(self, limit: int = 5000) -> List[Dict[str, Any]]:
        """Return all stored records' normalized_data (for cold-start hydration).
        Paginates so large tables come back fully."""
        out: List[Dict[str, Any]] = []
        page = 1000
        offset = 0
        while offset < limit:
            resp = await self._execute(
                self.client.table(self.table_name)
                .select("normalized_data")
                .range(offset, offset + page - 1)
                .execute
            )
            rows = resp.data or []
            for row in rows:
                nd = row.get("normalized_data")
                if isinstance(nd, dict):
                    out.append(nd)
            if len(rows) < page:
                break
            offset += page
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # User management (requires `users` table in Supabase)
    # ──────────────────────────────────────────────────────────────────────────

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        resp = await self._execute(
            self.client.table("users").select("*").eq("email", email).limit(1).execute
        )
        return resp.data[0] if resp.data else None

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        resp = await self._execute(
            self.client.table("users").insert(user_data).execute
        )
        return resp.data[0] if resp.data else user_data

    async def list_users(
        self, page: int = 1, limit: int = 20, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        offset = (page - 1) * limit
        q = self.client.table("users").select("id, email, phone, created_at, is_active").range(offset, offset + limit - 1)
        if search:
            q = q.ilike("email", f"%{search}%")
        resp = await self._execute(q.execute)
        return resp.data or []

    # ──────────────────────────────────────────────────────────────────────────
    # Saved items (requires `saved_items` table in Supabase)
    # ──────────────────────────────────────────────────────────────────────────

    async def save_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        payload = {"user_id": user_id, "item_id": item_id}
        resp = await self._execute(
            self.client.table("saved_items").upsert(payload, on_conflict="user_id,item_id").execute
        )
        return resp.data[0] if resp.data else payload

    async def get_saved_items(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        resp = await self._execute(
            self.client.table("saved_items")
            .select("item_id, saved_at, bot_alerts(normalized_data)")
            .eq("user_id", user_id)
            .limit(limit)
            .execute
        )
        rows = resp.data or []
        out = []
        for row in rows:
            nd = (row.get("bot_alerts") or {}).get("normalized_data") or {}
            nd["item_id"] = row.get("item_id")
            out.append(nd)
        return out

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return await self.get_by_id(item_id)

    # ──────────────────────────────────────────────────────────────────────────
    # Health check
    # ──────────────────────────────────────────────────────────────────────────

    async def ping(self) -> bool:
        """Quick connectivity check."""
        resp = await self._execute(
            self.client.table(self.table_name).select("id").limit(1).execute
        )
        return True  # if execute didn't raise, we're connected

    async def delete_by_hash(self, hash_val: str) -> int:
        """
        Delete all records with a given hash.

        Args:
            hash_val: MD5 hash string.

        Returns:
            Number of deleted records.
        """
        resp = await self._execute(
            self.client.table(self.table_name)
            .delete()
            .eq("hash", hash_val)
            .execute
        )
        return len(resp.data) if resp.data else 0