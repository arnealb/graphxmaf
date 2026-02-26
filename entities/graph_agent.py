from data.classes import Email, File, Contact, CalendarEvent, EmailAddress 



class GraphAgent:
    def __init__(self, repo):
        self.repo = repo
        self._email_cache: dict[str, Email] = {}
        self._file_cache: dict[str, File] = {}
        self._contact_cache: dict[str, Contact] = {}
        self._event_cache: dict[str, CalendarEvent] = {}
        self._people_cache: dict[str, EmailAddress] = {}

# whoami ------------------------------------------------------------------

    async def whoami(self) -> str:
        user = await self.repo.get_user()
        return f"Name: {user.display_name}\nEmail: {user.mail or user.user_principal_name}"

# people ------------------------------------------------------------------

    async def find_people(self, name: str) -> str:
        print("in find people")
        people = await self.repo.find_people(name)
        print("in agent, find_people from repo done")

        if not people:
            return "No people found."

        # cache op email
        self._people_cache = {
            p.address.lower(): p
            for p in people
            if p.address
        }

        out = []
        for p in people:
            out.append(
                f"Name: {p.name}\n"
                f"Email: {p.address}\n"
            )

        return "\n".join(out)


# email ------------------------------------------------------------------

    async def search_emails(
        self,
        sender: str | None = None,
        subject: str | None = None,
        received_after=None,
        received_before=None,
    ) -> str:
        emails = await self.repo.search_emails(
            sender=sender,
            subject=subject,
            received_after=received_after,
            received_before=received_before,
        )

        if not emails:
            return "No emails found."

        # cache
        self._email_cache = {e.id: e for e in emails}

        out = []
        for e in emails:
            out.append(
                f"ID: {e.id}\n"
                f"Subject: {e.subject}\n"
                f"From: {e.sender_name}\n"
                f"Received: {e.received}\n"
                f"webLink: {e.web_link}\n"
            )

        return "\n".join(out)

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
                f"From: {e.sender_name}, {e.sender_email}\n"
                f"Received: {e.received}\n"
                f"webLink: {e.web_link}\n"
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
            f"From: {email.sender_name}\n"
            f"Received: {email.received}\n"
            f"webLink: {email.web_link}\n"
            f"{body}"
        )

# files ------------------------------------------------------------------

    async def list_files(self) -> str:
        files = await self.repo.get_drive_items()
        if not files:
            return "No files found."

        self._file_cache = {f.id: f for f in files}

        out = []
        for f in files:
            out.append(
                f"ID: {f.id}\n"
                f"Name: {f.name}\n"
                f"Type: {'Folder' if f.is_folder else 'File'}\n"
                f"WebLink: {f.web_link}\n"
            )
        return "\n".join(out)

# contacts ------------------------------------------------------------------

    async def list_contacts(self) -> str:
        contacts = await self.repo.get_contacts()
        if not contacts:
            return "No contacts found."

        self._contact_cache = {c.id: c for c in contacts}

        out = []
        for c in contacts:
            out.append(
                f"ID: {c.id}\n"
                f"Name: {c.name}\n"
                f"Email: {c.email}\n"
            )

        return "\n".join(out)

# calendar ------------------------------------------------------------------

    async def list_calendar(self) -> str:
        upcoming_events = await self.repo.get_upcoming_events()
        past_events = await self.repo.get_past_events()

        if not upcoming_events and not past_events:
            return "No events found."

        self._event_cache = {e.id: e for e in (upcoming_events + past_events)}

        out = []

        if upcoming_events:
            out.append("Upcoming events:")
            for e in upcoming_events:
                out.append(
                    f"ID: {e.id}\n"
                    f"Subject: {e.subject}\n"
                    f"Start: {e.start}\n"
                    f"End: {e.end}\n"
                )

        if past_events:
            out.append("Past events:")
            for e in past_events:
                out.append(
                    f"ID: {e.id}\n"
                    f"Subject: {e.subject}\n"
                    f"Start: {e.start}\n"
                    f"End: {e.end}\n"
                )

        return "\n".join(out)

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