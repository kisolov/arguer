from dataclasses import dataclass, field


from .unprocessed_message import UnprocessedMessage

@dataclass
class Dialogue:
    messages: list[UnprocessedMessage] = field(default_factory=list)

    @property
    def participants(self):
        """Уникальные участники в порядке имён: порядок не зависит от хэшей."""
        return sorted({r.speaker for r in self.messages}, key=lambda s: s.name)

    @property
    def media_duration(self):
        return sum(message.media.duration for message in self.messages if message.media)

    @property
    def total_symbols(self):
        return sum(len(message.text) for message in self.messages if message.text)
    
    def add_message(self, message: UnprocessedMessage):
        self.messages.append(message)


