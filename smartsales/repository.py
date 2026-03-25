import json
import logging

import httpx

log = logging.getLogger("smartsales.repository")

_BASE_URL = "https://proxy-smartsales.easi.net/proxy/rest"

_field_cache: dict[str, list] = {}


class SmartSalesRepository:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    async def get_location(self, uid: str) -> dict:
        """Retrieve a single location by its uid."""
        url = f"{_BASE_URL}/api/v3/location/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return r.json()

    async def list_locations(
        self,
        q: str | None = None,
        s: str | None = None,
        p: str | None = "fullWithColor",
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

        params: dict = {}
        if q is not None:
            params["q"] = q
        if s is not None:
            params["s"] = s
        if p is not None:
            params["p"] = p
        if d is not None:
            params["d"] = d
        if nextPageToken is not None:
            params["nextPageToken"] = nextPageToken
        if skipResultSize is not None:
            params["skipResultSize"] = str(skipResultSize).lower()

        

        log.info("list_locations params=%s", params)

        if _field_cache:
            if q is not None:
                try:
                    q_fields = set(json.loads(q).keys())
                    valid_fields = {f["fieldName"] for f in _field_cache.get("queryable", [])}
                    invalid = q_fields - valid_fields
                    if invalid:
                        return {"error": f"Unknown filter field(s): {sorted(invalid)}. Valid fields: {sorted(valid_fields)}"}
                except (json.JSONDecodeError, KeyError):
                    pass

            if s is not None:
                sort_field = s.split(":")[0]
                valid_sort = {f["keyName"] for f in _field_cache.get("sortable", [])}
                if sort_field not in valid_sort:
                    return {"error": f"Unknown sort field: '{sort_field}'. Valid fields: {sorted(valid_sort)}"}

        url = f"{_BASE_URL}/api/v3/location/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        return {
            "locations": data.get("entries") or [],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }


    async def list_displayable_fields(self) -> list:
        """Return the fields that can be displayed in a location list view."""
        if "displayable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/displayableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["displayable"] = r.json()
        return _field_cache["displayable"]

    async def list_queryable_fields(self) -> list:
        """Return the fields that can be used as filters in list_locations (q param)."""
        if "queryable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/queryableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["queryable"] = r.json()
        return _field_cache["queryable"]

    async def list_sortable_fields(self) -> list:
        """Return the fields that can be used for sorting in list_locations (s param)."""
        if "sortable" not in _field_cache:
            url = f"{_BASE_URL}/api/v3/location/list/sortableFields"
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.get(url, headers=self._headers())
                r.raise_for_status()
            _field_cache["sortable"] = r.json()
        return _field_cache["sortable"]

    async def warm_field_cache(self) -> None:
        """Pre-fetch all field lists and store in the module-level cache."""
        await self.list_displayable_fields()
        await self.list_queryable_fields()
        await self.list_sortable_fields()
        log.info("Field cache warmed: displayable=%d, queryable=%d, sortable=%d",
                 len(_field_cache["displayable"]),
                 len(_field_cache["queryable"]),
                 len(_field_cache["sortable"]))


