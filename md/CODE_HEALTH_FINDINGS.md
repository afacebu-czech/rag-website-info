## Code Health Findings

- **Streamlit double configuration** (`Chat.py`): `st.set_page_config` is invoked both at module import and inside `main()`. Streamlit raises `RuntimeError` the second time, so the app stops before rendering. Use a single `st.set_page_config` call (ideally at the top level only) and remove the duplicate.

- **Session snapshot accessor broken** (`src/session_management.py`): `SessionManager.get_session_snapshot()` is defined without a `self` parameter, yet it is called as an instance method. Every call (for example in `process_image`) raises `TypeError: get_session_snapshot() takes 0 positional arguments but 1 was given`. Add the missing `self` argument (or mark it `@staticmethod`) so image handling works.

- **SQLite conversation history retrieval crash** (`src/conversation_management.py`): `get_conversation_history()` checks `if conversation_id not in self.db.get_all_conversations_of_user(self.user_id)`, but the helper returns a list of dicts, so the membership test always fails. Immediately after, the function calls `self.db.get_conversation_messages`, which does not exist on `SQLiteManager`, triggering `AttributeError`. This prevents thread switching and retrieving context. Replace the membership check with a proper search and call the existing `SQLiteManager.get_all_messages_from_conversation()` helper instead.

- **Broken answer caching** (`src/conversation_management.py`): `cache_answer()` accepts `(conversation_id, answer, source_documents)` and simply forwards the string that the caller passes as the first argument into `add_message()`. Callers hand in the user question, so the method creates a bogus conversation whose ID equals the question text, and the cache JSON is never updated. Refactor the method to hash the question (using `_hash_question`), persist the answer/source pair inside `self.question_cache`, and write it via `_save_cache()`. Separate cache storage from conversation history.

- **Message ordering bug** (`src/sqlite_manager.py`): In `add_message()`, the params tuple is `("conversation_id",)` instead of `(conversation_id,)`. The MAX query therefore never filters by the real conversation ID, so each insert computes `new_position = 1`. Messages end up with repeated positions and list out of order. Pass the actual `conversation_id` argument to the query before inserting.

- **Schema foreign key typo** (`src/sqlite_manager.py`): The messages table declares `FOREIGN KEY(conversation_id) REFERENCES conversation (id)`. The referenced table is `conversations`, so the constraint never activates. Fix the table definition (and migrate existing databases) so referential integrity works.

- **Conversation deletion check** (`src/conversation_management.py`): `delete_conversation()` looks for `conv["conversation_id"]`, but entries from SQLite use the key `"id"`. As written, the guard always fails and the code never calls `delete_row`. Switch the key to `"id"` (and refresh `self.conversations`) so deletion succeeds.

- **Optional guard for session clearing** (`src/session_management.py`): `clear()` calls `del st.session_state[key]` without checking membership. When used for optional keys (e.g., `pending_inquiry`), it can raise `KeyError`. Wrap the deletion in an `if key in st.session_state` guard to keep the UI stable during reruns.

These fixes restore core flows: the app boots, session introspection works, conversations load correctly, and caching / persistence behaves as intended.
