from data.classes import Email

class GraphAgent:
    def __init__(self, repo):
        self.repo = repo
        self._email_cache: dict[str, Email] = {}

    async def whoami(self) -> str:
        user = await self.repo.get_user()
        return f"Name: {user.display_name}\nEmail: {user.mail or user.user_principal_name}"

    async def list_files(self) -> str:
        files = await self.repo.get_drive_items()
        if not files or not files.value:
            return "No files found."

        output = []
        for item in files.value:
            output.append(
                f"Name: {item.name}\n"
                f"Type: {'Folder' if item.folder else 'File'}\n"
                f"WebUrl: {item.web_url}\n"
            )
        return "\n".join(output)

    async def list_email(self) -> str:
        emails = await self.repo.get_inbox()
        if not emails:
            return "No emails found."

        print("---------- saving to cache ----------")
        self._email_cache = {e.id: e for e in emails}

        out = []
        for e in emails:
            out.append(
                f"ID: {e.id}\n"
                f"Subject: {e.subject}\n"
                f"From: {e.sender}\n"
                f"Received: {e.received}\n"
            )
        return "\n".join(out)

    async def read_email(self, message_id: str) -> str:
        print("---------- fist fetching from cache ------------")
        email = self._email_cache.get(message_id)

        if not email:
            email = await self.repo.get_message_body(message_id)
            if not email:
                return "Message not found."

        body = email.body or "(no body)"

        return (
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"Received: {email.received}\n\n"
            f"{body}"
        )

    async def list_contacts(self) -> str:
        contacts = await self.repo.get_contacts()
        if not contacts or not contacts.value:
            return "No contacts found."

        output = []
        for c in contacts.value:
            email = c.email_addresses[0].address if c.email_addresses else "N/A"
            output.append(f"Name: {c.display_name}\nEmail: {email}\n")
        return "\n".join(output)

    async def list_calendar(self) -> str:
        events = await self.repo.get_upcoming_events()
        if not events or not events.value:
            return "No upcoming events found."

        output = []
        for event in events.value:
            output.append(
                f"Subject: {event.subject}\n"
                f"Start: {event.start.date_time if event.start else 'N/A'}\n"
                f"End: {event.end.date_time if event.end else 'N/A'}\n"
            )
        return "\n".join(output)


    async def unified_search(
        self,
        query: str,
        entities: list[str] | None = None,
    ) -> str:
        if entities is None:
            entities = ["message", "event", "driveItem", "person"]

        result = await self.repo.search(query=query, entity_types=entities)

        if not result or not result.value:
            return "No results found."

        output = []
        for response in result.value:
            if not response.hits_containers:
                continue
            for container in response.hits_containers:
                if not container.hits:
                    continue
                for hit in container.hits:
                    resource = hit.resource
                    if resource is None:
                        continue

                    odata_type = (resource.odata_type or "").lower()

                    if "message" in odata_type:
                        output.append(
                            f"[MAIL]\n"
                            f"ID: {resource.id}\n"
                            f"Subject: {getattr(resource, 'subject', 'N/A')}\n"
                        )
                    elif "event" in odata_type:
                        output.append(
                            f"[EVENT]\n"
                            f"Subject: {getattr(resource, 'subject', 'N/A')}\n"
                            f"Start: {getattr(resource.start, 'date_time', 'N/A') if resource.start else 'N/A'}\n"
                        )
                    elif "driveitem" in odata_type:
                        output.append(
                            f"[FILE]\n"
                            f"Name: {getattr(resource, 'name', 'N/A')}\n"
                            f"WebUrl: {getattr(resource, 'web_url', 'N/A')}\n"
                        )
                    elif "person" in odata_type or "contact" in odata_type:
                        output.append(
                            f"[CONTACT]\n"
                            f"Name: {getattr(resource, 'display_name', 'N/A')}\n"
                        )
                    else:
                        output.append(f"[{odata_type}] ID: {resource.id}\n")

        return "\n".join(output) if output else "No results found."