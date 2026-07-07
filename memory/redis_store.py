import json
import logging
import redis

logger = logging.getLogger("RedisStore")

class RedisDict(dict):
    """
    A dictionary subclass that intercepts all mutation methods and
    instantly saves the full state back to the RedisStore.
    """
    def __init__(self, store, sid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = store
        self.sid = sid

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.store._save(self.sid, self)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.store._save(self.sid, self)

    def clear(self):
        super().clear()
        self.store._save(self.sid, self)

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.store._save(self.sid, self)

    def pop(self, key, default=None):
        res = super().pop(key, default)
        self.store._save(self.sid, self)
        return res

    def setdefault(self, key, default=None):
        res = super().setdefault(key, default)
        self.store._save(self.sid, self)
        return res


class RedisStore:
    """
    Manages connections to Redis and implements fallback local memory.
    """
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        self.client = None
        self.local_store = {}

        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
                health_check_interval=0,
                decode_responses=True,
            )

            # Force a connection
            self.client.ping()

            logger.info("Connected to Redis.")

        except Exception as e:
            logger.warning(f"Redis unavailable. Using local memory. ({e})")
            self.client = None
            
    def get_context(self, sid: str) -> RedisDict:
        data = self._load_raw(sid)
        return RedisDict(self, sid, data)

    def _load_raw(self, sid: str) -> dict:
        if self.client:
            try:
                data = self.client.get(f"session:{sid}")
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        return self.local_store.setdefault(sid, {})

    def _save(self, sid: str, data: dict):
        if self.client:
            try:
                self.client.set(f"session:{sid}", json.dumps(data))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        self.local_store[sid] = dict(data)

    def delete_context(self, sid: str):
        if self.client:
            try:
                self.client.delete(f"session:{sid}")
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        if sid in self.local_store:
            del self.local_store[sid]

    def clear_context(self, sid: str):
        self._save(sid, {})
