from dataclasses import dataclass
from uuid import UUID


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedPdf:
    pages: list[ParsedPage]

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text.strip()).strip()

