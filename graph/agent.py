from graph.models import Email, File, Contact, CalendarEvent, EmailAddress
from datetime import datetime



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

    async def read_file(self, file_id: str) -> str:
        file = self._file_cache.get(file_id)
        content_bytes = await self.repo.get_file_content(file_id)

        name = file.name if file else file_id

        if name.lower().endswith(".docx"):
            import io
            from docx import Document
            doc = Document(io.BytesIO(content_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text)
        else:
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1")

        MAX_CHARS = 12_000
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[... content truncated ...]"

        return f"File: {name}\n\n{text}"

    async def read_multiple_files(self, file_ids: str) -> str:
        ids = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
        results = []
        for file_id in ids:
            content = await self.read_file(file_id)
            results.append(content)
        return "\n\n---\n\n".join(results)

    async def search_files(
            self,
            query: str,
            drive_id: str | None = None,
            folder_id: str = "root",
        ) -> str:
            files = await self.repo.search_drive_items_sdk(
                query=query,
                top=25,
                drive_id=drive_id,
            )

            if not files:
                return "No files found."

            self._file_cache = {f.id: f for f in files if f.id}

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

    async def search_events(
        self,
        text: str | None = None,
        location: str | None = None,
        attendee: str | None = None,
        start_after: datetime | None = None,
        start_before: datetime | None = None,
    ) -> str:

        events = await self.repo.search_events(
            text=text,
            location=location,
            attendee_query=attendee,
            start_after=start_after,
            start_before=start_before,
        )

        if not events:
            return "No events found."

        out = []
        for e in events:
            out.append(
                f"ID: {e.id}\n"
                f"Subject: {e.subject}\n"
                f"Start: {e.start}\n"
                f"End: {e.end}\n"
                f"webLink: {e.web_link}"
            )

        return "\n".join(out)
