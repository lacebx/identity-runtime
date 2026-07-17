# 01 — North Star

## The One Sentence

> **Identity portability across models — so developers and users are never locked into one provider.**

---

## What This Means

Right now, AI identity is owned by the model provider:
- Your ChatGPT memory lives inside OpenAI.
- Your Claude preferences live inside Anthropic.
- Switch models and start from zero.

The North Star for identity-runtime is simple: **own the identity layer, not the model.**

When a new model drops — GPT-6, Claude Fable 5, Gemini Ultra — your identities just run better without you changing anything. Models are like CPU upgrades. The identity layer is the OS.

---

## How to Know We've Hit It

The North Star is reached when:

1. A developer can define an identity in a spec file and load it into any major LLM (GPT, Claude, Grok, Gemini) with a single function call.
2. A user can start a chat on ChatGPT, continue on Grok, and the identity feels like the same continuous mind.
3. Switching models does not break the character, the memories, or the relationship history.
4. Identity fidelity can be measured and evaluated programmatically.

---

## What We Are NOT Building

- We are **not** building another ChatGPT or LLM wrapper.
- We are **not** competing with OpenAI, Anthropic, or Google.
- We are **not** trying to store or replace model weights.

We are building the **infrastructure layer** that makes those models more useful, more consistent, and more human.

---

## The Analogy

| Concept | Analogy |
|---|---|
| Models (GPT, Claude, Grok) | Taxi cars |
| Model providers (OpenAI, Anthropic) | Taxi companies |
| identity-runtime | Uber — the coordination layer, not the car |
| Closer analogy | Stripe — the infrastructure layer devs trust to just work |

Long-term moat: **the standard + the tooling to evaluate whether an identity stays faithful over time.**

---

## Why This Matters

In the anime *Pluto*, each robot has its own distinct AI. Officer Gesicht is not "a robot" — he is *Gesicht*, with his own history, values, doubts, and relationships. When we watch him, we don't ask what model he runs on.

That's the future we're building toward: AI identities so well-defined and portable that the underlying model is an implementation detail.
