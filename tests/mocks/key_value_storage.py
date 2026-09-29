class InMemoryKeyValueStorage:
    """KeyValueStorage в памяти: как Redis, get отдаёт bytes."""

    def __init__(self):
        self.data = {}
        self.ttls = {}

    def get(self, key):
        value = self.data.get(key)
        return value.encode() if value is not None else None

    def set(self, key, value, ttl=None):
        self.data[key] = value
        self.ttls[key] = ttl

    def delete(self, key):
        self.data.pop(key, None)

    def exists(self, key):
        return key in self.data
