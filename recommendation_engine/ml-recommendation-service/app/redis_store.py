from redis import Redis


class RedisEventStore:
    USER_EVENTS_KEY_PREFIX = "user_events:"

    def __init__(self, client: Redis) -> None:
        self._client = client

    def ping(self) -> bool:
        return bool(self._client.ping())

    def get_user_events(self, user_id: str, limit: int = 50) -> list[str]:
        safe_limit = max(1, min(limit, 200))
        key = f"{self.USER_EVENTS_KEY_PREFIX}{user_id}"
        values = self._client.lrange(key, 0, safe_limit - 1)
        return [str(value) for value in values]
