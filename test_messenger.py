import unittest

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


if __name__ == "__main__":
    unittest.main()
