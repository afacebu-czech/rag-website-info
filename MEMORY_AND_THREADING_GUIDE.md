# Memory, Caching & Threading Features Guide

## 🧠 Features Added

### 1. **Question Caching System**
- **Purpose**: Store and quickly retrieve answers to similar questions
- **How it works**:
  - When you ask a question, the system checks if a similar question was asked before
  - If similarity is ≥90%, it returns the cached answer instantly (much faster!)
  - New questions are automatically cached for future use
- **Benefits**:
  - Faster responses for common questions
  - Consistent answers across the team
  - Reduced processing load

### 2. **Conversation Threading**
- **Purpose**: Organize conversations by topic and maintain context
- **How it works**:
  - Each conversation gets a unique thread ID
  - Follow-up questions remember previous context in the thread
  - Threads are automatically saved and can be switched between
- **Benefits**:
  - Natural follow-up conversations
  - Prevents hallucination by maintaining context
  - Traceable conversation history
  - Switch between different topics easily

### 3. **Anti-Hallucination Protection**
- **How it works**:
  - System always references document context
  - Conversation history provides additional context
  - Explicit instructions to only use document information
  - If information isn't available, system says so clearly
- **Benefits**:
  - More accurate answers
  - Prevents false information
  - Builds trust with users

## 🎯 How to Use

### Starting a New Thread
1. Click "🆕 New Thread" button in the chat interface
2. A new conversation thread is created
3. All questions in this thread will be linked together

### Follow-up Questions
1. Ask your first question: "What are our pricing tiers?"
2. Ask follow-ups in the same thread: "What discounts apply to tier 2?"
3. The system remembers the previous conversation context

### Viewing Thread History
1. Go to sidebar → "Conversation Threads"
2. Select a thread from the dropdown
3. View all messages in that thread
4. Continue the conversation from where you left off

### Caching (Automatic)
- Caching is enabled by default
- Similar questions (≥90% similarity) get instant cached answers
- You'll see a "💾 Using cached answer" indicator
- Can be toggled in sidebar: "Enable Answer Caching"

## 📊 Technical Details

### Similarity Matching
- Uses Jaccard similarity (word overlap)
- Normalizes questions (lowercase, removes extra spaces)
- Direct hash matching for exact questions
- Threshold: 90% similarity for cache hits

### Thread Storage
- Threads stored in `./cache/conversations.json`
- Each thread contains:
  - Thread ID
  - Creation timestamp
  - Topic (first question)
  - All messages with sources
- Persistent across sessions

### Cache Storage
- Questions cached in `./cache/question_cache.json`
- Each cache entry contains:
  - Original question
  - Answer
  - Source documents
  - Timestamp

## 🔒 Privacy & Security
- All data stored locally (no cloud)
- Cache files are in project directory
- Can be cleared manually if needed
- Threads are session-based but persist locally

## 🚀 Performance Benefits
- **Cached answers**: Instant (no LLM processing)
- **Thread context**: Better accuracy with context
- **Reduced hallucinations**: Document-focused + conversation memory

