import redis
from redis.exceptions import RedisError

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)

def clear_user_order_cache(user_id: int):
    try:
        pattern = f"orders:user:{user_id}:*"

        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except RedisError:
        pass