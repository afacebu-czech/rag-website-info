## Sequential Message Position Plan

- **Goal**: guarantee that every message within the same conversation stores an incrementing `position` value so retrieval preserves chat order.

- **Current State Review**
  - `src/sqlite_manager.py`, `SQLiteManager.add_message()`
    - The function asks SQLite for the current max `position`, but the parameter tuple uses the literal string `"conversation_id"`. The `MAX` query never scopes to the real conversation, so each insert always returns `None` and defaults to `1`.
  - Messages table schema sets `position INT` but has no default/constraint to enforce sequencing.
  - Read paths (e.g., `ConversationManager.get_conversation_history`) expect strictly increasing positions to keep context ordering stable.

- **Pseudocode – Desired Flow**
  ```text
  function add_message(conversation_id, sender, message):
      rows = execute_sql(
          "SELECT COALESCE(MAX(position), 0) FROM messages WHERE conversation_id = ?",
          params=(conversation_id,)
      )
      last_position = rows[0]
      next_position = last_position + 1

      execute_sql(
          "INSERT INTO messages (id, conversation_id, position, sender, message) VALUES (?, ?, ?, ?, ?)",
          params=(generated_id, conversation_id, next_position, sender, message)
      )

      return next_position
  ```

- **Implementation Checklist**
  - Fix the parameter tuple in `SQLiteManager.add_message()` to pass `conversation_id` so `MAX(position)` scopes correctly.
  - (Optional hardening) Wrap the fetch/insert in a transaction to avoid race conditions if multiple writers exist.
  - (Optional) Add a unique index `(conversation_id, position)` to prevent duplicates if future callers bypass the helper.

- **Verification Steps**
  - Insert several messages for the same conversation; expect positions `1, 2, 3, ...`.
  - Check another conversation; its first message should start at `1`.
  - Retrieve messages via `get_all_messages_from_conversation`; confirm ordering matches insertion sequence.
