import logging

import httpx

from smartsales.models import SmartSalesLocation

log = logging.getLogger("smartsales.repository")

_BASE_URL = "https://proxy-smartsales.easi.net/proxy/rest"


class SmartSalesRepository:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # Locations
    # ------------------------------------------------------------------

    async def get_location(self, uid: str) -> SmartSalesLocation:
        """Retrieve a single location by its uid."""
        url = f"{_BASE_URL}/api/v3/location/{uid}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=self._headers())
            r.raise_for_status()
        return _parse_location(r.json())

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

        url = f"{_BASE_URL}/api/v3/location/list"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()

        data = r.json()
        entries = data.get("entries") or []
        return {
            "locations": [_parse_location(e).model_dump() for e in entries],
            "nextPageToken": data.get("nextPageToken"),
            "resultSizeEstimate": data.get("resultSizeEstimate"),
        }


def _parse_location(r: dict) -> SmartSalesLocation:
    return SmartSalesLocation(
        uid=r.get("uid", ""),
        code=r.get("code"),
        name=r.get("name"),
        city=r.get("city"),
        zip=r.get("zip"),
        country=r.get("country"),
        external_id=r.get("externalId"),
        street=r.get("street"),
        latitude=r.get("latitude"),
        longitude=r.get("longitude"),
        vat_number=r.get("vatNumber"),
        last_visit_date=r.get("lastVisitDate"),
        last_order_date=r.get("lastOrderDate"),
        tags=r.get("tags"),
        deleted=r.get("deleted"),
    )
