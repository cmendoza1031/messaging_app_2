import time
import unittest
from dataclasses import FrozenInstanceError

from messenger import Messenger


class TestStartConversation(unittest.TestCase):
    def setUp(self):
        self.m = Messenger()

    def test_creates_new_conversation(self):
        cid = self.m.start_conversation("alice", ["bob"])
        self.assertEqual(self.m.get_participants(cid, "alice"), ["alice", "bob"])

    def test_group_conversation(self):
        cid = self.m.start_conversation("alice", ["bob", "sarah"])
        self.assertEqual(self.m.get_participants(cid, "alice"), ["alice", "bob", "sarah"])

    def test_same_people_returns_same_conversation(self):
        first = self.m.start_conversation("alice", ["bob", "sarah"])
        second = self.m.start_conversation("alice", ["bob", "sarah"])
        self.assertEqual(first, second)

    def test_same_people_different_order_or_creator_returns_same(self):
        first = self.m.start_conversation("alice", ["bob", "sarah"])
        self.assertEqual(first, self.m.start_conversation("alice", ["sarah", "bob"]))
        self.assertEqual(first, self.m.start_conversation("bob", ["sarah", "alice"]))

    def test_duplicate_ids_ignored(self):
        first = self.m.start_conversation("alice", ["bob"])
        self.assertEqual(first, self.m.start_conversation("alice", ["bob", "bob"]))

    def test_creator_listed_in_others_is_ignored(self):
        first = self.m.start_conversation("alice", ["bob"])
        self.assertEqual(first, self.m.start_conversation("alice", ["alice", "bob"]))

    def test_different_people_make_different_conversations(self):
        dm = self.m.start_conversation("alice", ["bob"])
        group = self.m.start_conversation("alice", ["bob", "sarah"])
        other = self.m.start_conversation("alice", ["sarah"])
        self.assertEqual(len({dm, group, other}), 3)

    def test_creator_only_rejected(self):
        with self.assertRaises(ValueError):
            self.m.start_conversation("alice", [])
        with self.assertRaises(ValueError):
            self.m.start_conversation("alice", ["alice"])

    def test_bad_inputs_rejected(self):
        bad_creators = [None, "", "   ", 5, ["alice"]]
        for bad in bad_creators:
            with self.subTest(creator=bad), self.assertRaises(ValueError):
                self.m.start_conversation(bad, ["bob"])
        bad_others = [None, "bob", 5, {"a": 1}, [None], [""], ["  "], [5], ["bob", None]]
        for bad in bad_others:
            with self.subTest(others=bad), self.assertRaises(ValueError):
                self.m.start_conversation("alice", bad)

    def test_bad_input_does_not_create_conversation(self):
        with self.assertRaises(ValueError):
            self.m.start_conversation("alice", ["bob", None])
        self.assertEqual(self.m.get_conversations("alice"), [])
        self.assertEqual(self.m.get_conversations("bob"), [])


class TestGetConversations(unittest.TestCase):
    def setUp(self):
        self.m = Messenger()

    def test_user_with_no_conversations(self):
        self.assertEqual(self.m.get_conversations("alice"), [])

    def test_lists_only_users_conversations(self):
        c1 = self.m.start_conversation("alice", ["bob"])
        c2 = self.m.start_conversation("alice", ["sarah"])
        c3 = self.m.start_conversation("bob", ["sarah"])
        self.assertEqual(self.m.get_conversations("alice"), [c1, c2])
        self.assertEqual(self.m.get_conversations("bob"), [c1, c3])
        self.assertEqual(self.m.get_conversations("sarah"), [c2, c3])

    def test_repeated_start_does_not_duplicate(self):
        self.m.start_conversation("alice", ["bob"])
        self.m.start_conversation("alice", ["bob"])
        self.m.start_conversation("bob", ["alice"])
        self.assertEqual(len(self.m.get_conversations("alice")), 1)

    def test_back_to_back_calls_are_stable(self):
        self.m.start_conversation("alice", ["bob"])
        self.assertEqual(self.m.get_conversations("alice"), self.m.get_conversations("alice"))

    def test_bad_user_rejected(self):
        for bad in [None, "", "  ", 5, []]:
            with self.subTest(user=bad), self.assertRaises(ValueError):
                self.m.get_conversations(bad)


class TestGetParticipants(unittest.TestCase):
    def setUp(self):
        self.m = Messenger()
        self.cid = self.m.start_conversation("alice", ["bob", "sarah"])

    def test_every_member_can_view(self):
        for user in ["alice", "bob", "sarah"]:
            self.assertEqual(self.m.get_participants(self.cid, user), ["alice", "bob", "sarah"])

    def test_non_member_cannot_view(self):
        with self.assertRaises(PermissionError):
            self.m.get_participants(self.cid, "mallory")

    def test_unknown_conversation(self):
        for bad in [999, None, "1"]:
            with self.subTest(convo=bad), self.assertRaises(LookupError):
                self.m.get_participants(bad, "alice")

    def test_bad_user_rejected(self):
        for bad in [None, "", 5]:
            with self.subTest(user=bad), self.assertRaises(ValueError):
                self.m.get_participants(self.cid, bad)

    def test_returned_list_is_a_copy(self):
        self.m.get_participants(self.cid, "alice").append("mallory")
        self.assertEqual(self.m.get_participants(self.cid, "alice"), ["alice", "bob", "sarah"])


class TestSendMessage(unittest.TestCase):
    def setUp(self):
        self.m = Messenger()
        self.cid = self.m.start_conversation("alice", ["bob", "sarah"])

    def test_send_and_receive(self):
        mid = self.m.send_message(self.cid, "alice", "hello")
        (msg,) = self.m.get_messages(self.cid, "bob")
        self.assertEqual(msg.message_id, mid)
        self.assertEqual(msg.convo_id, self.cid)
        self.assertEqual(msg.sender_id, "alice")
        self.assertEqual(msg.body, "hello")

    def test_timestamp_is_set(self):
        before = time.time()
        self.m.send_message(self.cid, "alice", "hi")
        after = time.time()
        (msg,) = self.m.get_messages(self.cid, "alice")
        self.assertTrue(before <= msg.timestamp <= after)

    def test_order_preserved_across_senders(self):
        for sender, body in [("alice", "1"), ("bob", "2"), ("sarah", "3"), ("alice", "4")]:
            self.m.send_message(self.cid, sender, body)
        msgs = self.m.get_messages(self.cid, "sarah")
        self.assertEqual([x.body for x in msgs], ["1", "2", "3", "4"])
        self.assertEqual([x.timestamp for x in msgs], sorted(x.timestamp for x in msgs))

    def test_message_ids_unique_across_conversations(self):
        other = self.m.start_conversation("alice", ["bob"])
        ids = [
            self.m.send_message(self.cid, "alice", "a"),
            self.m.send_message(other, "alice", "b"),
            self.m.send_message(self.cid, "bob", "c"),
        ]
        self.assertEqual(len(set(ids)), 3)

    def test_messages_stay_in_their_conversation(self):
        other = self.m.start_conversation("alice", ["bob"])
        self.m.send_message(self.cid, "alice", "group")
        self.m.send_message(other, "alice", "dm")
        self.assertEqual([x.body for x in self.m.get_messages(self.cid, "alice")], ["group"])
        self.assertEqual([x.body for x in self.m.get_messages(other, "alice")], ["dm"])

    def test_identical_back_to_back_messages_both_kept(self):
        a = self.m.send_message(self.cid, "alice", "same")
        b = self.m.send_message(self.cid, "alice", "same")
        self.assertNotEqual(a, b)
        self.assertEqual(len(self.m.get_messages(self.cid, "alice")), 2)

    def test_body_length_limit(self):
        self.m.send_message(self.cid, "alice", "x" * 499)  # ok
        for n in (500, 501, 5000):
            with self.subTest(length=n), self.assertRaises(ValueError):
                self.m.send_message(self.cid, "alice", "x" * n)
        self.assertEqual(len(self.m.get_messages(self.cid, "alice")), 1)

    def test_bad_body_rejected(self):
        for bad in [None, "", "   ", "\n\t", 5, ["hi"], b"hi"]:
            with self.subTest(body=bad), self.assertRaises(ValueError):
                self.m.send_message(self.cid, "alice", bad)
        self.assertEqual(self.m.get_messages(self.cid, "alice"), [])

    def test_non_member_cannot_send(self):
        with self.assertRaises(PermissionError):
            self.m.send_message(self.cid, "mallory", "let me in")
        self.assertEqual(self.m.get_messages(self.cid, "alice"), [])

    def test_unknown_conversation(self):
        for bad in [999, None, "1"]:
            with self.subTest(convo=bad), self.assertRaises(LookupError):
                self.m.send_message(bad, "alice", "hi")

    def test_bad_sender_rejected(self):
        for bad in [None, "", "  ", 5]:
            with self.subTest(sender=bad), self.assertRaises(ValueError):
                self.m.send_message(self.cid, bad, "hi")

    def test_sender_bookmark_advances_others_do_not(self):
        self.m.send_message(self.cid, "alice", "hi")
        self.m.send_message(self.cid, "alice", "again")
        participants = self.m._conversations[self.cid].participants
        self.assertEqual(participants["alice"], 1)
        self.assertEqual(participants["bob"], -1)
        self.assertEqual(participants["sarah"], -1)


class TestGetMessages(unittest.TestCase):
    def setUp(self):
        self.m = Messenger()
        self.cid = self.m.start_conversation("alice", ["bob"])

    def test_empty_conversation(self):
        self.assertEqual(self.m.get_messages(self.cid, "alice"), [])

    def test_both_members_see_same_messages(self):
        self.m.send_message(self.cid, "alice", "hi")
        self.m.send_message(self.cid, "bob", "yo")
        self.assertEqual(self.m.get_messages(self.cid, "alice"), self.m.get_messages(self.cid, "bob"))

    def test_non_member_cannot_view(self):
        self.m.send_message(self.cid, "alice", "secret")
        with self.assertRaises(PermissionError):
            self.m.get_messages(self.cid, "mallory")

    def test_user_in_other_conversation_cannot_view(self):
        self.m.start_conversation("mallory", ["sarah"])
        with self.assertRaises(PermissionError):
            self.m.get_messages(self.cid, "sarah")

    def test_unknown_conversation(self):
        for bad in [999, None, "1"]:
            with self.subTest(convo=bad), self.assertRaises(LookupError):
                self.m.get_messages(bad, "alice")

    def test_bad_user_rejected(self):
        for bad in [None, "", 5]:
            with self.subTest(user=bad), self.assertRaises(ValueError):
                self.m.get_messages(self.cid, bad)

    def test_returned_list_is_a_copy(self):
        self.m.send_message(self.cid, "alice", "hi")
        self.m.get_messages(self.cid, "alice").clear()
        self.assertEqual(len(self.m.get_messages(self.cid, "alice")), 1)

    def test_messages_are_immutable(self):
        self.m.send_message(self.cid, "alice", "hi")
        (msg,) = self.m.get_messages(self.cid, "alice")
        with self.assertRaises(FrozenInstanceError):
            msg.body = "tampered"


if __name__ == "__main__":
    unittest.main()
