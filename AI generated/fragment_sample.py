"""Example demonstrating how to refresh the Streamlit sidebar thread list via `st.fragment`.

When the chat input submits, `session_manager.refresh_list_conversations()` triggers
and the fragment reruns, rebuilding the thread options with updated titles.
"""

import streamlit as st


def render_sidebar_fragment(session_manager, update_conversations_callback):
    """Wrap the sidebar rendering logic inside an `st.fragment` block.

    This lets the fragment rerun independently whenever the chat input submits
    and the callback refreshes the stored conversation metadata.
    """

    @st.fragment
    def sidebar_threads():
        st.subheader("Conversation Threads")

        update_conversations_callback()
        threads = session_manager.get("conversation_manager").get_all_conversations()

        if not threads:
            st.caption("No previous threads")
            return

        options = {
            f"{(t.get('topic') or 'Untitled Conversation')[:50]} ({t.get('message_count', 0)} msgs)": t["thread_id"]
            for t in threads
        }

        current_thread_id = session_manager.get("current_thread_id")
        current_keys = list(options.keys())
        default_index = next((i for i, key in enumerate(current_keys) if options[key] == current_thread_id), 0)

        selected_label = st.selectbox(
            "Switch to thread:",
            options=current_keys,
            index=default_index,
        )

        selected_id = options[selected_label]
        if selected_id != current_thread_id:
            session_manager.set("current_thread_id", selected_id)
            history = session_manager.get("conversation_manager").get_conversation_history(selected_id)
            session_manager.set(
                "messages",
                [{"role": msg["sender"], "content": msg["message"]} for msg in history],
            )

    sidebar_threads()
