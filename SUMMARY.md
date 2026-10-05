# Summary

In-memory messenger backend (`messenger.py`), 58 `unittest` tests (`test_messenger.py`), all passing.
Run: `python3 -m unittest -v`

## What was built
| Step | Interfaces | Tests |
|------|------------|-------|
| 1 | `start_conversation`, `get_conversations`, `get_participants` | 20 |
| 2 | `send_message`, `get_messages` | 20 |
| 3 | `mark_read`, `get_read_by` | 18 |

## Design recap
- Same set of people -> same conversation (`frozenset(members) -> convo_id`).
- Messages are an append-only list per conversation, so order is the list order.
- Read receipts use one bookmark per participant (index of last message read), not a per-message set. `mark_read` is a single O(1) write and never moves backwards.
- "Who read message X" = members whose bookmark >= X's index, excluding the sender.
- Errors are logged and raised: `ValueError` (bad input), `PermissionError` (non-member), `LookupError` (unknown conversation/message).

## Edge cases covered
Null / wrong-type inputs on every method, body empty / whitespace / >= 500 chars, non-members cannot view or send, older reads don't rewind the bookmark, repeated and back-to-back calls, messages from another conversation, defensive copies of returned data.

## Decisions to be aware of
- Body limit is strictly `< 500` characters (spec wording); 500 exactly is rejected.
- A message's sender is excluded from its read-by list.

## Next steps if improving
1. Persistence (database) instead of in-memory dicts.
2. Pagination for `get_messages` (and "messages after bookmark" for unread views).
3. Unread counts per conversation from the bookmark.
4. Thread safety: lock per conversation around send/mark_read, which matters once there are real concurrent requests.
5. Per-participant `joined_at` and add/remove participants (currently out of scope).
6. Rollout, per the spec: structured logging with request ids, metrics on error rates, and a feature flag for a small user group so rollback is easy.
