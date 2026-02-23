import sys
import asyncio
from configparser import SectionProxy

from azure.identity import DeviceCodeCredential
from msgraph import GraphServiceClient

from msgraph.generated.users.item.user_item_request_builder import (
    UserItemRequestBuilder,
)
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)

from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress


from msgraph.generated.drives.item.items.item.children.children_request_builder import (
    ChildrenRequestBuilder,
)

from msgraph.generated.users.item.contacts.contacts_request_builder import (
    ContactsRequestBuilder,
)

from msgraph.generated.users.item.events.events_request_builder import (
    EventsRequestBuilder,
)


class Graph:
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

    async def get_inbox(self):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['from', 'isRead', 'receivedDateTime', 'subject'],
            # Get at most 25 results
            top=25,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters= query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id('inbox').messages.get(
                request_configuration=request_config)
        return messages


    async def get_drive_items(self):
        query_params = ChildrenRequestBuilder.ChildrenRequestBuilderGetQueryParameters(
            top=20
        )

        request_config = ChildrenRequestBuilder.ChildrenRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        drive = await self.user_client.me.drive.get()

        items = await self.user_client.drives.by_drive_id(drive.id).items.by_drive_item_id("root").children.get(
            request_configuration=request_config
        )

        return items

    async def get_contacts(self):
        query_params = ContactsRequestBuilder.ContactsRequestBuilderGetQueryParameters(
            top=15
        )

        request_config = ContactsRequestBuilder.ContactsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        contacts = await self.user_client.me.contacts.get(
            request_configuration=request_config
        )

        return contacts

    async def get_upcoming_events(self):
        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            top=10,
            orderby=["start/dateTime"]
        )

        request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        events = await self.user_client.me.events.get(
            request_configuration=request_config
        )

        return events