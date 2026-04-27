import html as _html
import re as _re
import sys
from dataclasses import dataclass
from typing import Optional
from configparser import SectionProxy
from datetime import datetime, timezone
from typing import List
import httpx
import asyncio
from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient

from msgraph.generated.users.item.user_item_request_builder import (
    UserItemRequestBuilder,
)
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.users.item.messages.item.message_item_request_builder import (
    MessageItemRequestBuilder,
)

from msgraph.generated.drives.item.items.item.children.children_request_builder import (
    ChildrenRequestBuilder,
)

from msgraph.generated.users.item.contacts.contacts_request_builder import (
    ContactsRequestBuilder,
)

from msgraph.generated.users.item.events.events_request_builder import (
    EventsRequestBuilder,
)

from msgraph.generated.drives.item.items.item.search_with_q.search_with_q_request_builder import (
    SearchWithQRequestBuilder,
)

from msgraph.generated.users.users_request_builder import UsersRequestBuilder

from msgraph.generated.search.query.query_post_request_body import QueryPostRequestBody
from msgraph.generated.models.search_request import SearchRequest
from msgraph.generated.models.search_query import SearchQuery


from graph.interface import IGraphRepository
from graph.models import Email, File, Contact, CalendarEvent, EmailAddress, Attendee

import logging
log = logging.getLogger("graph")
log.setLevel(logging.INFO)

_MAX_EMAIL_CHARS = 8_000
_GRAPH_TIMEOUT = 30.0  # seconds; Graph SDK calls exceeding this are cancelled


def _strip_html(raw: str) -> str:
    """Convert HTML email body to plain text using stdlib only."""
    # Remove <style> and <script> blocks — often kilobytes of CSS/JS
    text = _re.sub(r'<(style|script)[^>]*>.*?</\1>', '', raw, flags=_re.DOTALL | _re.IGNORECASE)
    # Turn block-level elements into newlines so paragraphs survive
    text = _re.sub(r'<(br|p|div|tr|li|h[1-6])\b[^>]*/?>', '\n', text, flags=_re.IGNORECASE)
    # Drop all remaining tags
    text = _re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities (&amp; &nbsp; &#8203; etc.)
    text = _html.unescape(text)
    # Collapse runs of blank lines and horizontal whitespace
    text = _re.sub(r'\n[ \t]+', '\n', text)
    text = _re.sub(r'\n{3,}', '\n\n', text)
    text = _re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


class GraphRepository(IGraphRepository):
    settings: SectionProxy
    device_code_credential: DeviceCodeCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy, credential=None):
        self.settings = config

        client_id = self.settings["clientId"]
        tenant_id = self.settings["tenantId"]
        graph_scopes = self.settings["graphUserScopes"].split(" ")

        if credential is not None:
            self.device_code_credential = credential
        else:
            self.device_code_credential = DeviceCodeCredential(
                client_id=client_id,
                tenant_id=tenant_id,
                prompt_callback=self._device_code_callback,
            )

        self.user_client = GraphServiceClient(
            self.device_code_credential,
            graph_scopes,
        )

    async def _graph_call(self, coro, timeout: float = _GRAPH_TIMEOUT):
        """Await a Graph SDK coroutine with a timeout. Raises TimeoutError on expiry."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Graph API call timed out after {timeout}s")

    def get_user_token(self):
        scopes = self.settings["graphUserScopes"].split(" ")
        token = self.device_code_credential.get_token(*scopes)
        return token.token

    def _device_code_callback(self, verification_uri, user_code, expires_on):
        print("\nAuthenticate here:", file=sys.stderr)
        print(verification_uri, file=sys.stderr)
        print("Code:", user_code, file=sys.stderr)
        print(file=sys.stderr)

    async def get_user(self):
        query_params = (
            UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
                select=["displayName", "mail", "userPrincipalName"]
            )
        )

        request_config = (
            UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )
        )

        user = await self._graph_call(self.user_client.me.get(
            request_configuration=request_config
        ))

        return user


# people ------------------------------------------------------------------

    async def _find_directory_users(self, query: str, top: int = 5) -> list[EmailAddress]:
        # Graph OData startswith is case-sensitive, so try both the raw query
        # and its title-cased variant (e.g. "arne" → also try "Arne").
        q = query.strip().replace("'", "''")
        q_title = query.strip().title().replace("'", "''")
        variants = list({q, q_title})  # deduplicate
        display_parts = " or ".join(f"startswith(displayName,'{v}')" for v in variants)
        mail_parts    = " or ".join(f"startswith(mail,'{v}')" for v in variants)
        upn_parts     = " or ".join(f"startswith(userPrincipalName,'{v}')" for v in variants)
        odata_filter  = f"{display_parts} or {mail_parts} or {upn_parts}"

        log.info("[_find_directory_users] query=%r filter=%s", query, odata_filter)

        params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=["displayName", "mail", "userPrincipalName"],
            top=top,
            filter=odata_filter,
        )
        cfg = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        users = await self._graph_call(self.user_client.users.get(request_configuration=cfg))

        out = []
        if users and users.value:
            for u in users.value:
                email = u.mail or u.user_principal_name
                if email:
                    out.append(EmailAddress(name=u.display_name, address=email))

        log.info("[_find_directory_users] returned %d result(s)", len(out))
        return out

    async def _find_mail_people(self, query: str, top: int = 5) -> list[EmailAddress]:
        params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            search=f'"{query}"',
            select=["from","toRecipients","ccRecipients"],
            top=top,
        )

        cfg = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        res = await self._graph_call(self.user_client.me.messages.get(request_configuration=cfg))

        found = {}

        if res and res.value:
            for m in res.value:
                candidates = []

                if m.from_ and m.from_.email_address:
                    candidates.append(m.from_.email_address)

                for lst in [m.to_recipients, m.cc_recipients]:
                    if lst:
                        for r in lst:
                            if r.email_address:
                                candidates.append(r.email_address)

                for c in candidates:
                    if not c.address:
                        continue
                    key = c.address.lower()
                    if key not in found:
                        found[key] = EmailAddress(
                            name=c.name,
                            address=c.address
                        )

        return list(found.values())

    async def _find_contacts(self, query: str, top: int = 5) -> list[EmailAddress]:
        # OData startswith is case-sensitive; also try title-cased variant.
        safe_query  = query.strip().replace("'", "''")
        safe_title  = query.strip().title().replace("'", "''")
        variants    = list({safe_query, safe_title})
        odata_filter = (
            " or ".join(f"startswith(displayName,'{v}')" for v in variants)
            if query else None
        )

        log.info("[_find_contacts] query=%r filter=%s", query, odata_filter)


        params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["displayName", "emailAddresses"],
            top=top,
            filter=odata_filter,
        )

        cfg = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        res = await self._graph_call(self.user_client.me.contacts.get(request_configuration=cfg))

        out = []
        if res and res.value:
            for c in res.value:
                if c.email_addresses:
                    e = c.email_addresses[0]
                    out.append(EmailAddress(name=e.name, address=e.address))

        return out

    async def find_people(self, query: str, top: int = 5) -> list[EmailAddress]:
        log.info("[find_people] query=%r", query)
        contacts  = await self._find_contacts(query, top)
        directory = await self._find_directory_users(query, top)
        mail      = await self._find_mail_people(query, top)

        log.info("[find_people] contacts=%d  directory=%d  mail=%d",
                 len(contacts), len(directory), len(mail))

        merged: dict[str, EmailAddress] = {}
        for src in (contacts + directory + mail):
            if not src.address:
                continue
            merged[src.address.lower()] = src

        merged_list = list(merged.values())[:top]
        log.info("[find_people] merged=%d result(s): %s",
                 len(merged_list), [(p.name, p.address) for p in merged_list])
        return merged_list

# email ------------------------------------------------------------------

    async def get_inbox(self) -> List[Email]:
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["id", "from", "isRead", "receivedDateTime", "subject", "webLink"],
            top=25,
            orderby=["receivedDateTime DESC"],
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        messages = await self._graph_call(
            self.user_client.me.mail_folders.by_mail_folder_id("inbox").messages.get(
                request_configuration=request_config
            )
        )

        emails: List[Email] = []
        if not messages or not messages.value:
            return emails

        for m in messages.value:
            sender_name = ""
            sender_email = None

            if m.from_ and m.from_.email_address:
                sender_name = (
                    m.from_.email_address.name
                    or m.from_.email_address.address
                    or ""
                )
                sender_email = m.from_.email_address.address


            emails.append(
                Email(
                    id=m.id or "",
                    subject=m.subject or "",
                    sender_name=sender_name,
                    sender_email=sender_email,
                    received=m.received_date_time,
                    web_link=m.web_link
                )
            )

        return emails

    async def get_message_body(self, message_id: str) -> Email | None:
        query_params = MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
            select=["id", "subject", "from", "receivedDateTime", "body", "webLink"],
        )

        log.info(f"[read_email] for email with id: {message_id}")

        request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        log.info("[get_message_body] headers type=%s value=%r", type(request_config.headers), request_config.headers)

        # Ask Graph API to return the body as plain text directly.
        # Falls back to HTML transparently if no plain-text version exists.
        request_config.headers.try_add("Prefer", 'outlook.body-content-type="text"')


        m = await self._graph_call(
            self.user_client.me.messages.by_message_id(message_id).get(
                request_configuration=request_config
            )
        )

        if not m:
            return None

        sender_name = ""
        sender_email = None

        if m.from_ and m.from_.email_address:
            sender_name = (
                m.from_.email_address.name
                or m.from_.email_address.address
                or ""
            )
            sender_email = m.from_.email_address.address

        raw_body = m.body.content if m.body and m.body.content else None

        if raw_body:
            # Strip HTML if the server still returned HTML (no plain-text alternative)
            content_type = (m.body.content_type.value if m.body.content_type else "").lower()
            if content_type == "html" or raw_body.lstrip().startswith("<"):
                raw_body = _strip_html(raw_body)
                log.debug("Email body HTML-stripped, content_type=%s", content_type)
            # Truncate to prevent token explosions
            if len(raw_body) > _MAX_EMAIL_CHARS:
                raw_body = raw_body[:_MAX_EMAIL_CHARS] + "\n\n[... body truncated ...]"
                log.debug("Email body truncated to %d chars", _MAX_EMAIL_CHARS)

        body = raw_body

        log.info("[get_message_body] id=%s content_type=%s raw_body_len=%d body_len=%d body_preview=%r",
            message_id,
            m.body.content_type.value if m.body and m.body.content_type else "None",
            len(m.body.content) if m.body and m.body.content else 0,
            len(body) if body else 0,
            body[:200] if body else None,
        )


        return Email(
            id=m.id or "",
            subject=m.subject or "",
            sender_name=sender_name,
            sender_email=sender_email,
            received=m.received_date_time,
            body=body,
            web_link=m.web_link,
        )


    async def search_emails(
        self,
        sender: str | None = None,
        subject: str | None = None,
        received_after: datetime | None = None,
        received_before: datetime | None = None,
        top: int = 25,
    ) -> list[Email]:
        filters: list[str] = []

        if subject:
            filters.append(f"contains(subject, '{subject}')")

        if sender:
            filters.append(f"contains(from/emailAddress/address,'{sender}')")

        if received_after:
            filters.append(f"receivedDateTime ge {received_after}")

        if received_before:
            filters.append(f"receivedDateTime le {received_before}")

        f = " and ".join(filters) if filters else None

        qp = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select=["id", "subject", "from", "receivedDateTime", "webLink"],
            top=top,
            filter=f,
        )

        cfg = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self._graph_call(self.user_client.me.messages.get(request_configuration=cfg))

        out: list[Email] = []
        for m in (res.value or []) if res else []:
            name = ""
            addr = None
            if m.from_ and m.from_.email_address:
                name = m.from_.email_address.name or m.from_.email_address.address or ""
                addr = m.from_.email_address.address

            out.append(
                Email(
                    id=m.id or "",
                    subject=m.subject or "",
                    sender_name=name,
                    sender_email=addr,
                    received=m.received_date_time,
                    web_link=m.web_link,
                )
            )

        return out


# files ------------------------------------------------------------------

    async def get_drive_items(self) -> List[File]:
        query_params = ChildrenRequestBuilder.ChildrenRequestBuilderGetQueryParameters(
            select=[
                "id",
                "name",
                "webUrl",
                "size",
                "createdDateTime",
                "lastModifiedDateTime",
                "file",
                "folder",
                "parentReference",
            ],
            top=20,
            orderby=["name"]
        )

        request_config = ChildrenRequestBuilder.ChildrenRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        drive = await self._graph_call(self.user_client.me.drive.get())

        items = await self._graph_call(
            self.user_client.drives.by_drive_id(
                drive.id
            ).items.by_drive_item_id("root").children.get(
                request_configuration=request_config
            )
        )

        files: list[File] = []

        if not items or not items.value: 
            return []

        for item in items.value:
            files.append(
                File(
                    id=item.id,
                    name=item.name,
                    is_folder=item.folder is not None,
                    size=item.size,
                    created=item.created_date_time,
                    modified=item.last_modified_date_time,
                    parent_id=item.parent_reference.id if item.parent_reference else None,
                    web_link=item.web_url,
                )
            )

        return files 



    async def get_file_text(self, file_id: str) -> str:
        content_bytes = await self.get_file_content(file_id)
        log.info("[get_file_text] file_id=%s bytes=%d magic=%r", file_id, len(content_bytes), content_bytes[:4])

        # Detect ZIP-based Office formats (docx, xlsx) by magic bytes
        if content_bytes[:4] == b'PK\x03\x04':
            import io, zipfile
            try:
                with zipfile.ZipFile(io.BytesIO(content_bytes)) as zf:
                    names = zf.namelist()
                is_xlsx = any(n.startswith("xl/") for n in names)
            except Exception:
                is_xlsx = False

            if is_xlsx:
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(content_bytes), read_only=True, data_only=True)
                    parts = []
                    for sheet in wb.worksheets:
                        parts.append(f"=== Sheet: {sheet.title} ===")
                        for row in sheet.iter_rows(values_only=True):
                            line = "\t".join("" if v is None else str(v) for v in row)
                            if line.strip():
                                parts.append(line)
                    text = "\n".join(parts)
                    log.info("[get_file_text] xlsx parsed OK, sheets=%d chars=%d", len(wb.worksheets), len(text))
                except Exception as exc:
                    log.warning("[get_file_text] xlsx parse failed: %s", exc)
                    text = f"[Could not parse Excel file: {exc}]"
            else:
                try:
                    from docx import Document
                    doc = Document(io.BytesIO(content_bytes))
                    text = "\n".join(p.text for p in doc.paragraphs if p.text)
                except Exception:
                    try:
                        text = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        text = content_bytes.decode("latin-1")
        else:
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1")

        MAX_CHARS = 12_000
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[... content truncated ...]"
        return text

    async def get_files_text_batch(self, file_ids: list[str]) -> list[str]:
        results = await asyncio.gather(
            *[self.get_file_text(fid) for fid in file_ids],
            return_exceptions=True,
        )
        return [
            r if isinstance(r, str) else f"Error reading file {fid}: {r}"
            for fid, r in zip(file_ids, results)
        ]

    async def get_file_content(self, file_id: str, drive_id: str | None = None) -> bytes:
        if drive_id is None:
            drive = await self._graph_call(self.user_client.me.drive.get())
            drive_id = drive.id

        content = await self._graph_call(
            self.user_client.drives.by_drive_id(drive_id)
            .items.by_drive_item_id(file_id)
            .content.get()
        )
        return content or b""

    async def search_drive_items_sdk(self, query: str, top: int = 25, drive_id: str | None = None) -> list[File]:
        if drive_id is None:
            drive = await self._graph_call(self.user_client.me.drive.get())
            drive_id = drive.id
        log.info("[search_drive_items_sdk] query=%r drive_id=%s top=%d", query, drive_id, top)

        qp = SearchWithQRequestBuilder.SearchWithQRequestBuilderGetQueryParameters(
            select=[
                "id","name","webUrl","size","createdDateTime","lastModifiedDateTime",
                "file","folder","parentReference"
            ],
            top=top,
        )
        cfg = SearchWithQRequestBuilder.SearchWithQRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self._graph_call(
            self.user_client.drives.by_drive_id(drive_id)
            .items.by_drive_item_id("root")
            .search_with_q(query)
            .get(request_configuration=cfg)
        )

        out: list[File] = []
        for item in (res.value or []) if res else []:
            out.append(File(
                id=item.id or "",
                name=item.name or "",
                is_folder=item.folder is not None,
                size=item.size,
                created=item.created_date_time,
                modified=item.last_modified_date_time,
                parent_id=item.parent_reference.id if item.parent_reference else None,
                web_link=item.web_url,
            ))
        log.info("[search_drive_items_sdk] query=%r → %d result(s): %s", query, len(out), [f.name for f in out])
        return out



        


# contacts ------------------------------------------------------------------

    async def get_contacts(self) -> list[Contact]:
        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["id", "displayName", "emailAddresses", "mobilePhone", "businessPhones"],
            top=15
        )

        request_config = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self._graph_call(self.user_client.me.contacts.get(
            request_configuration=request_config
        ))

        contacts: list[Contact] = []

        if not result or not result.value:
            return []

        for c in result.value:
            email = c.email_addresses[0].address if c.email_addresses else None
            phone = c.mobile_phone or (c.business_phones[0] if c.business_phones else None)
            contacts.append(
                Contact(
                    id=c.id,
                    name=c.display_name,
                    email=email,
                    phone=phone,
                )
            )

        return contacts

# calendar ------------------------------------------------------------------

    async def get_upcoming_events(self) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id", "subject", "start", "end", "attendees", "organizer"],
            top=10,
            orderby=["start/dateTime"],
            filter=f"start/dateTime ge '{now}'",
        )

        request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self._graph_call(self.user_client.me.events.get(
            request_configuration=request_config
        ))

        events: list[CalendarEvent] = []
        if not result or not result.value:
            return events

        for e in result.value:
            events.append(self.map_event(e))

        return events

    async def get_past_events(self) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id", "subject", "start", "end", "attendees", "organizer"],
            top=10,
            orderby=["start/dateTime desc"],
            filter=f"start/dateTime lt '{now}'",
        )

        request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self._graph_call(self.user_client.me.events.get(
            request_configuration=request_config
        ))

        events: list[CalendarEvent] = []
        if not result or not result.value:
            return events

        for e in result.value:
            events.append(self.map_event(e))

        return events

    def map_event(self, ev) -> CalendarEvent:
        organizer = None
        if ev.organizer and ev.organizer.email_address:
            organizer = EmailAddress(
                name=ev.organizer.email_address.name,
                address=ev.organizer.email_address.address,
            )

        attendees = []
        if ev.attendees:
            attendees = [
                Attendee(
                    email=EmailAddress(
                        name=a.email_address.name,
                        address=a.email_address.address,
                    )
                )
                for a in ev.attendees
                if a.email_address
            ]

        return CalendarEvent(
            id=ev.id,
            subject=ev.subject,
            start=ev.start.date_time if ev.start else None,
            end=ev.end.date_time if ev.end else None,
            organizer=organizer,
            attendees=attendees,
            web_link=ev.web_link,   # hier
        )


    async def search_events(
        self,
        text: str | None = None,
        location: str | None = None,
        attendee_query: str | None = None,
        start_after: datetime | None = None,
        start_before: datetime | None = None,
        top: int = 25,
    ) -> list[CalendarEvent]:

        filters: list[str] = []

        if text:
            filters.append(f"contains(subject,'{text}')")

        if location:
            filters.append(f"contains(location/displayName,'{location}')")

        if start_after:
            iso = start_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            filters.append(f"start/dateTime ge '{iso}'")

        if start_before:
            iso = start_before.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            filters.append(f"start/dateTime le '{iso}'")

        f = " and ".join(filters) if filters else None

        qp = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["id","subject","start","end","attendees","organizer","location", "webLink"],
            top=top,
            filter=f,
            orderby=["start/dateTime"],
        )

        cfg = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self._graph_call(self.user_client.me.events.get(request_configuration=cfg))

        events: list[CalendarEvent] = []
        if not res or not res.value:
            return events

        mapped = [self.map_event(e) for e in res.value]

        # attendee filter (client-side)
        if attendee_query:
            people = await self.find_people(attendee_query)
            emails = {p.address.lower() for p in people if p.address}

            def match(ev: CalendarEvent) -> bool:
                for a in ev.attendees:
                    if a.email and a.email.address and a.email.address.lower() in emails:
                        return True
                return False

            mapped = [ev for ev in mapped if match(ev)]

        return mapped













    ## this is a backup
    # async def search_drive_items(
    #     self,
    #     query: str,
    #     top: int = 25,
    #     drive_id: str | None = None,
    #     folder_id: str = "root",
    # ) -> list[File]:
    #     if drive_id is None:
    #         drive = await self.user_client.me.drive.get()
    #         drive_id = drive.id

    #     # escape single quotes for OData string literal
    #     q = query.replace("'", "''")

    #     if folder_id == "root":
    #         url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{q}')"
    #     else:
    #         url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}/search(q='{q}')"

    #     params = {
    #         "$select": ",".join([
    #             "id",
    #             "name",
    #             "webUrl",
    #             "size",
    #             "createdDateTime",
    #             "lastModifiedDateTime",
    #             "file",
    #             "folder",
    #             "parentReference",
    #         ]),
    #         "$top": str(top),
    #     }

    #     token = self.get_user_token()
    #     headers = {"Authorization": f"Bearer {token}"}

    #     async with httpx.AsyncClient(timeout=30) as client:
    #         r = await client.get(url, params=params, headers=headers)
    #         r.raise_for_status()
    #         data = r.json()

    #     out: list[File] = []
    #     for item in data.get("value", []):
    #         out.append(
    #             File(
    #                 id=item.get("id") or "",
    #                 name=item.get("name") or "",
    #                 is_folder=item.get("folder") is not None,
    #                 size=item.get("size"),
    #                 created=item.get("createdDateTime"),
    #                 modified=item.get("lastModifiedDateTime"),
    #                 parent_id=(item.get("parentReference") or {}).get("id"),
    #                 web_link=item.get("webUrl"),
    #             )
    #         )

    #     return out



