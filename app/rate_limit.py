from redis.exceptions import RedisError

from app.cache import redis_client
import time
import uuid
import json

#FIXED WINDOW
def check_fixed_window_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """
    Returns True if the request is allowed.
    Returns False if the rate limit is exceeded.
    """

    try:
        count = redis_client.incr(key)

        if count == 1:
            redis_client.expire(key, window_seconds)

        return count <= limit

    except RedisError: 
        # Fail open:
        # if Redis is down, allow the request.
        return True


#SLIDING WINDOW
def check_sliding_window_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    try:
        now = time.time()
        window_start = now - window_seconds

        # Remove requests older than the current window
        redis_client.zremrangebyscore(
            key,
            0,
            window_start,
        )

        # Count requests still inside the window
        current_count = redis_client.zcard(key)

        if current_count >= limit:
            return False

        # Add the current request
        request_id = f"{now}:{uuid.uuid4()}"

        redis_client.zadd(
            key,
            {request_id: now},
        )

        redis_client.expire(
            key,
            window_seconds,
        )

        return True

    except RedisError:
        # Fail open if Redis is unavailable
        return True
    
#TOKEN BUCKET
def check_token_bucket_rate_limit(
    key: str,
    capacity: int,
    refill_interval_seconds: int,
) -> bool:
    """
    Returns True if the request is allowed.
    Returns False if no token is available.
    """

    try:
        now = time.time()

        stored = redis_client.get(key)

        if stored is None:
            tokens = capacity
            last_refill_time = now
        else:
            data = json.loads(stored)

            tokens = data["tokens"]
            last_refill_time = data["last_refill_time"]

        elapsed = now - last_refill_time

        refill_count = int(
            elapsed // refill_interval_seconds
        )

        if refill_count > 0:
            tokens = min(
                capacity,
                tokens + refill_count,
            )

            last_refill_time += (
                refill_count * refill_interval_seconds
            )

        if tokens <= 0:
            redis_client.set(
                key,
                json.dumps(
                    {
                        "tokens": tokens,
                        "last_refill_time": last_refill_time,
                    }
                ),
                ex=refill_interval_seconds * capacity,
            )

            return False

        tokens -= 1

        redis_client.set(
            key,
            json.dumps(
                {
                    "tokens": tokens,
                    "last_refill_time": last_refill_time,
                }
            ),
            ex=refill_interval_seconds * capacity,
        )

        return True

    except RedisError:
        # Fail open if Redis is unavailable.
        return True
    

