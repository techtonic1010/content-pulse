# 🧠 Online User Representation System
## Real-Time User Embedding Design for a 2-Stage Recommender

> No code. Pure system design, methodology, and reasoning.  
> Continuation of the ML RecSys Blueprint — Phase 3 Deep Dive.

---

## 📐 Where This Fits in the Bigger Picture

Before diving in, it's important to anchor this phase in the full system:

```
[Offline]  ALS Training → Item Embeddings (V) → FAISS Index
                                                      ↑
[Online]   User Events → Redis Sliding Window → User Vector Builder
                                                      ↓
                                              FAISS ANN Search
                                                      ↓
                                          Candidate Pool (200–500)
                                                      ↓
                                           Ranker → Top-N
```

The user vector builder is the **bridge** between raw behavioral events and the embedding space your FAISS index lives in. It must be fast, accurate, and degrade gracefully under edge cases. Everything downstream — retrieval quality, ranking quality, diversity — is only as good as what this module produces.

---

## SECTION 1 — User Vector Construction

### 1.1 The Core Idea

You already have 128-dimensional item embeddings from your ALS model. Each embedding captures a point in a shared latent taste space. The idea is simple but powerful: **a user's taste at any moment is a weighted combination of the items they've recently engaged with.**

Instead of learning a user embedding offline (which becomes stale), you synthesize it on the fly from their interaction history. The user vector ends up in the same 128-dimensional space as the item embeddings — making dot-product similarity between a user and any item meaningful and directly usable by FAISS.

This approach has a name in the literature: **Interaction-Based User Representation** or sometimes **Session-Aware Embedding Aggregation**. The key insight is that the item embedding space is already rich with semantic structure — you're not building a user vector from scratch, you're navigating the user *into* that existing space.

---

### 1.2 The Signal Hierarchy — What Events Tell You

Not all events are equal. Before you build any formula, you need to understand what each event type is actually *communicating* about user intent:

| Event Type | What It Signals | Trust Level |
|------------|----------------|-------------|
| `COMPLETE` | Strong positive — user watched to the end | Very High |
| `PLAY` | Moderate positive — user chose to start | Moderate |
| `LIKE` / `RATE` | Explicit positive — user expressed preference | High |
| `CLICK` | Weak positive — user was curious, not committed | Low |
| `SKIP` | Mild negative — user saw it and rejected it | Negative |
| `PAUSE + EXIT` | Ambiguous — could be interruption or disinterest | Very Low |

**Design implication:** Each event type gets a scalar weight that reflects its signal trust level. COMPLETE and LIKE should be your anchors — they are the most reliable signals of genuine preference. CLICK is noisy (accidental clicks, thumbnail curiosity) and should be weighted low. SKIP is the only explicit negative signal in this list — handled separately.

---

### 1.3 The Three Weighting Dimensions

Your user vector is computed as a weighted average of item embeddings, where each item's weight is the product of three independent factors:

#### Dimension 1: Event Type Weight

A discrete multiplier based on the event category. For example:
- COMPLETE → 3.0
- PLAY → 2.0
- CLICK → 1.0
- SKIP → −0.5 (negative — more on this below)

These values are not fixed truths — they are hyperparameters you tune empirically. Start with intuitive values and adjust based on whether your retrieval quality improves.

#### Dimension 2: Completion Ratio Weight

This is the most granular signal you have. A raw `PLAY` event tells you someone started a movie. A completion ratio of 0.92 tells you they were absorbed by it. A ratio of 0.08 tells you they tried it and immediately abandoned it.

The completion ratio should act as a **continuous multiplier** on top of the event type weight. A natural formulation is:

```
completion_multiplier = α + (1 − α) × completionRatio
```

Where `α` is a floor value (e.g., 0.3). This means even a 0% completion still contributes something (at weight `α`), and a 100% completion contributes at full weight (1.0). The floor prevents divide-by-zero edge cases and acknowledges that even watching 5 seconds is a signal.

**Important edge case:** For events that have no completion ratio (CLICK, SKIP), treat it as not applicable — don't zero out the weight, just use the event type weight alone.

#### Dimension 3: Recency Decay

A movie watched 2 minutes ago should influence your next recommendation far more than one watched 3 weeks ago. Recency decay encodes this time-sensitivity.

The right decay function is **exponential**, not linear. Why? Because the *rate* at which preferences become stale is proportional to how old they are — the first few hours are the most critical, and beyond a week, things plateau. Linear decay would underweight very recent events and overweight week-old ones.

The conceptual formula:

```
recency_weight = exp(−λ × age_in_hours)
```

Where `λ` controls the half-life. A 7-day half-life means an event from 7 days ago carries exactly half the weight of an event from right now.

**Tuning the half-life** is domain-specific:
- For a news recommender: half-life might be 4–8 hours
- For a movie recommender: 3–7 days is reasonable
- For a music streaming service: somewhere in between

In your system, start with 7 days and observe whether recommendations feel too "stuck in the past" or too volatile. These are the two failure modes of recency decay.

---

### 1.4 The Final Weight per Event

The weight for each item-event pair is the **product** of all three dimensions:

```
weight_i = event_type_weight × completion_multiplier × recency_weight
```

Then the user vector is the **weighted average** of all item embeddings in the sliding window, where weights are normalized to sum to 1 (so the vector's magnitude stays in the same range as individual item embeddings).

Normalization is critical — without it, a user with 50 events would have a much larger-magnitude vector than a user with 3 events, which would skew similarity scores.

---

### 1.5 Handling SKIP — The Negative Signal

SKIP is special. It tells you what the user *doesn't* want. Instead of contributing positively to the user vector (pulling it toward that item's embedding), you want it to **push the vector away** from that embedding.

The elegant way to handle this: include the item embedding with a **negative weight**. After weighted averaging and normalization, the user vector will be slightly farther from skipped items in the embedding space.

The magnitude of this negative weight matters:
- Too large: one skip can distort the user vector significantly
- Too small: the signal is ignored

A negative weight of −0.5 to −1.0 (relative to a PLAY weight of 2.0) is a reasonable starting range. Treat this as a hyperparameter.

**Practical guard:** If a user skips many items in rapid succession (e.g., browsing), the cumulative negative effect can degrade the user vector. Consider capping the total negative contribution across the window.

---

### 1.6 Handling Missing Embeddings (New Content)

Your FAISS index only contains items with ALS-trained embeddings. But what if an event references a new item added after training?

**Strategy: Content-Based Fallback Embedding**

For any item not in your embedding map, generate a proxy embedding from its metadata:
- Compute a weighted average of genre embeddings (if you have genre-level embeddings)
- Or use a TF-IDF/sentence-transformer embedding of the title + description

This proxy embedding may be lower quality than an ALS embedding, but it's far better than ignoring the event entirely. Tag these events with a lower weight (e.g., 0.5×) to reflect the lower confidence in the proxy.

**Alternative: Skip and Compensate**

If the new item is very new and you have very few events for it, simply exclude it from the user vector computation and compensate by giving slightly higher weights to the other events (re-normalize). This is simpler and avoids injecting noisy proxy embeddings.

The right choice depends on how frequently new content is added. High-frequency catalogs (news, short-form video) need the fallback approach. Low-frequency catalogs (movies) can afford to skip and wait for the next retraining cycle.

---

## SECTION 2 — Session vs Long-Term Preference

### 2.1 Why This Distinction Matters

Consider two users:

- **User A**: Has watched 400 drama films over 3 years. In the last 10 minutes, they watched 2 action films.
- **User B**: Is a new user who just watched 2 action films.

If you use only recent events (session-based), both users look identical — two action film interactions. But User A's long-term identity is a drama lover who's having an atypical session. Recommending only action to them would be wrong.

This is the core tension: **sessions capture mood and intent**, long-term history captures **identity and deep preferences**. A great recommendation system serves both.

---

### 2.2 Two-Layer User Representation

Design the user vector as a **blend of two components**:

**Layer 1 — Session Vector (Short-Term)**
- Built from the last ~10–15 events (current session window)
- High recency decay (half-life: hours, not days)
- Captures: current mood, genre exploration, binge session context
- Weighted heavily when the session has strong signals (high completion ratios, multiple completes)

**Layer 2 — Historical Vector (Long-Term)**
- Built from the last ~50–200 events (or computed offline from all-time history)
- Moderate recency decay (half-life: weeks)
- Captures: genre identity, director preferences, era preferences
- Weighted heavily for users with rich history

**Blending formula:**
```
final_user_vector = β × session_vector + (1 − β) × historical_vector
```

Where `β` is the session weight, and it should be **adaptive**:

---

### 2.3 Making β Adaptive

The ideal β is not a fixed constant — it should respond to context:

| Condition | β (Session Weight) | Reasoning |
|-----------|--------------------|-----------|
| Session has ≥3 strong signals (COMPLETE events) | High (0.7) | User is clearly in a mode |
| Session has only CLICKs or weak signals | Low (0.3) | Session is noisy, trust history |
| New user (<10 total events) | Very high (0.9) | No history to blend with |
| User with 500+ events, rich history | Moderate (0.5) | Honor their deep identity |
| Late night (based on timestamp) | Slightly higher | Viewing context shifts at night |

**The practical simplification:** Start with a fixed β (e.g., 0.6) and move to adaptive β once you have enough click/impression data to tune it. Don't over-engineer β before you have empirical data.

---

### 2.4 Where to Store Each Layer

| Layer | Storage | Update Frequency |
|-------|---------|-----------------|
| Session events (raw) | Redis List (TTL: 2h) | Every event |
| Historical events (raw) | Redis List (TTL: 30d) OR PostgreSQL | On session end / batch |
| Session vector (computed) | Redis (TTL: 30min) | On new session event |
| Historical vector (computed) | Redis (TTL: 24h) | Daily batch OR on new event |

**Key insight:** The historical vector doesn't need to be rebuilt on every request. Rebuild it at most once per day (batch job) or when a significant new event arrives (a COMPLETE with high ratio). The session vector, however, must be fresh — rebuild it whenever a new event arrives or the session cache expires.

---

## SECTION 3 — Efficiency and Latency Design

### 3.1 Latency Budget Decomposition

Your target: **under 5ms for user vector construction**. Let's break down where time goes:

| Step | Target Time | Notes |
|------|------------|-------|
| Redis fetch (50 events) | ~0.5ms | Single LRANGE call, network-local |
| Deserialization (JSON → objects) | ~0.3ms | 50 small objects |
| Embedding lookup (50 items) | ~0.5ms | In-memory numpy array |
| Weight computation | ~0.2ms | Pure math, vectorized |
| Weighted average (numpy) | ~0.1ms | Single matrix operation |
| L2 normalization | <0.1ms | Trivial |
| **Total** | **~1.7ms** | Well within 5ms budget |

The math itself is cheap. The bottleneck is always I/O — specifically, the Redis fetch and the embedding lookup. Both can be optimized:

---

### 3.2 Embedding Lookup Strategy

**Option A: In-Memory Numpy Array (Recommended for your scale)**

Load the full item embedding matrix into RAM when the ML service starts. A 128-dim float32 matrix for 60K movies is:
```
60,000 × 128 × 4 bytes = ~30MB
```

30MB in RAM is trivial. Lookup by index is O(1) — just an array index. This eliminates all database calls for embedding lookup.

**Option B: Redis Hash per Item (For larger scales)**

Store each item's embedding as a Redis hash. Network latency per lookup is ~0.3ms, and you need 50 lookups — that's 15ms just for embeddings. Too slow unless you pipeline all 50 fetches into a single Redis batch call.

**Recommendation:** In-memory numpy for your current scale. If your catalog grows to millions of items (RAM pressure), move to Redis pipelining or a lightweight embedding server.

---

### 3.3 Cache Architecture — When to Reuse vs Recompute

The user vector is expensive to build from scratch only in relative terms (1–2ms). But at 10,000 recommendations/second, even 1ms per request is 10 CPU-seconds per second — significant.

**The caching strategy has three states:**

**State 1: Cache HIT — Return Immediately**
The user vector was computed recently (within TTL) and no new events have arrived since. Return the cached vector directly. No computation needed.

**State 2: Cache STALE — Soft Recompute**
The vector exists but is older than TTL. Two approaches:
- *Synchronous*: Recompute before responding (adds latency but guarantees freshness)
- *Asynchronous*: Return the stale vector now, trigger background recomputation for next request

For real-time recommendations, use **asynchronous** staleness handling. A vector that's 6 minutes old (TTL was 5 min) is almost certainly still good enough for a recommendation.

**State 3: Cache MISS — Full Compute**
No vector exists (new user, or TTL expired with no events). Full computation runs synchronously. This is unavoidable, but it's rare for active users.

**TTL Design:**

| User Activity State | Session Vector TTL | Historical Vector TTL |
|---------------------|-------------------|----------------------|
| Active user (events <10min ago) | 5 minutes | 24 hours |
| Semi-active (events today) | 30 minutes | 24 hours |
| Inactive (no events today) | — (let expire) | 7 days |

**Cache Invalidation Trigger:** When a new event arrives via Kafka/Redis, publish an invalidation signal for that user's session vector. The next recommendation request then rebuilds it. Don't invalidate the historical vector on every event — batch that.

---

### 3.4 Incremental Update Instead of Full Rebuild

For users generating many events rapidly (binge-watching), full rebuilds on every event are wasteful. Instead, maintain a **rolling update**:

When a new event arrives:
1. Pop the oldest event from the window (if at capacity)
2. Subtract its weighted contribution from the running sum
3. Add the new event's weighted contribution
4. Re-normalize

This reduces per-event computation from O(window_size) to O(1). The trade-off is that recency decay weights on existing events are now slightly stale (they should have decayed by a few minutes). Accept this approximation — it's negligible for a 5-minute active binge session.

---

## SECTION 4 — Integration with FAISS

### 4.1 Normalization — Why It's Non-Negotiable

Your FAISS index was built with normalized item embeddings. Your user vector must be **L2-normalized before querying**, without exception.

Here's why: you're using Inner Product (IP) similarity as a proxy for cosine similarity. Cosine similarity is dot product only when both vectors have unit length. If the user vector is not normalized, the dot product with item embeddings is no longer cosine similarity — it becomes a combination of angle AND magnitude. The search will be biased toward items with high-magnitude embeddings, not items that are directionally aligned with the user.

**Normalization must happen every time you build or retrieve a user vector**, even from cache. If you cache the normalized vector, confirm it's still unit-norm before querying (floating point operations can accumulate tiny errors over incremental updates).

---

### 4.2 Choosing K — How Many Candidates to Retrieve

The retrieval K (number of candidates passed to the ranker) is a critical parameter:

| K Value | Recall | Ranker Speed | Risk |
|---------|--------|-------------|------|
| 50 | Low | Very fast | Miss good items |
| 200 | Good | Fast | Acceptable |
| 500 | High | Moderate | Acceptable |
| 1000+ | Very high | Slow | Not worth it |

**Recommended: 300 as your default K.** Here's the reasoning:
- You'll filter out seen items (could remove 30–100 items)
- You want diversity (MMR or other filtering might remove another 30–50)
- You need the ranker to have enough variety to work with
- 300 items at 128 dimensions is a tiny matrix for scoring

K should also be adaptive based on user activity:
- New user (few interactions) → retrieve more (K=500) to compensate for noisy user vector
- Power user (rich history) → retrieve fewer (K=200), user vector is precise

---

### 4.3 The Role of `nprobe`

`nprobe` is the IVF index parameter that controls how many of the clustered "cells" (Voronoi regions) are searched during a query.

Think of IVF as a city divided into neighborhoods. With `nprobe=1`, you only search the one neighborhood closest to the query — fast, but you might miss good results in adjacent neighborhoods. With `nprobe=50`, you search 50 neighborhoods — slower, but much better recall.

**The nprobe–latency–recall tradeoff:**

| nprobe | Approx. Recall | Approx. Latency | Use Case |
|--------|---------------|-----------------|----------|
| 1 | ~60% | <1ms | Exploration / high traffic |
| 10 | ~85% | ~2ms | Good default |
| 32 | ~95% | ~4ms | Recommended for production |
| 64 | ~98% | ~7ms | High-quality, lower traffic |
| nlist | 100% | Same as Flat | Defeat the purpose of IVF |

**Recommendation:** Start with `nprobe=16` or `nprobe=32`. This gives you ~90–95% recall at well under 5ms for your catalog size. You can tune this up if you see that the ranker is consistently forced to work with poor candidates.

**Important:** nprobe is not a fire-and-forget setting. After you add items to the index or rebuild it with new embeddings, revalidate recall at your chosen nprobe value by comparing IVF results against Flat index results on a sample of query vectors.

---

### 4.4 Querying the Index

The query is a single normalized 128-dim vector. FAISS returns:
- **Distances array**: inner product similarity scores (higher = more similar, since normalized)
- **Indices array**: integer positions in the FAISS index

You then use your `faiss_idx → movieId` mapping to convert indices back to real item IDs. These are your candidates.

One subtle point: FAISS returns indices in its internal numbering, not your original movieIds. The mapping must be maintained carefully, especially as you rebuild the index with new embeddings. A rebuild should regenerate the mapping atomically alongside the index.

---

## SECTION 5 — Post-Retrieval Handling

### 5.1 Filtering Already-Seen Items

This is simpler than it sounds but has a non-obvious implementation detail.

**The naive approach:** After ANN search, remove any returned movie that appears in the user's interaction history.

**The problem:** You're filtering *after* retrieval. If the user has seen 80 of the top 300 results, you're left with 220 candidates — still fine. But if the user is a power user who's seen 500 movies, and 200 of your top 300 are ones they've seen, you're left with only 100 candidates for the ranker.

**The solution:** Over-fetch. Request K + |seen_items_likely_in_top_K| candidates. For a power user, you might request K=500 knowing that ~150 will be filtered. Estimate this dynamically based on the user's total interaction count.

**What to store for "seen" lookup:**
- Keep a Redis Set of movieIds the user has interacted with (not just the last 50 — all time)
- Key: `user_seen:{userId}`, Type: Redis Set
- Lookup is O(1) per item (SISMEMBER), or batch check all 300 at once (SMISMEMBER in Redis 6.2+)
- Size estimate: 500 movies × 8 bytes = 4KB per user — trivially small

---

### 5.2 Maintaining Diversity

Pure ANN search has a diversity problem: if you've recently watched 5 sci-fi films, your user vector points deep into the sci-fi region of the embedding space. FAISS dutifully returns 300 sci-fi movies. The user gets a mono-genre recommendation page — boring.

**Two complementary strategies:**

**Strategy 1: Modulate the User Vector**

Before querying FAISS, slightly "flatten" the user vector toward a more neutral point. This is done by blending the user vector with the mean of all item embeddings (the "global average taste"):

```
query_vector = (1 − γ) × user_vector + γ × global_mean_vector
```

Where γ is a small diversity coefficient (e.g., 0.1–0.2). This pulls the query vector slightly away from the user's niche, broadening the ANN search radius. The effect is subtle but meaningful.

**Strategy 2: Post-Retrieval Genre Capping**

After retrieving 300 candidates, apply a soft cap per genre cluster:
- No more than X% of candidates from the same primary genre
- Sort within each genre cluster by ANN score and keep the top X%
- Fill the remainder with high-scoring candidates from other clusters

This is simple to implement and very interpretable. It directly addresses the mono-genre failure mode.

**Which to use?** Start with post-retrieval genre capping (Strategy 2) — it's easier to debug and tune. Add vector modulation (Strategy 1) if you want diversity to propagate into the ANN search itself.

---

### 5.3 Avoiding Overfitting to Recent Interactions

Your recency decay already addresses this partially, but there's a subtler problem: **binge sessions create a spike in your user vector**.

If a user watches 8 horror films in 2 hours, all 8 events are very recent (high recency weight), all are PLAY/COMPLETE (high event weight), and they dominate the user vector. The session vector becomes almost entirely "horror". Your historical vector is blended in but it gets diluted.

**Mitigation: Diminishing Returns per Session**

Apply a session-level cap on total weight from a single genre cluster. If horror events already account for 60%+ of the session weight, additional horror events contribute with a reduced multiplier (e.g., 0.5×). This simulates "I get it, they like horror — but I've already accounted for that."

This is sometimes called **redundancy discounting**. It's the same intuition behind why you don't need 30 data points to tell you the user likes horror — the first 3 told you that clearly.

---

## SECTION 6 — Edge Cases

### 6.1 New User — True Cold Start

A user with zero interaction history has no events in Redis and no historical vector. You cannot build a meaningful user vector.

**The cold start funnel:**

**Stage A — Onboarding Signals**
If your product collects onboarding preferences (age, favorite genres, moods), translate these into a pseudo-embedding by averaging the genre-level embedding vectors corresponding to their selections. This is weak but directional — better than nothing.

**Stage B — Demographic / Contextual Fallback**
Without onboarding, serve the globally trending + critically acclaimed items. This is a safe default. It doesn't personalize, but it's unlikely to frustrate. Use the `trending:global` Redis sorted set.

**Stage C — Rapid Warming (first 1–3 events)**
After even one COMPLETE event, you have something to work with. The user vector is low-confidence but directional. Blend it heavily with the popularity signal:

```
query_vector = α × user_vector + (1 − α) × popularity_proxy_vector
```

Where `α` starts at 0.2 (mostly popularity) and increases with each event — reaching 0.8 by event 10. This is the cold-start graduation curve.

**Stage D — Full Personalization (>10 events)**
The user vector is now reliable enough to use without blending. Confidence threshold: at least 3 COMPLETE events or 10 total events.

Track which stage each user is in with a simple Redis field (`user_stage:{userId}`). The recommendation service reads this and routes accordingly.

---

### 6.2 Sparse Interaction History

A user who's been on the platform for 2 years but only watched 8 movies is not the same as a new user. They have genuine preferences, just low volume.

**Don't treat them as cold start.** Instead:
- Use longer history windows (all 8 events, not just last 50)
- Apply lower recency decay (they interact rarely — old events are still valid)
- Use a smaller K in retrieval to ensure precision over recall

**The failure mode to avoid:** Serving popularity-heavy recommendations to a sparse user who's been on the platform a long time and has clearly expressed preferences — just slowly. That's a poor experience.

**Heuristic:** If total event count < 20 but the user has at least 2 COMPLETE events, treat them as a "deliberate" user (they don't interact much but when they do it's meaningful). Weight COMPLETE events even higher (4.0× instead of 3.0×) and use longer recency windows.

---

### 6.3 New Content Without Embeddings

This was touched on in Section 1.6 but deserves more design detail.

**Three scenarios:**

**Scenario A: Content added between retraining cycles**
The item exists in your catalog but has no ALS embedding. Generate a content-based proxy embedding (genre-average or title embedding). Add it to a separate "new_items" FAISS index or directly to the main index with a "new_item" flag.

**Why a separate index?** New items with proxy embeddings are lower quality. If they're in the main index, they'll compete with well-trained embeddings and may pollute retrieval. A separate index lets you control their exposure (e.g., always surface N new items per recommendation batch regardless of ANN score — a form of exploration).

**Scenario B: Viral/trending new content**
A new item is generating massive interaction data. You want to surface it immediately even though it has no embedding. Solution: inject it via the ranker's popularity signal, not via ANN retrieval. The ranker can boost any item with high trending score regardless of whether it was retrieved via ANN.

**Scenario C: Content in a user event that has no embedding**
When building the user vector, you encounter an event for a content item with no embedding. Don't break. Skip the event and compensate by re-normalizing the remaining weights. Log these misses — they're a signal to prioritize content for the next retraining cycle.

---

## SECTION 7 — Putting It All Together: The Request Lifecycle

Here is the complete flow for a single recommendation request:

```
1. REQUEST ARRIVES
   └── userId received by Spring Boot → forwarded to ML service

2. CHECK USER STAGE
   └── Redis lookup: user_stage:{userId}
       ├── COLD START → serve popularity + onboarding blend
       └── ACTIVE → proceed to step 3

3. FETCH VECTORS
   ├── Check Redis: user_emb:{userId} (session vector cache)
   │   ├── HIT + Fresh → skip rebuild → step 5
   │   └── MISS or Stale → step 4
   └── Fetch Redis: user_emb_hist:{userId} (historical vector cache)

4. BUILD USER VECTOR
   ├── Fetch last 50 events: LRANGE user_events:{userId}
   ├── Compute event weights (type × completion × recency)
   ├── Look up item embeddings (in-memory numpy)
   ├── Apply session weighting + diminishing returns
   ├── Weighted average → session vector
   ├── Blend with historical vector (adaptive β)
   ├── L2 normalize
   └── Cache result → user_emb:{userId} TTL=5min

5. RETRIEVE CANDIDATES
   ├── Set K based on user activity level
   ├── Apply subtle diversity flattening (γ blend with global mean)
   ├── Set nprobe=32
   ├── Query FAISS IVF index
   └── Map indices → movieIds, retain scores

6. POST-RETRIEVAL FILTERING
   ├── Remove seen items (SMISMEMBER user_seen:{userId})
   ├── Apply genre cap (diversity enforcement)
   └── Final candidate pool: 200–300 items

7. PASS TO RANKER
   └── Candidate pool + user features → hybrid scorer → Top-N

8. LOG IMPRESSION
   └── Kafka: {userId, recommendedIds, positions, timestamp, algo_version}
```

Total time budget across steps 3–6: under 10ms. The ranker adds another 10–20ms. Total under 30ms end-to-end.

---

## Design Decisions Summary

| Decision | Choice | Why |
|----------|--------|-----|
| User vector approach | Weighted average of item embeddings | Same embedding space, dynamic, no retraining |
| Negative signals | Negative weights for SKIP | Pushes vector away from rejected content |
| Recency | Exponential decay, 7-day half-life | Captures session intent without forgetting history |
| Session vs history | Two-layer blend with adaptive β | Serves both mood and identity |
| Embedding lookup | In-memory numpy | 30MB trivial, O(1) access, no I/O |
| Cache invalidation | Event-triggered for session, batch for history | Balances freshness with compute cost |
| FAISS nprobe | 32 (tunable) | ~95% recall at <5ms |
| Diversity | Post-retrieval genre capping + vector flattening | Simple, debuggable, effective |
| Cold start graduation | 5-stage confidence blend (α scales with events) | Smooth transition, no hard cutoffs |
| New content | Separate index for proxy embeddings | Isolates quality, controls exposure |
| Seen item filtering | Redis Set, over-fetch K to compensate | O(1) lookup, handles power users |

---

*Phase 3 Deep Dive — Online User Representation | RecSys Blueprint Series*
