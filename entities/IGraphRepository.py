from abc import ABC, abstractmethod

class IGraphRepository(ABC):

    @abstractmethod
    async def get_user(self): ...

    @abstractmethod
    async def get_inbox(self): ...

    @abstractmethod
    async def get_drive_items(self): ...

    @abstractmethod
    async def get_contacts(self): ...

    @abstractmethod
    async def get_upcoming_events(self): ...

    @abstractmethod
    async def get_message_body(self, message_id: str): ...

    # @abstractmethod
    # async def search(self, query: str, entity_types: list[str], size: int = 25): ...