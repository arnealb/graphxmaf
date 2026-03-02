import sys
from dataclasses import dataclass
from typing import Optional
from configparser import SectionProxy
from datetime import datetime, timezone
from typing import List
import httpx

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


from entities.IGraphRepository import IGraphRepository
from data.classes import Email, File, Contact, CalendarEvent, EmailAddress, Attendee

import logging
log = logging.getLogger("graph")
log.setLevel(logging.INFO)


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

        user = await self.user_client.me.get(
            request_configuration=request_config
        )

        return user


# people ------------------------------------------------------------------

    async def _find_directory_users(self, query: str, top: int = 5) -> list[EmailAddress]:
        params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select=["displayName", "mail", "userPrincipalName"],
            top=top,
            filter=f"startswith(displayName,'{query}') or startswith(mail,'{query}') or startswith(userPrincipalName,'{query}')"
        )

        cfg = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        users = await self.user_client.users.get(request_configuration=cfg)

        out = []
        if users and users.value:
            for u in users.value:
                email = u.mail or u.user_principal_name
                if email:
                    out.append(EmailAddress(name=u.display_name, address=email))

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

        res = await self.user_client.me.messages.get(request_configuration=cfg)

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
        params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["displayName","emailAddresses"],
            top=top,
        )


        cfg = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=params
        )

        print("before res")
        res = await self.user_client.me.contacts.get(request_configuration=cfg)
        print("after res")

        out = []
        if res and res.value:
            for c in res.value:
                if c.email_addresses:
                    e = c.email_addresses[0]
                    out.append(EmailAddress(name=e.name, address=e.address))

        return out

    async def find_people(self, query: str, top: int = 5) -> list[EmailAddress]:
        print("fetching contacts / dir / mail")
        contacts = await self._find_contacts(query, top)
        print("find contacts done")
        directory = await self._find_directory_users(query, top)
        mail = await self._find_mail_people(query, top)
        print("fetching contacts / dir / mail done")

        print(f"[find_people] query={query!r}")
        print("  contacts :", [(p.name, p.address) for p in contacts])
        print("  directory:", [(p.name, p.address) for p in directory])
        print("  mail     :", [(p.name, p.address) for p in mail])

        merged = {}

        for src in (contacts + directory + mail):
            if not src.address:
                continue
            merged[src.address.lower()] = src

        merged_list = list(merged.values())[:top]

        print("  merged   :", [(p.name, p.address) for p in merged_list])
        print()

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

        messages = await self.user_client.me.mail_folders.by_mail_folder_id("inbox").messages.get(
            request_configuration=request_config
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

        request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        m = await self.user_client.me.messages.by_message_id(message_id).get(
            request_configuration=request_config
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

        body = m.body.content if m.body and m.body.content else None

        return Email(
            id=m.id or "",
            subject=m.subject or "",
            sender_name=sender_name,
            sender_email=sender_email,
            received=m.received_date_time,
            body=body,
            web_link=m.web_link,   # ← correct
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

        res = await self.user_client.me.messages.get(request_configuration=cfg)

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

        drive = await self.user_client.me.drive.get()

        items = await self.user_client.drives.by_drive_id(
            drive.id
        ).items.by_drive_item_id("root").children.get(
            request_configuration=request_config
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



    async def search_drive_items_sdk(self, query: str, top: int = 25, drive_id: str | None = None) -> list[File]:
        if drive_id is None:
            drive = await self.user_client.me.drive.get()
            drive_id = drive.id

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

        res = await (
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
        return out



        


# contacts ------------------------------------------------------------------

    async def get_contacts(self) -> list[Contact]:
        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            select=["id", "displayName", "emailAddresses"],
            top=15
        )

        request_config = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        result = await self.user_client.me.contacts.get(
            request_configuration=request_config
        )

        contacts: list[Contact] = []

        if not result or not result.value:
            return []
        
        for c in result.value:
            email = c.email_addresses[0].address if c.email_addresses else None
            contacts.append(
                Contact(
                    id=c.id,
                    name=c.display_name,
                    email=email
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

        result = await self.user_client.me.events.get(
            request_configuration=request_config
        )

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

        result = await self.user_client.me.events.get(
            request_configuration=request_config
        )

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
            start= ev.start.date_time if ev.start else None,
            end= ev.end.date_time if ev.end else None,
            organizer=organizer,
            attendees=attendees,
        )


# subject werkt, de rest not sure 
# postman url: https://graph.microsoft.com/v1.0/me/events?$filter=contains(subject,'meeting')
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
            select=["id","subject","start","end","attendees","organizer","location"],
            top=top,
            filter=f,
            orderby=["start/dateTime"],
        )

        cfg = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=qp
        )

        res = await self.user_client.me.events.get(request_configuration=cfg)

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



