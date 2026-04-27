import json
import logging

import httpx

log = logging.getLogger("smartsales.repository")

_BASE_URL = "https://proxy-smartsales.easi.net/proxy/rest"
_SS_TIMEOUT = 30.0  # seconds; SmartSales API calls exceeding this are cancelled

_field_cache: dict[str, list] = {}


class SmartSalesRepository:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=_SS_TIMEOUT) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()
        return r

    def _validate_query(self, q: str | None, cache_key: str) -> dict | None:
        if not q or cache_key not in _field_cache:
            return None
        try:
            valid_fields = {f["fieldName"] for f in _field_cache[cache_key]}
            invalid = set(json.loads(q).keys()) - valid_fields
            if invalid:
                return {"error": f"Unknown filter field(s): {sorted(invalid)}. Valid fields: {sorted(valid_fields)}"}
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _validate_sort(self, s: str | None, cache_key: str) -> dict | None:
        if not s or cache_key not in _field_cache:
            return None
        sort_field = s.split(":")[0]
        valid = {f["keyName"] for f in _field_cache[cache_key]}
        if sort_field not in valid:
            return {"error": f"Unknown sort field: '{sort_field}'. Valid fields: {sorted(valid)}"}
        return None

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    async def get_location(self, uid: str) -> dict:
        """Retrieve a single location by its uid."""
        r = await self._get(f"{_BASE_URL}/api/v3/location/{uid}")
        return r.json()

    async def list_locations(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "simple",
        d: str | None = None,
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales locations — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"city":"eq:Knokke"}'
        s               — sort expression, e.g. "name:asc"
        p               — projection: "minimal", "simple", "fullWithColor", "full"
        d               — comma-separated field list, e.g. "code,name,city,country"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default True)
        """
        params = {k: v for k, v in {"q": q, "s": s, "p": p, "d": d, "nextPageToken": nextPageToken}.items() if v is not None}
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        log.info("[list_locations] params=%s", params)

        if err := self._validate_query(q, "location_queryable"):
            return err
        if err := self._validate_sort(s, "location_sortable"):
            return err

        r = await self._get(f"{_BASE_URL}/api/v3/location/list", params)
        data = r.json()
        return {
            "locations": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def list_displayable_fields(self) -> list:
        """Return the fields that can be displayed in a location list view."""
        if "location_displayable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/location/list/displayableFields")
            _field_cache["location_displayable"] = r.json()
        return _field_cache["location_displayable"]

    async def list_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_locations (q param)."""
        if "location_queryable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/location/list/queryableFields")
            _field_cache["location_queryable"] = r.json()
        return _field_cache["location_queryable"]

    async def list_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_locations (s param)."""
        if "location_sortable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/location/list/sortableFields")
            _field_cache["location_sortable"] = r.json()
        return _field_cache["location_sortable"]

    async def warm_field_cache(self) -> None:
        """Pre-fetch all field lists and store in the module-level cache."""
        await self.list_displayable_fields()
        await self.list_queryable_fields()
        await self.list_sortable_fields()
        await self.list_catalog_displayable_fields()
        await self.list_catalog_queryable_fields()
        await self.list_catalog_sortable_fields()
        await self.list_order_displayable_fields()
        await self.list_order_queryable_fields()
        await self.list_order_sortable_fields()
        log.info(
            "Field cache warmed: loc_displayable=%d, loc_queryable=%d, loc_sortable=%d, "
            "cat_displayable=%d, cat_queryable=%d, cat_sortable=%d, "
            "ord_displayable=%d, ord_queryable=%d, ord_sortable=%d",
            len(_field_cache["location_displayable"]),
            len(_field_cache["location_queryable"]),
            len(_field_cache["location_sortable"]),
            len(_field_cache["catalog_displayable"]),
            len(_field_cache["catalog_queryable"]),
            len(_field_cache["catalog_sortable"]),
            len(_field_cache["order_displayable"]),
            len(_field_cache["order_queryable"]),
            len(_field_cache["order_sortable"]),
        )

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    async def get_catalog_item(self, uid: str) -> dict:
        """Retrieve a single catalog item by its uid."""
        r = await self._get(f"{_BASE_URL}/api/v3/catalog/item/{uid}")
        return r.json()

    async def get_catalog_group(self, uid: str) -> dict:
        """Retrieve a single catalog group by its uid."""
        r = await self._get(f"{_BASE_URL}/api/v3/catalog/group/{uid}")
        return r.json()

    async def list_catalog_items(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "simple",
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales catalog items — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"name":"contains:widget"}'
        s               — sort expression, e.g. "name:asc"
        p               — projection: "minimal", "simple", "full", "simpleWithDiscount", "fullWithDiscount"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default False)
        """
        params = {k: v for k, v in {"q": q, "s": s, "p": p, "nextPageToken": nextPageToken}.items() if v is not None}
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        log.info("list_catalog_items params=%s", params)

        if err := self._validate_query(q, "catalog_queryable"):
            return err
        if err := self._validate_sort(s, "catalog_sortable"):
            return err

        r = await self._get(f"{_BASE_URL}/api/v3/catalog/list", params)
        data = r.json()
        return {
            "items": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def list_catalog_displayable_fields(self) -> list:
        """Return the fields that can be displayed in a catalog item list view."""
        if "catalog_displayable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/catalog/list/displayableFields")
            _field_cache["catalog_displayable"] = r.json()
        return _field_cache["catalog_displayable"]

    async def list_catalog_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_catalog_items (q param)."""
        if "catalog_queryable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/catalog/list/queryableFields")
            _field_cache["catalog_queryable"] = r.json()
        return _field_cache["catalog_queryable"]

    async def list_catalog_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_catalog_items (s param)."""
        if "catalog_sortable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/catalog/list/sortableFields")
            _field_cache["catalog_sortable"] = r.json()
        return _field_cache["catalog_sortable"]

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    async def get_order(self, uid: str) -> dict:
        """Retrieve a single order by its uid."""
        r = await self._get(f"{_BASE_URL}/api/v3/order/{uid}")
        return r.json()

    async def list_orders(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "simple",
        nextPageToken: str | None = None,
        skipResultSize: bool | None = False,
    ) -> dict:
        """Query SmartSales orders — raw API params passed straight through.

        q               — JSON filter string, e.g. '{"type":"eq:ORDER"}'
        s               — sort expression, e.g. "date:desc"
        p               — projection: "minimal", "simple", "full", "custom"
        nextPageToken   — pagination token from previous response
        skipResultSize  — skip total count calculation (default False)
        """
        params = {k: v for k, v in {"q": q, "s": s, "p": p, "nextPageToken": nextPageToken}.items() if v is not None}
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        log.info("list_orders params=%s", params)

        if err := self._validate_query(q, "order_queryable"):
            return err
        if err := self._validate_sort(s, "order_sortable"):
            return err

        r = await self._get(f"{_BASE_URL}/api/v3/order/list", params)
        data = r.json()
        return {
            "orders": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def get_order_configuration(self) -> dict:
        """Retrieve the global order configuration."""
        r = await self._get(f"{_BASE_URL}/api/v3/order/configuration")
        return r.json()

    async def list_approbation_statuses(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "minimal",
        nextPageToken: str | None = None,
    ) -> dict:
        """Query SmartSales order approbation statuses."""
        params = {k: v for k, v in {"q": q, "s": s, "p": p, "nextPageToken": nextPageToken}.items() if v is not None}

        log.info("list_approbation_statuses params=%s", params)

        r = await self._get(f"{_BASE_URL}/api/v3/order/approbation/status/list", params)
        data = r.json()
        return {
            "statuses": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }

    async def get_approbation_status(self, uid: str) -> dict:
        """Retrieve a single approbation status by its uid."""
        r = await self._get(f"{_BASE_URL}/api/v3/order/approbation/status/{uid}")
        return r.json()

    async def list_order_displayable_fields(self) -> list:
        """Return the fields that can be displayed in an order list view."""
        if "order_displayable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/order/list/displayableFields")
            _field_cache["order_displayable"] = r.json()
        return _field_cache["order_displayable"]

    async def list_order_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_orders (q param)."""
        if "order_queryable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/order/list/queryableFields")
            _field_cache["order_queryable"] = r.json()
        return _field_cache["order_queryable"]

    async def list_order_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_orders (s param)."""
        if "order_sortable" not in _field_cache:
            r = await self._get(f"{_BASE_URL}/api/v3/order/list/sortableFields")
            _field_cache["order_sortable"] = r.json()
        return _field_cache["order_sortable"]
