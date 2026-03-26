from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    """Base model that accepts camelCase JSON fields from the SmartSales API."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------------------
# Embedded / shared sub-objects
# ---------------------------------------------------------------------------

class EmbeddedUser(_CamelModel):
    uid: str | None = None
    username: str | None = None
    firstname: str | None = None
    lastname: str | None = None


class EmbeddedLocation(_CamelModel):
    uid: str | None = None
    code: str | None = None
    external_id: str | None = None
    name: str | None = None


class EmbeddedPerson(_CamelModel):
    uid: str | None = None
    code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    language: str | None = None


class EmbeddedUserGroup(_CamelModel):
    uid: str | None = None
    name: str | None = None
    system: bool | None = None


class EmbeddedAttribute(_CamelModel):
    name: str | None = None
    value: str | None = None


class EmbeddedDocument(_CamelModel):
    uid: str | None = None
    name: str | None = None


class EmbeddedImage(_CamelModel):
    uid: str | None = None
    code: str | None = None
    name: str | None = None
    extension: str | None = None
    tech_server_update_date: str | None = None
    last_modified: str | None = None


class EmbeddedCatalogItemGroup(_CamelModel):
    uid: str | None = None
    code: str | None = None
    title: str | None = None
    parent: EmbeddedCatalogItemGroup | None = None


# ---------------------------------------------------------------------------
# Order line items and modifiers
# ---------------------------------------------------------------------------

class AutoDiscount(_CamelModel):
    code: str | None = None
    discount: float | None = None
    discount_type: str | None = None
    discount_is_percentage: bool | None = None
    discount_is_fixed_discount: bool | None = None
    discount_is_free_quantity: bool | None = None
    discount_is_fixed_price: bool | None = None


class OrderItem(_CamelModel):
    code: str | None = None
    description: str | None = None
    quantity: int | None = None
    price: float | None = None
    sales_unit: int | None = None
    packaging_unit: int | None = None
    measure: float | None = None
    unit_of_measure: str | None = None
    discount: float | None = None
    discount_is_percentage: bool | None = None
    total_price: float | None = None
    final_discount_price: float | None = None
    free: bool | None = None
    auto_discounts: list[AutoDiscount] | None = None
    has_auto_discounts: bool | None = None
    has_overridden_auto_discount: bool | None = None
    comment: str | None = None
    free_reason: str | None = None
    price_manually_set: bool | None = None


class TotalModifier(_CamelModel):
    name: str | None = None
    value: float | None = None
    value_is_percentage: bool | None = None


# ---------------------------------------------------------------------------
# Order configuration DTOs
# ---------------------------------------------------------------------------

class OrderConfigItemField(_CamelModel):
    format: str | None = None
    name: str | None = None
    type: str | None = None
    default_value: str | None = None
    free: bool | None = None


class OrderConfigSectionField(_CamelModel):
    format: str | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    location_attribute_name: str | None = None
    mandatory: bool | None = None
    read_only: bool | None = None
    highlight: bool | None = None


class OrderConfigSection(_CamelModel):
    name: str | None = None
    display_name: str | None = None
    read_only: bool | None = None
    fields: list[OrderConfigSectionField] | None = None


class SmartSalesOrderConfiguration(_CamelModel):
    comment_allowed: bool | None = None
    customer_vat_number_required: bool | None = None
    discount_per_item_allowed: str | None = None
    global_discount_allowed: str | None = None
    has_disclaimer: bool | None = None
    show_signature_input: bool | None = None
    show_vat_per_item: bool | None = None
    signature_required: bool | None = None
    total_modifiers: list[str] | None = None
    items: list[OrderConfigItemField] | None = None
    sections: list[OrderConfigSection] | None = None


# ---------------------------------------------------------------------------
# Approbation status
# ---------------------------------------------------------------------------

class SmartSalesApprobationStatus(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    type: str | None = None
    code: str | None = None
    position: int | None = None
    icon_code: str | None = None
    icon_color: str | None = None
    percent_of_success: float | None = None
    terminal: bool | None = None
    secured: bool | None = None
    system: bool | None = None
    deleted: bool | None = None
    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    mail_subject: dict[str, str] | None = None
    mail_body: dict[str, str] | None = None
    notification_types: list[str] | None = None
    security_permissions: list[EmbeddedUserGroup] | None = None


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class SmartSalesOrder(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    tech_client_creation_date: str | None = None
    tech_client_update_date: str | None = None
    tech_creation_user_uid: str | None = None
    tech_update_user_uid: str | None = None
    tech_creation_user: EmbeddedUser | None = None
    tech_update_user: EmbeddedUser | None = None
    to_synchronize: bool | None = None
    date: str | None = None
    internal_reference: str | None = None
    external_reference: str | None = None
    version_key: str | None = None
    version_history: bool | None = None
    has_manual_discount: bool | None = None
    has_new_manual_discount: bool | None = None
    comments: str | None = None
    locale: str | None = None
    total: float | None = None
    subtotal: float | None = None
    total_quantity: int | None = None
    type: str | None = None
    approbation_status: str | None = None
    user: EmbeddedUser | None = None
    customer: EmbeddedLocation | None = None
    customer_email: str | None = None
    supplier: EmbeddedLocation | None = None
    supplier_email: str | None = None
    person: EmbeddedPerson | None = None
    commented: bool | None = None
    signature_image: list[str] | None = None
    company_logo_image: list[str] | None = None
    discount_visible: bool | None = None
    form: dict[str, str] | None = None
    custom_fields: dict[str, str] | None = None
    items: list[OrderItem] | None = None
    has_auto_discounts: bool | None = None
    auto_discounts: list[AutoDiscount] | None = None
    total_modifiers: list[TotalModifier] | None = None
    offer: bool | None = None


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

class SmartSalesLocation(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    tech_client_creation_date: str | None = None
    tech_client_update_date: str | None = None
    tech_creation_user_uid: str | None = None
    tech_update_user_uid: str | None = None
    tech_creation_user: EmbeddedUser | None = None
    tech_update_user: EmbeddedUser | None = None
    to_synchronize: bool | None = None
    code: str | None = None
    external_id: str | None = None
    street: str | None = None
    city: str | None = None
    zip: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    name: str | None = None
    vat_number: str | None = None
    deleted: bool | None = None
    suppliers: list[EmbeddedLocation] | None = None
    attributes: list[EmbeddedAttribute] | None = None
    users: list[EmbeddedUser] | None = None
    groups: list[EmbeddedUserGroup] | None = None
    documents: list[EmbeddedDocument] | None = None
    tags: list[str] | None = None
    commented: bool | None = None
    last_visit_date: str | None = None
    last_order_date: str | None = None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class SmartSalesCatalogItemGroup(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    code: str | None = None
    title: str | None = None
    position: int | None = None
    image_code: str | None = None
    image: EmbeddedImage | None = None
    generate_thumbnail: bool | None = None
    parent: EmbeddedCatalogItemGroup | None = None
    deleted: bool | None = None
    type: str | None = None


class SmartSalesCatalogItem(_CamelModel):
    uid: str | None = None
    tech_server_creation_date: str | None = None
    tech_server_update_date: str | None = None
    code: str | None = None
    external_id: str | None = None
    title: str | None = None
    description: str | None = None
    position: int | None = None
    price: float | None = None
    sales_unit: int | None = None
    packaging_unit: int | None = None
    measure: float | None = None
    unit_of_measure: str | None = None
    availability: str | None = None
    group: EmbeddedCatalogItemGroup | None = None
    groups: list[EmbeddedCatalogItemGroup] | None = None
    tags: list[str] | None = None
    attributes: list[EmbeddedAttribute] | None = None
    documents: list[EmbeddedDocument] | None = None
    image: EmbeddedImage | None = None
    commented: bool | None = None
    deleted: bool | None = None


# ---------------------------------------------------------------------------
# Generic list / field-metadata wrappers
# ---------------------------------------------------------------------------

class SmartSalesListResponse(_CamelModel):
    next_page_token: str | None = None
    result_size_estimate: int | None = None
    entries: list[Any] | None = None


class DisplayField(_CamelModel):
    field_name: str | None = None
    display_name: str | None = None
    type: str | None = None
    constraint_type: str | None = None
    fixed: bool | None = None
    size: str | None = None
    audiences: list[str] | None = None


class QueryField(_CamelModel):
    field_name: str | None = None
    display_name: str | None = None
    type: str | None = None
    hidden: bool | None = None
    allow_expression: bool | None = None
    selector: str | None = None
    audiences: list[str] | None = None


class SortField(_CamelModel):
    key_name: str | None = None
    display_name: str | None = None
    hidden: bool | None = None
    audiences: list[str] | None = None
