from dataclasses import dataclass


@dataclass
class Speaker:
    name: str

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Speaker):
            return False
        return self.name == other.name