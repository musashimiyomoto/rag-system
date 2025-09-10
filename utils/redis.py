import redis.asyncio as redis

from settings import redis_settings

redis_client = redis.StrictRedis(
    host=redis_settings.host,
    port=redis_settings.port,
    db=redis_settings.db,
    decode_responses=True,
)
