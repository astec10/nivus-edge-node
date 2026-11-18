"""Redis-backed queue with atomic claims, capacity slots, and expiring leases."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis

from .models import (
    AgentMapping,
    AgentRegistration,
    AgentStatus,
    ClaimedTask,
    TaskPayload,
    TaskResult,
    TaskState,
)


PREFIX = "nivus:parallel-ai:v1"
TASK_PREFIX = f"{PREFIX}:task:"

_REGISTER_LUA = r"""
if redis.call('EXISTS', KEYS[1]) == 1 then
  return 0
end
redis.call('SET', KEYS[1], ARGV[1])
redis.call('SADD', KEYS[2], ARGV[2])
redis.call('HSET', KEYS[3], ARGV[3], ARGV[2])
redis.call('HSET', KEYS[4], ARGV[2], ARGV[3])
return 1
"""

_ENQUEUE_LUA = r"""
local delivery_task = redis.call('GET', KEYS[3])
if delivery_task then
  return {0, delivery_task}
end
if redis.call('EXISTS', KEYS[1]) == 1 then
  redis.call('SET', KEYS[3], ARGV[2], 'EX', ARGV[3], 'NX')
  return {0, ARGV[2]}
end
redis.call('SET', KEYS[1], ARGV[1])
redis.call('ZADD', KEYS[2], ARGV[4], ARGV[2])
redis.call('SET', KEYS[3], ARGV[2], 'EX', ARGV[3])
return {1, ARGV[2]}
"""

_CLAIM_LUA = r"""
if redis.call('EXISTS', KEYS[2]) == 0 or redis.call('EXISTS', KEYS[3]) == 0 then
  return nil
end
local profile = cjson.decode(redis.call('GET', KEYS[2]))
local active = redis.call('SCARD', KEYS[4])
if active >= profile.max_concurrent_tasks then
  return nil
end
local agent_skills = {}
for _, skill in ipairs(profile.skill_ids or {}) do agent_skills[skill] = true end
local agent_specialties = {}
for _, specialty in ipairs(profile.specialties or {}) do agent_specialties[specialty] = true end
local pending_count = redis.call('ZCARD', KEYS[1])
if pending_count == 0 then return nil end
local batch_size = math.min(tonumber(ARGV[8]), pending_count)
local start_at = tonumber(redis.call('GET', KEYS[6]) or '0') % pending_count
local stop_at = math.min(pending_count - 1, start_at + batch_size - 1)
local candidates = redis.call('ZRANGE', KEYS[1], start_at, stop_at)
if #candidates < batch_size and start_at > 0 then
  local remaining = batch_size - #candidates
  local wrapped = redis.call('ZRANGE', KEYS[1], 0, remaining - 1)
  for _, task_id in ipairs(wrapped) do table.insert(candidates, task_id) end
end
redis.call('SET', KEYS[6], (start_at + batch_size) % pending_count)
for _, task_id in ipairs(candidates) do
  local task_key = ARGV[9] .. task_id
  local raw = redis.call('GET', task_key)
  if raw then
    local task = cjson.decode(raw)
    local eligible = task.status == 'pending'
    local required = task.payload.required_skills or {}
    for _, skill in ipairs(required) do
      if not agent_skills[skill] then eligible = false; break end
    end
    local specialty = task.payload.required_specialty
    if specialty and specialty ~= cjson.null and not agent_specialties[specialty] then
      eligible = false
    end
    if eligible then
      task.status = 'leased'
      task.assigned_agent_id = ARGV[1]
      task.attempt = (task.attempt or 0) + 1
      task.updated_at = ARGV[3]
      task.lease_expires_at = ARGV[5]
      redis.call('SET', task_key, cjson.encode(task))
      redis.call('ZREM', KEYS[1], task_id)
      redis.call('SADD', KEYS[4], task_id)
      redis.call('ZADD', KEYS[5], ARGV[4], task_id)
      redis.call('SET', ARGV[10] .. task_id, ARGV[6], 'EX', ARGV[7])
      return cjson.encode(task)
    end
  else
    redis.call('ZREM', KEYS[1], task_id)
  end
end
return nil
"""

_START_LUA = r"""
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[2] then return 0 end
local task = cjson.decode(raw)
if task.assigned_agent_id ~= ARGV[1] or task.status ~= 'leased' then return 0 end
task.status = 'running'
task.updated_at = ARGV[3]
redis.call('SET', KEYS[1], cjson.encode(task))
return 1
"""

_RENEW_LUA = r"""
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[2] then return nil end
local task = cjson.decode(raw)
if task.assigned_agent_id ~= ARGV[1] or (task.status ~= 'leased' and task.status ~= 'running') then return nil end
task.lease_expires_at = ARGV[4]
task.updated_at = ARGV[3]
redis.call('SET', KEYS[1], cjson.encode(task))
redis.call('EXPIRE', KEYS[2], ARGV[5])
redis.call('ZADD', KEYS[3], ARGV[6], ARGV[7])
return cjson.encode(task)
"""

_FINISH_LUA = r"""
local raw = redis.call('GET', KEYS[1])
if not raw or redis.call('GET', KEYS[2]) ~= ARGV[2] then return nil end
local task = cjson.decode(raw)
if task.assigned_agent_id ~= ARGV[1] or (task.status ~= 'leased' and task.status ~= 'running') then return nil end
task.status = 'result_pending_review'
task.result = cjson.decode(ARGV[3])
task.failure_reason = cjson.null
task.lease_expires_at = cjson.null
task.updated_at = ARGV[4]
redis.call('SET', KEYS[1], cjson.encode(task))
redis.call('DEL', KEYS[2])
redis.call('SREM', KEYS[3], ARGV[5])
redis.call('ZREM', KEYS[4], ARGV[5])
return cjson.encode(task)
"""

_REAP_LUA = r"""
local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, tonumber(ARGV[4]))
local changed = 0
for _, task_id in ipairs(ids) do
  local task_key = ARGV[5] .. task_id
  local raw = redis.call('GET', task_key)
  if raw then
    local task = cjson.decode(raw)
    local agent_id = task.assigned_agent_id
    if agent_id and (task.status == 'leased' or task.status == 'running') then
      redis.call('SREM', ARGV[6] .. agent_id, task_id)
      if (task.attempt or 0) < (task.max_attempts or 3) then
        task.status = 'pending'
        task.assigned_agent_id = cjson.null
        task.lease_expires_at = cjson.null
        task.updated_at = ARGV[2]
        task.failure_reason = 'Lease expirou; tarefa retornou à fila.'
        redis.call('ZADD', KEYS[2], ARGV[3], task_id)
      else
        task.status = 'failed'
        task.assigned_agent_id = cjson.null
        task.lease_expires_at = cjson.null
        task.updated_at = ARGV[2]
        task.failure_reason = 'Lease expirou após o limite de tentativas.'
      end
      redis.call('SET', task_key, cjson.encode(task))
      changed = changed + 1
    end
  end
  redis.call('DEL', ARGV[7] .. task_id)
  redis.call('ZREM', KEYS[1], task_id)
end
return changed
"""

_REVOKE_LUA = r"""
if redis.call('EXISTS', KEYS[1]) == 0 then return 0 end
local agent_id = ARGV[1]
local token_hash = redis.call('HGET', KEYS[6], agent_id)
if token_hash then redis.call('HDEL', KEYS[5], token_hash) end
redis.call('HDEL', KEYS[6], agent_id)
local task_ids = redis.call('SMEMBERS', KEYS[3])
for _, task_id in ipairs(task_ids) do
  local task_key = ARGV[4] .. task_id
  local raw = redis.call('GET', task_key)
  if raw then
    local task = cjson.decode(raw)
    if task.assigned_agent_id == agent_id and (task.status == 'leased' or task.status == 'running') then
      task.assigned_agent_id = cjson.null
      task.lease_expires_at = cjson.null
      task.updated_at = ARGV[3]
      if (task.attempt or 0) < (task.max_attempts or 3) then
        task.status = 'pending'
        task.failure_reason = 'Agente revogado; tarefa retornou à fila.'
        redis.call('ZADD', KEYS[4], ARGV[2], task_id)
      else
        task.status = 'failed'
        task.failure_reason = 'Agente revogado após o limite de tentativas.'
      end
      redis.call('SET', task_key, cjson.encode(task))
      redis.call('DEL', ARGV[5] .. task_id)
      redis.call('ZREM', KEYS[7], task_id)
    end
  end
end
redis.call('DEL', KEYS[1], KEYS[2], KEYS[3])
redis.call('SREM', KEYS[8], agent_id)
return 1
"""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _key(suffix: str) -> str:
    return f"{PREFIX}:{suffix}"


class RedisDispatcher:
    """Redis state store. All assignment and slot changes run atomically in Lua."""

    def __init__(self, redis_client: Redis, *, lease_seconds: int = 120, delivery_ttl: int = 2_592_000):
        if lease_seconds < 30 or lease_seconds > 3_600:
            raise ValueError("lease_seconds deve estar entre 30 e 3600")
        self.redis = redis_client
        self.lease_seconds = lease_seconds
        self.delivery_ttl = delivery_ttl

    async def register_agent(self, registration: AgentRegistration) -> tuple[AgentMapping, str]:
        agent_id = f"agent-{secrets.token_hex(8)}"
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        agent = AgentMapping(agent_id=agent_id, **registration.model_dump())
        created = await self.redis.eval(
            _REGISTER_LUA,
            4,
            _key(f"agent:{agent_id}"),
            _key("agents"),
            _key("agent-tokens"),
            _key("agent-token-by-id"),
            agent.model_dump_json(),
            agent_id,
            token_hash,
            agent_id,
        )
        if created != 1:
            raise RuntimeError("Não foi possível registrar o agente")
        return agent, token

    async def authenticate_agent(self, token: str) -> str | None:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        value = await self.redis.hget(_key("agent-tokens"), digest)
        return str(value) if value else None

    async def heartbeat(self, agent_id: str, *, ttl_seconds: int) -> None:
        if not await self.redis.exists(_key(f"agent:{agent_id}")):
            raise KeyError(agent_id)
        await self.redis.set(_key(f"agent-online:{agent_id}"), "1", ex=ttl_seconds)

    async def list_agents(self) -> list[AgentStatus]:
        agent_ids = sorted(await self.redis.smembers(_key("agents")))
        if not agent_ids:
            return []
        pipe = self.redis.pipeline(transaction=False)
        for agent_id in agent_ids:
            pipe.get(_key(f"agent:{agent_id}"))
            pipe.exists(_key(f"agent-online:{agent_id}"))
            pipe.scard(_key(f"agent-leases:{agent_id}"))
        values = await pipe.execute()
        result: list[AgentStatus] = []
        for index, agent_id in enumerate(agent_ids):
            raw, online, active = values[index * 3 : index * 3 + 3]
            if raw:
                profile = AgentMapping.model_validate_json(raw)
                result.append(
                    AgentStatus(
                        **profile.model_dump(),
                        is_online=bool(online),
                        active_tasks=int(active),
                    )
                )
        return result

    async def revoke_agent(self, agent_id: str) -> bool:
        now = _utcnow()
        result = await self.redis.eval(
            _REVOKE_LUA,
            8,
            _key(f"agent:{agent_id}"),
            _key(f"agent-online:{agent_id}"),
            _key(f"agent-leases:{agent_id}"),
            _key("pending"),
            _key("agent-tokens"),
            _key("agent-token-by-id"),
            _key("leases"),
            _key("agents"),
            agent_id,
            now.timestamp(),
            now.isoformat(),
            TASK_PREFIX,
            _key("lease-token:"),
        )
        return result == 1

    async def enqueue(self, payload: TaskPayload, delivery_id: str) -> tuple[TaskState, bool]:
        task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"nivus:{payload.repository.casefold()}#{payload.issue_number}"))
        now = _utcnow()
        state = TaskState(task_id=task_id, payload=payload, created_at=now, updated_at=now)
        result = await self.redis.eval(
            _ENQUEUE_LUA,
            3,
            _key(f"task:{task_id}"),
            _key("pending"),
            _key(f"delivery:{delivery_id}"),
            state.model_dump_json(),
            task_id,
            self.delivery_ttl,
            now.timestamp(),
        )
        created = int(result[0]) == 1
        existing_id = str(result[1])
        existing = await self.get_task(existing_id)
        if existing is None:
            raise RuntimeError("A tarefa não foi persistida no Redis")
        return existing, created

    async def claim_next(self, agent_id: str, *, max_scan: int = 100) -> ClaimedTask | None:
        now = _utcnow()
        expiry = now + timedelta(seconds=self.lease_seconds)
        lease_token = secrets.token_urlsafe(32)
        raw = await self.redis.eval(
            _CLAIM_LUA,
            6,
            _key("pending"),
            _key(f"agent:{agent_id}"),
            _key(f"agent-online:{agent_id}"),
            _key(f"agent-leases:{agent_id}"),
            _key("leases"),
            _key(f"claim-cursor:{agent_id}"),
            agent_id,
            now.timestamp(),
            now.isoformat(),
            expiry.timestamp(),
            expiry.isoformat(),
            lease_token,
            self.lease_seconds,
            max_scan,
            TASK_PREFIX,
            _key("lease-token:"),
        )
        if not raw:
            return None
        task = TaskState.model_validate_json(raw)
        return ClaimedTask(task=task, lease_token=lease_token)

    async def start_task(self, agent_id: str, task_id: str, lease_token: str) -> bool:
        now = _utcnow()
        changed = await self.redis.eval(
            _START_LUA,
            2,
            _key(f"task:{task_id}"),
            _key(f"lease-token:{task_id}"),
            agent_id,
            lease_token,
            now.isoformat(),
        )
        return changed == 1

    async def renew_lease(self, agent_id: str, task_id: str, lease_token: str) -> TaskState | None:
        now = _utcnow()
        expiry = now + timedelta(seconds=self.lease_seconds)
        raw = await self.redis.eval(
            _RENEW_LUA,
            3,
            _key(f"task:{task_id}"),
            _key(f"lease-token:{task_id}"),
            _key("leases"),
            agent_id,
            lease_token,
            now.isoformat(),
            expiry.isoformat(),
            self.lease_seconds,
            expiry.timestamp(),
            task_id,
        )
        return TaskState.model_validate_json(raw) if raw else None

    async def submit_result(
        self,
        agent_id: str,
        task_id: str,
        lease_token: str,
        result: TaskResult,
    ) -> TaskState | None:
        now = _utcnow()
        raw = await self.redis.eval(
            _FINISH_LUA,
            4,
            _key(f"task:{task_id}"),
            _key(f"lease-token:{task_id}"),
            _key(f"agent-leases:{agent_id}"),
            _key("leases"),
            agent_id,
            lease_token,
            result.model_dump_json(),
            now.isoformat(),
            task_id,
        )
        return TaskState.model_validate_json(raw) if raw else None

    async def get_task(self, task_id: str) -> TaskState | None:
        raw = await self.redis.get(_key(f"task:{task_id}"))
        return TaskState.model_validate_json(raw) if raw else None

    async def reap_expired_leases(self, *, batch_size: int = 100) -> int:
        now = _utcnow()
        changed = await self.redis.eval(
            _REAP_LUA,
            2,
            _key("leases"),
            _key("pending"),
            now.timestamp(),
            now.isoformat(),
            now.timestamp(),
            batch_size,
            TASK_PREFIX,
            _key("agent-leases:"),
            _key("lease-token:"),
        )
        return int(changed)
