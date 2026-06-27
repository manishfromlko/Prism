from src.retrieval import user_profile_store as store_module
from src.retrieval.user_profile_store import UserProfileStore


def test_get_all_profiles_returns_profiles_sorted_by_user_id(monkeypatch):
    store = UserProfileStore.__new__(UserProfileStore)
    store.collection = "user_profiles"

    monkeypatch.setattr(store, "_ensure_client", lambda: object())
    monkeypatch.setattr(
        store_module,
        "scroll_payloads",
        lambda *args, **kwargs: [
            {"id": "3", "user_id": "priya2.patel"},
            {"id": "1", "user_id": "aarav.mehra"},
            {"id": "2", "user_id": "Priya.Patel"},
        ],
    )

    profiles = store.get_all_profiles()

    assert [profile["user_id"] for profile in profiles] == [
        "aarav.mehra",
        "Priya.Patel",
        "priya2.patel",
    ]
