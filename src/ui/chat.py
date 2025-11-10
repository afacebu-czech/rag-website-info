import streamlit as st
from typing import Callable, Optional, Any, Dict
from PIL import Image

# Try multimodal component first (supports Ctrl+V paste), fallback to native Streamlit
try:
    from st_chat_input_multimodal import multimodal_chat_input
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    multimodal_chat_input = None  # type: ignore


def render_chat_tab(initialize_rag_system: Callable[[], Any], session_manager: Any) -> None:
    st.header("Ask Questions")
    st.caption("Get quick, clear answers from your uploaded documents")

    # Check if documents are processed
    if not session_manager.get("documents_processed"):
        rag = initialize_rag_system()
        if rag:
            vs_info = rag.get_vectorstore_info()
            if vs_info["status"] != "initialized" or vs_info.get("document_count", 0) == 0:
                st.warning("⚠️ Please upload and process documents first in the 'Upload Documents' tab.")
                return

    # Thread management UI
    col1, _ = st.columns([3, 1])
    with col1:
        if session_manager.get("current_thread_id"):
            threads = session_manager.get("conversation_manager").get_all_threads()
            thread_topic = "Current conversation"
            for t in threads:
                if t['thread_id'] == session_manager.get("current_thread_id"):
                    thread_topic = t.get('topic', 'Current conversation')
                    if len(thread_topic) > 40:
                        thread_topic = thread_topic[:40] + "..."
                    break
            st.caption(f"💬 Thread: {thread_topic}")
        else:
            st.caption("💬 Thread: New conversation")

    # Display chat messages
    for message in session_manager.get("messages"):
        with st.chat_message(message["role"]):
            if message.get("cached"):
                st.caption("💾 From cache")
            st.markdown(message["content"])
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📄 Reference Documents"):
                    for _, source in enumerate(message["sources"], 1):
                        doc_name = source.get("source", "Document")
                        doc_name = doc_name.replace("_", " ").replace("-", " ").title()
                        st.markdown(f"**{doc_name}**")
                        if source.get("content"):
                            preview = source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                            st.caption(preview)

    # Unified chat input that accepts both text and images
    prompt: Optional[str] = None
    uploaded_image: Optional[Any] = None

    if MULTIMODAL_AVAILABLE:
        user_input = multimodal_chat_input(
            placeholder="💬 Type a message or paste an image (Ctrl+V)...",
            accepted_file_types=["png", "jpg", "jpeg", "gif", "bmp", "webp"],
            enable_voice_input=False,
            max_file_size_mb=10,
            key="multimodal_chat_input",
        )

        if user_input:
            session_manager.start_processing()
            if isinstance(user_input, dict):
                image_data = user_input.get("image") or user_input.get("file") or user_input.get("files")
                if isinstance(image_data, list) and len(image_data) > 0:
                    image_data = image_data[0]
                if image_data:
                    uploaded_image = image_data
                    session_manager.set("pasted_image", True)
                    if user_input.get("text"):
                        prompt = user_input["text"].strip()
                    elif user_input.get("message"):
                        prompt = user_input["message"].strip()
                elif user_input.get("text"):
                    prompt = user_input["text"].strip()
                    session_manager.set("pasted_image", False)
                elif user_input.get("message"):
                    prompt = user_input["message"].strip()
                    session_manager.set("pasted_image", False)
            elif isinstance(user_input, str):
                prompt = user_input.strip()
                session_manager.set("pasted_image", False)
    else:
        try:
            if not session_manager.get("is_processing"):
                user_input = st.chat_input(
                    "💬 Type a message or attach an image...",
                    key="main_chat_input",
                    accept_file=True,
                    file_type=["png", "jpg", "jpeg", "gif", "bmp"],
                )
            else:
                st.chat_input("Processing...", key="disabled_input", disabled=True)
                user_input = None

            if user_input:
                if hasattr(user_input, 'files') and user_input.files:
                    uploaded_image = user_input.files[0]
                    session_manager.set("pasted_image", True)
                    if hasattr(user_input, 'text') and user_input.text:
                        prompt = user_input.text
                elif hasattr(user_input, 'text') and user_input.text:
                    prompt = user_input.text
                    session_manager.set("pasted_image", False)
                elif isinstance(user_input, str):
                    prompt = user_input
                    session_manager.set("pasted_image", False)
        except TypeError:
            col1, col2 = st.columns([5, 1])
            with col1:
                if not session_manager.get("is_processing"):
                    prompt = st.chat_input("💬 Ask a question...", key="main_chat_input")
                else:
                    st.chat_input("Processing...", key="disabled_input", disabled=True)
            with col2:
                uploaded_image = st.file_uploader(
                    "📷",
                    type=["png", "jpg", "jpeg", "gif", "bmp"],
                    help="Paste (Ctrl+V) or upload",
                    key="inquiry_image_fallback",
                    label_visibility="collapsed",
                )

    # Process image if pasted/uploaded
    if uploaded_image is not None:
        if session_manager.get("image_processor"):
            try:
                import io
                import base64

                if isinstance(uploaded_image, dict):
                    image_bytes = None
                    if 'type' in uploaded_image and uploaded_image.get('type') == 'image':
                        image_bytes = uploaded_image.get('content') or uploaded_image.get('data')
                    if not image_bytes:
                        for key in ['data', 'content', 'bytes', 'file', 'image']:
                            if key in uploaded_image:
                                image_bytes = uploaded_image[key]
                                break
                    if image_bytes:
                        if isinstance(image_bytes, bytes):
                            image = Image.open(io.BytesIO(image_bytes))
                        elif hasattr(image_bytes, 'read'):
                            image = Image.open(image_bytes)
                        elif isinstance(image_bytes, Image.Image):
                            image = image_bytes
                        elif isinstance(image_bytes, str):
                            if image_bytes.startswith('data:image/'):
                                try:
                                    header, encoded = image_bytes.split(',', 1)
                                    image_data = base64.b64decode(encoded)
                                    image = Image.open(io.BytesIO(image_data))
                                except Exception as e:
                                    raise ValueError(f"Failed to parse data URI: {str(e)}")
                            else:
                                try:
                                    image_data = base64.b64decode(image_bytes)
                                    image = Image.open(io.BytesIO(image_data))
                                except Exception:
                                    image = Image.open(image_bytes)
                        else:
                            st.error(f"Unsupported image data format in dict: {type(image_bytes)}")
                            return
                    else:
                        st.error("Could not find image data in provided dictionary input")
                        return
                elif hasattr(uploaded_image, 'read'):
                    image = Image.open(uploaded_image)
                elif isinstance(uploaded_image, bytes):
                    image = Image.open(io.BytesIO(uploaded_image))
                elif isinstance(uploaded_image, str):
                    import base64 as _b64
                    if uploaded_image.startswith('data:image/'):
                        try:
                            header, encoded = uploaded_image.split(',', 1)
                            image_data = _b64.b64decode(encoded)
                            image = Image.open(io.BytesIO(image_data))
                        except Exception as e:
                            raise ValueError(f"Failed to parse data URI: {str(e)}")
                    else:
                        image = Image.open(uploaded_image)
                else:
                    image = Image.open(uploaded_image)

                with st.spinner("📖 Reading image and extracting text..."):
                    st.markdown("---")
                    img_col1, img_col2 = st.columns([2, 3])
                    with img_col1:
                        st.image(image, caption="📷 Pasted/Uploaded Image", width=True)
                    with img_col2:
                        result = st.session_state.image_processor.process_image(image)
                        if result["success"]:
                            st.success("✅ Image processed successfully!")
                            client_name = result["client_name"]
                            if client_name:
                                st.info(f"👤 **Client:** {client_name}")
                            else:
                                st.caption("ℹ️ Client name not detected - responses will use generic greeting")
                            if result["inquiry"]:
                                st.markdown("**📝 Inquiry:**")
                                st.write(result["inquiry"])
                            if result.get("has_multiple_questions") and result.get("questions"):
                                st.success(f"✅ Detected {len(result['questions'])} questions!")
                                with st.expander(f"📋 View {len(result['questions'])} Individual Questions"):
                                    for i, q in enumerate(result["questions"], 1):
                                        st.markdown(f"**{i}.** {q}")
                            with st.expander("📄 View Full Extracted Text"):
                                st.text_area("", result["extracted_text"], height=150, label_visibility="collapsed", key="extracted_text_display")
                            prompt_local = result["inquiry"]
                            if not prompt_local or len(prompt_local.strip()) < 5:
                                if result["extracted_text"] and len(result["extracted_text"].strip()) > 10:
                                    prompt_local = result["extracted_text"].strip()
                                    st.warning("⚠️ No clear inquiry detected. Using full extracted text as inquiry.")
                                else:
                                    st.error("❌ Could not extract a valid inquiry from the image. Please ensure the text is clear and readable.")
                                    session_manager.stop_processing()
                                    st.stop()
                                    return
                            pending_inquiry_dict = {
                                "prompt": prompt_local.strip(),
                                "client_name": client_name,
                                "image": image,
                                "extracted_text": result["extracted_text"],
                            }
                            session_manager.set("pending_inquiry", pending_inquiry_dict)
                            st.balloons()
                            st.success("🚀 Ready to generate response suggestions! Processing automatically...")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to process image: {result.get('error', 'Unknown error')}")
                            st.info("💡 Try a clearer image or check that the text is readable")
            except Exception as e:
                st.error(f"❌ Error processing image: {str(e)}")
                st.info("💡 Make sure the image format is supported (PNG, JPG, JPEG, GIF, BMP)")
        else:
            st.error("⚠️ Image processing not available. Please install OCR dependencies: `pip install easyocr pillow`")

    # Process text prompt or pending inquiry
    if prompt or session_manager.get("pending_inquiry"):
        client_name: Optional[str] = None
        image_processed = False
        if session_manager.get("pending_inquiry"):
            inquiry_data: Dict[str, Any] = session_manager.get("pending_inquiry")
            prompt = inquiry_data.get("prompt", "").strip()
            client_name = inquiry_data.get("client_name")
            extracted_text = inquiry_data.get("extracted_text", "").strip()
            image_processed = True
            if not prompt or len(prompt.strip()) < 5:
                if extracted_text and len(extracted_text) > 10:
                    prompt = extracted_text
                    st.warning("ℹ️ Using full extracted text as inquiry (no clear question detected).")
                elif prompt:
                    pass
                else:
                    st.error("❌ Could not extract a valid inquiry from the image.")
                    st.stop()
                    session_manager.stop_processing()
                    return
            session_manager.clear("pending_inquiry")

        if not prompt or len(prompt.strip()) < 3:
            st.warning("⚠️ No valid question found. Please try again.")
            st.stop()
            session_manager.stop_processing()
            return

        if not session_manager.get("current_thread_id"):
            session_manager.set("current_thread_id", session_manager.get("conversation_manager").create_conversation_thread())

        user_message = prompt
        if client_name:
            user_message = f"Client: {client_name}\n\nInquiry: {prompt}"

        session_manager.get("conversation_manager").add_message(
            session_manager.get("current_thread_id"),
            "user",
            user_message,
        )

        display_message = prompt
        if client_name:
            display_message = f"**{client_name}** asks: {prompt}"
        session_manager.get("messages").append({"role": "user", "content": display_message})

        with st.chat_message("user"):
            if client_name:
                st.markdown(f"**Client:** {client_name}")
            st.markdown(prompt)

        rag = initialize_rag_system()
        if rag and rag.qa_chain:
            with st.chat_message("assistant"):
                with st.spinner("Generating response suggestions..."):
                    try:
                        if image_processed:
                            st.caption(f"Processing inquiry: {prompt[:100]}...")
                        regenerate_requested = session_manager.get("regenerate_response", False)
                        if regenerate_requested:
                            session_manager.set("regenerate_response", False)
                            st.info("🔄 Regenerating fresh response (bypassing cache)...")

                        cached_result = None
                        if session_manager.get("use_cache") and not regenerate_requested:
                            cached_result = session_manager.get("conversation_manager").find_similar_question(prompt)
                            if cached_result and cached_result.get("similarity", 0) >= 0.9:
                                st.info("💾 Using cached answer (similar question found)")
                                _, col2 = st.columns([3, 1])
                                with col2:
                                    if st.button("🔄 Regenerate", key="regenerate_cached", use_container_width=True):
                                        st.session_state.regenerate_response = True
                                        st.rerun()
                                result = {
                                    "suggestions": [cached_result["answer"]],
                                    "source_documents": cached_result.get("source_documents", []),
                                    "cached": True,
                                    "original_question": cached_result.get("original_question"),
                                }
                            else:
                                conversation_context = session_manager.get("conversation_manager").get_thread_context(
                                    session_manager.get("current_thread_id")
                                )
                                num_suggestions = 2
                                if image_processed:
                                    st.info("🎯 Generating personalized response suggestions based on the client inquiry...")
                                try:
                                    result = rag.generate_response_suggestions(
                                        question=prompt,
                                        client_name=client_name,
                                        conversation_context=conversation_context,
                                        num_suggestions=num_suggestions,
                                    )
                                    if not result or not result.get("suggestions"):
                                        st.warning("⚠️ No suggestions generated. Trying fallback method...")
                                        fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                        if fallback_result.get("answer"):
                                            result = {
                                                "suggestions": [fallback_result["answer"]],
                                                "source_documents": fallback_result.get("source_documents", []),
                                                "cached": False,
                                            }
                                        else:
                                            raise Exception("Could not generate any response")
                                    session_manager.get("conversation_manager").cache_answer(
                                        prompt,
                                        result["suggestions"][0] if result["suggestions"] else result.get("answer", ""),
                                        result["source_documents"],
                                    )
                                    result["cached"] = False
                                except Exception as e:
                                    st.error(f"❌ Error generating responses: {str(e)}")
                                    st.info("🔄 Trying fallback response generation...")
                                    try:
                                        fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                        if fallback_result.get("answer"):
                                            result = {
                                                "suggestions": [fallback_result["answer"]],
                                                "source_documents": fallback_result.get("source_documents", []),
                                                "cached": False,
                                            }
                                        else:
                                            raise Exception("Fallback also failed")
                                    except Exception as e2:
                                        st.error(f"❌ Fallback also failed: {str(e2)}")
                                        session_manager.stop_processing()
                                        st.stop()
                                        return
                        else:
                            conversation_context = session_manager.get("conversation_manager").get_thread_context(
                                session_manager.get("current_thread_id")
                            )
                            num_suggestions = 2
                            if image_processed:
                                st.info("🎯 Generating personalized response suggestions based on the client inquiry...")
                            try:
                                result = rag.generate_response_suggestions(
                                    question=prompt,
                                    client_name=client_name,
                                    conversation_context=conversation_context,
                                    num_suggestions=num_suggestions,
                                )
                                if not result or not result.get("suggestions"):
                                    st.warning("⚠️ No suggestions generated. Trying fallback method...")
                                    fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                    if fallback_result.get("answer"):
                                        result = {
                                            "suggestions": [fallback_result["answer"]],
                                            "source_documents": fallback_result.get("source_documents", []),
                                            "cached": False,
                                        }
                                    else:
                                        raise Exception("Could not generate any response")
                                result["cached"] = False
                            except Exception as e:
                                st.error(f"❌ Error generating responses: {str(e)}")
                                st.info("🔄 Trying fallback response generation...")
                                try:
                                    fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                    if fallback_result.get("answer"):
                                        result = {
                                            "suggestions": [fallback_result["answer"]],
                                            "source_documents": fallback_result.get("source_documents", []),
                                            "cached": False,
                                        }
                                    else:
                                        raise Exception("Fallback also failed")
                                except Exception as e2:
                                    st.error(f"❌ Fallback also failed: {str(e2)}")
                                    session_manager.stop_processing()
                                    st.stop()
                                    return

                        suggestions = result.get("suggestions", [])
                        if not suggestions or len(suggestions) == 0:
                            st.error("❌ No response suggestions generated. This might be due to:")
                            st.markdown("- No relevant information found in documents")
                            st.markdown("- The inquiry could not be processed")
                            st.markdown("- RAG system error")
                            try:
                                st.info("🔄 Trying fallback response generation...")
                                conversation_context = session_manager.get("conversation_manager").get_thread_context(
                                    session_manager.get("current_thread_id")
                                )
                                fallback_result = rag.query(prompt, conversation_context=conversation_context)
                                if fallback_result.get("answer"):
                                    st.markdown("**Response:**")
                                    st.markdown(fallback_result["answer"])\

                                    session_manager.get("conversation_manager").add_message(
                                        session_manager.get("current_thread_id"),
                                        "assistant",
                                        fallback_result["answer"],
                                        sources=fallback_result.get("source_documents", []),
                                    )
                                    session_manager.get("messages").append({
                                        "role": "assistant",
                                        "content": fallback_result["answer"],
                                        "sources": fallback_result.get("source_documents", []),
                                    })
                                else:
                                    st.error("❌ Could not generate a response. Please check your documents and try again.")
                            except Exception as e:
                                st.error(f"❌ Error generating response: {str(e)}")
                            session_manager.stop_processing()
                            st.stop()
                            return

                        st.markdown("### 💬 Suggested Responses")
                        regen_col1, regen_col2 = st.columns([3, 1])
                        with regen_col1:
                            if client_name:
                                st.caption(f"Choose a response to send to **{client_name}**:")
                            else:
                                st.caption("Choose a response to send to the client:")
                        with regen_col2:
                            if st.button("🔄 Regenerate", key="regenerate_top", use_container_width=True, help="Generate new response variations"):
                                session_manager.set("regenerate_response", True)
                                st.rerun()

                        session_manager.set("current_suggestions", {
                            "suggestions": suggestions,
                            "sources": result["source_documents"],
                            "client_name": client_name,
                            "inquiry": prompt,
                        })

                        for idx, suggestion in enumerate(suggestions, 1):
                            with st.container():
                                col_a, col_b = st.columns([4, 1])
                                with col_a:
                                    st.markdown(f"**Option {idx}:**")
                                    st.markdown(suggestion)
                                with col_b:
                                    if st.button(
                                        "📋 Use This",
                                        key=f"select_{idx}_{len(session_manager.get('messages'))}",
                                        use_container_width=True,
                                    ):
                                        session_manager.set("selected_response_idx", idx)
                                        session_manager.set("selected_response", suggestion)
                                        st.rerun()
                                if idx < len(suggestions):
                                    st.divider()

                        st.markdown("---")
                        _, regen_bottom_col2, _ = st.columns([2, 1, 1])
                        with regen_bottom_col2:
                            if st.button(
                                "🔄 Regenerate All",
                                key="regenerate_bottom",
                                use_container_width=True,
                                help="Generate completely new response variations (bypasses cache)",
                            ):
                                session_manager.set("regenerate_response", True)
                                st.rerun()

                        if session_manager.get("selected_response") and session_manager.get("selected_response_idx"):
                            selected_response = session_manager.get("selected_response")
                            selected_idx = session_manager.get("selected_response_idx")
                            stored_data = session_manager.get("current_suggestions", {})
                            session_manager.get("conversation_manager").add_message(
                                session_manager.get("current_thread_id"),
                                "assistant",
                                selected_response,
                                sources=stored_data.get("sources", result["source_documents"]),
                            )
                            session_manager.get("messages").append({
                                "role": "assistant",
                                "content": f"**Selected Response {selected_idx}:**\n\n{selected_response}",
                                "sources": stored_data.get("sources", result["source_documents"]),
                                "suggestions": stored_data.get("suggestions", suggestions),
                                "selected": selected_idx,
                            })
                            session_manager.clear("selected_response")
                            session_manager.clear("selected_response_idx")
                            if "current_suggestions" in session_manager.get_session_snapshot():
                                session_manager.clear("current_suggestions")
                            st.success(f"✅ Response {selected_idx} selected and saved!")
                            st.rerun()

                        if result["source_documents"]:
                            with st.expander("📄 Reference Documents"):
                                for _, source in enumerate(result["source_documents"], 1):
                                    doc_name = source.get("source", "Document")
                                    doc_name = doc_name.replace("_", " ").replace("-", " ").title()
                                    st.markdown(f"**{doc_name}**")
                                    if source.get("content"):
                                        preview = source["content"][:200] + "..." if len(source["content"]) > 200 else source["content"]
                                        st.caption(preview)
                    except Exception as e:
                        st.error(f"Error generating suggestions: {str(e)}")
                        try:
                            conversation_context = session_manager.get("conversation_manager").get_thread_context(
                                session_manager.get("current_thread_id")
                            )
                            result = rag.query(prompt, conversation_context=conversation_context)
                            st.markdown(result["answer"])
                            session_manager.get("conversation_manager").add_message(
                                session_manager.get("current_thread_id"),
                                "assistant",
                                result["answer"],
                                sources=result["source_documents"],
                            )
                            session_manager.get("messages").append({
                                "role": "assistant",
                                "content": result["answer"],
                                "sources": result["source_documents"],
                            })
                        except Exception as e2:
                            st.error(f"Error: {str(e2)}")
                            session_manager.get("messages").append({
                                "role": "assistant",
                                "content": f"Error: {str(e2)}",
                            })
        else:
            st.error("RAG system not ready. Please check your configuration.")




