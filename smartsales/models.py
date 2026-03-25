from pydantic import BaseModel


class SmartSalesLocation(BaseModel):
    """
    SmartSales Location record.

    Base fields (always returned): uid, code, name, city, zip, country
    Optional fields: external_id, street, latitude, longitude, vat_number,
                     last_visit_date, last_order_date, tags, deleted
    """
    uid: str
    code: str | None
    name: str | None
    city: str | None = None
    zip: str | None = None
    country: str | None = None
    external_id: str | None = None
    street: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    vat_number: str | None = None
    last_visit_date: str | None = None
    last_order_date: str | None = None
    tags: list[str] | None = None
    deleted: bool | None = None
