# SDK Improvements Required by the Community Agent

While building the Community Agent, the following SDK improvements were identified and implemented:

## Added Methods

### `identity.infer_intentions(text, author_id, source_channel)`
- **Problem:** The SDK had `intention()` for explicit creation but no way to parse natural language commitments.
- **Solution:** Pattern-matching engine that detects "I'll X tomorrow", "I will Y tonight", "Let me Z", etc.
- **Usage:** `identity.infer_intentions("I'll finish auth tomorrow.", author_id="user-1")`
- **Returns:** List of created intention dicts with metadata tracking

### `identity.infer_meetings(text, author_id, source_channel)`
- **Problem:** No built-in way to detect meeting proposals from conversation.
- **Solution:** Pattern-matching for "Let's meet", "We should sync", "Can we schedule", etc.
- **Usage:** `identity.infer_meetings("Let's meet Friday at 7.", author_id="user-1")`
- **Returns:** List of meeting event dicts

### `identity.reminders(max_results)`
- **Problem:** No way to get a prioritized list of intentions that need attention.
- **Solution:** Queries all intentions, calculates urgency (overdue, due_soon, due_today, etc.), sorts by urgency.
- **Usage:** `identity.reminders(max_results=10)`
- **Returns:** List of reminder dicts sorted by urgency

### `identity.team_status()`
- **Problem:** No aggregated view of what's happening across goals, intentions, and timeline.
- **Solution:** Single method that aggregates active goals, intentions (grouped by author), upcoming meetings, recent events, and relationship changes.
- **Usage:** `identity.team_status()`
- **Returns:** Dict with goals, intentions_by_author, upcoming_meetings, recent_events, relationships

### `identity.digest(period)`
- **Problem:** No way to generate daily/weekly activity summaries.
- **Solution:** Filters timeline events by period, aggregates goals, intentions, reminders, meetings, and relationship highlights.
- **Usage:** `identity.digest("daily")` or `identity.digest("weekly")`
- **Returns:** Formatted digest dict with summary statistics

## Modified Methods

### `identity.intention()` — metadata support
- **Problem:** Couldn't track who authored an intention or where it came from.
- **Solution:** Added `metadata` parameter (passed via `**kwargs`) to store author_id, source_channel, etc.

### `identity._intention_to_dict()` — expose metadata
- **Problem:** Metadata wasn't included in intention serialization.
- **Solution:** Added `metadata` to the returned dict.

## Design Decisions

1. **No bypassing the runtime:** Every new SDK method calls existing runtime services through `self._runtime.*`. The community agent never accesses `self._runtime` directly.
2. **Pattern matching over LLM:** Intention and meeting detection uses regex patterns rather than an LLM call. This makes the SDK lightweight, deterministic, and dependency-free. Future iterations could add an LLM-powered mode.
3. **Author tracking via metadata:** Rather than adding a separate `author_id` field to the Intention model, we use metadata. This keeps the core model clean while allowing the SDK/application layer to attach domain-specific data.
