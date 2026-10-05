"""In-memory messenger backend.

Data model:
    conversations: convo_id -> Conversation
    Conversation.participants: user_id -> last_read_idx (the "bookmark", -1 = nothing read)
    Conversation.messages: append-only list of Message
"""
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_BODY_LENGTH = 500  # body must be strictly shorter than this


@dataclass(frozen=True)
class Message:
    message_id: int
    convo_id: int
    sender_id: str
    body: str
    timestamp: float


@dataclass
class Conversation:
    convo_id: int
    participants: dict = field(default_factory=dict)  # user_id -> last_read_idx
    messages: list = field(default_factory=list)


class Messenger:
    def __init__(self):
        self._conversations = {}  # convo_id -> Conversation
        self._convo_by_members = {}  # frozenset(user_ids) -> convo_id
        self._next_convo_id = 1
        self._next_message_id = 1
        self._message_index = {}  # message_id -> (convo_id, idx in convo.messages)

    # ---- validation helpers ----
    @staticmethod
    def _validate_user_id(user_id):
        if not isinstance(user_id, str) or not user_id.strip():
            logger.error("invalid user_id: %r", user_id)
            raise ValueError("user_id must be a non-empty string")

    @staticmethod
    def _validate_body(body):
        if not isinstance(body, str) or not body.strip():
            logger.error("invalid message body: %r", body)
            raise ValueError("message body must be a non-empty string")
        if len(body) >= MAX_BODY_LENGTH:
            logger.error("message body too long: %d chars", len(body))
            raise ValueError(f"message body must be under {MAX_BODY_LENGTH} characters")

    def _get_convo(self, convo_id):
        convo = self._conversations.get(convo_id)
        if convo is None:
            logger.error("unknown convo_id: %r", convo_id)
            raise LookupError(f"unknown conversation: {convo_id!r}")
        return convo

    def _get_convo_for_member(self, convo_id, user_id):
        self._validate_user_id(user_id)
        convo = self._get_convo(convo_id)
        if user_id not in convo.participants:
            logger.error("user %r is not in convo %r", user_id, convo_id)
            raise PermissionError(f"{user_id!r} is not in conversation {convo_id!r}")
        return convo

    # ---- interfaces ----
    def start_conversation(self, creator_id, other_user_ids):
        """Start a conversation, or return the existing one with the same people."""
        self._validate_user_id(creator_id)
        if not isinstance(other_user_ids, (list, tuple, set, frozenset)):
            logger.error("invalid other_user_ids: %r", other_user_ids)
            raise ValueError("other_user_ids must be a list of user ids")
        for uid in other_user_ids:
            self._validate_user_id(uid)

        members = frozenset(other_user_ids) | {creator_id}
        if len(members) < 2:
            logger.error("conversation needs at least one other user")
            raise ValueError("a conversation needs at least one other user")

        existing = self._convo_by_members.get(members)
        if existing is not None:
            return existing

        convo = Conversation(self._next_convo_id, {uid: -1 for uid in members})
        self._next_convo_id += 1
        self._conversations[convo.convo_id] = convo
        self._convo_by_members[members] = convo.convo_id
        return convo.convo_id

    def get_conversations(self, user_id):
        """Return ids of all conversations the user is in (oldest first)."""
        self._validate_user_id(user_id)
        return [c.convo_id for c in self._conversations.values() if user_id in c.participants]

    def get_participants(self, convo_id, user_id):
        """Return the participant ids of a conversation. Only members may ask."""
        convo = self._get_convo_for_member(convo_id, user_id)
        return sorted(convo.participants)

    def send_message(self, convo_id, sender_id, body):
        """Append a message to the conversation and return its message_id."""
        convo = self._get_convo_for_member(convo_id, sender_id)
        self._validate_body(body)

        idx = len(convo.messages)
        msg = Message(self._next_message_id, convo_id, sender_id, body, time.time())
        self._next_message_id += 1
        convo.messages.append(msg)
        self._message_index[msg.message_id] = (convo_id, idx)
        # the sender has obviously seen their own message
        convo.participants[sender_id] = idx
        return msg.message_id

    def get_messages(self, convo_id, user_id):
        """Return all messages in the conversation, oldest first. Only members may read."""
        convo = self._get_convo_for_member(convo_id, user_id)
        return list(convo.messages)
