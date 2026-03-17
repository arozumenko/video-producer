---
name: demo-script
description: Co-author demo video scripts by exploring the live product via browser. Use when user asks to "write a demo script", "plan a product video", "script a walkthrough", "create a demo storyboard", or "plan a recording". Generates structured JSON scripts with actions, narration, timing, and highlight styles ready for /record-demo.
compatibility: Requires Playwright MCP server for browser exploration.
metadata:
  author: arozumenko
  version: 1.0.0
---

# Demo Script Skill

Create structured demo video scripts by exploring the live product and co-authoring with the user.

## Why This Exists

Good demo videos need good scripts. Bad demos ramble, skip important bits, or move too fast. This skill produces a precise, reviewable script that `/record-demo` can execute automatically.

## Workflow

### Stage 1: Brief

Gather context from the user:

**Required:**
- What product/feature to demo
- Target URL (staging/production)
- Who is the audience? (prospects, existing users, developers, internal team)

**Optional (ask if not provided):**
- Specific flow to show (e.g. "create a test case with steps and expected results")
- Tone (professional, casual, technical, marketing)
- Duration target (30s, 1min, 3min, 5min)
- Key points to emphasize
- Things to avoid/skip

Default assumptions if not specified:
- Audience: prospective users evaluating the product
- Tone: professional but approachable
- Duration: 1-2 minutes
- Resolution: 1920x1080

### Stage 2: Product Exploration

**Use the Playwright browser tools to explore the actual product UI.**

This is critical — don't guess what the UI looks like. Actually navigate it:

1. Open the target URL in the browser
2. Take screenshots of each relevant page/screen
3. Note the actual button labels, menu items, form fields
4. Understand the navigation flow
5. Identify UI elements by their real selectors

```
Example exploration flow:
  → Navigate to app URL
  → Screenshot the dashboard
  → Click through the target feature
  → Screenshot each state change
  → Note exact selectors for all interactive elements
  → Check for loading states, animations, modals
```

**Why explore first?**
- Real selector names (not guessed ones that will fail during recording)
- Accurate narration that matches what's on screen
- Discover the natural flow (maybe there's a step the user forgot to mention)
- Catch potential issues (auth walls, slow loads, empty states)

**Authentication:**
- If the app requires login, ask the user for credentials or a pre-authenticated session
- Alternatively, use a staging environment with test data
- Note: save cookies/session for the recording phase

### Stage 3: Script Drafting

Generate a structured script in JSON format with `metadata` and `scenes` arrays.

For the full JSON schema, action reference, and highlight styles, consult `references/script-format.md`.

### Stage 4: Review & Iterate

Present the script to the user in a readable format (NOT raw JSON). Format it as:

```
🎬 Demo Script: "Creating Your First Test Case"
Duration: ~90 seconds | Audience: Prospective users

━━━ Scene 1: Opening — Dashboard Overview ━━━
  → Navigate to /dashboard
  🎙️ "Welcome to OneTest. Let's create your first test case."
  ⏸️ 2s pause

━━━ Scene 2: Navigate to Test Cases ━━━
  → Click: sidebar "Test Cases"
  🎙️ "Open the Test Cases section from the sidebar."
  ✨ Highlight: sidebar item (pulse)
  ⏸️ 1.5s pause

━━━ Scene 3: Create New Test Case ━━━
  → Click: "Create" button
  🎙️ "Click Create to start a new test case."
  ✨ Highlight: Create button (glow)
  ⏸️ 2s pause

  → Type in title: "Login with valid credentials"
  🎙️ "Give it a descriptive title."
  ⏸️ 1s pause

  → Type in description: "Verify that users can log in..."
  🎙️ "Add a clear description of what this test case verifies."
  ⏸️ 1.5s pause

━━━ Scene 4: Closing ━━━
  → Wait 2s (hold on final screen)
  🎙️ "And that's it — your first test case is ready."
  ⏸️ 1.5s pause

Total estimated: ~90 seconds
```

**Iterate with user:**
- "Want to add/remove any scenes?"
- "Should the pacing be faster or slower?"
- "Any narration text you'd change?"
- "Want to reorder anything?"

### Stage 5: Save & Handoff

Once approved:
1. Save script JSON to `workspace/<date>/demo-script-<name>.json`
2. Save readable version to `workspace/<date>/demo-script-<name>.md`
3. Tell user: "Script ready! Run `/record-demo` to record it, or I can start recording now."

## Script Action Reference

10 supported actions: `navigate`, `click`, `type`, `select`, `scroll`, `hover`, `wait`, `screenshot`, `drag`, `keyboard`.

5 highlight styles: `pulse`, `glow`, `arrow`, `dim-others`, `zoom` (injected via CSS/JS).

Full reference with fields and examples in `references/script-format.md`.

## Narration Guidelines

**Good narration:**
- Short sentences (under 15 words)
- Present tense, active voice ("Click Create" not "We will click on the Create button")
- Describe what's happening AND why ("Add a description so your team knows what to test")
- Don't narrate the obvious ("I'm moving my cursor to..." — no)
- Match the pause to narration length (longer narration = longer pause)

**Pacing rules:**
- First scene: longer pauses (viewer orienting)
- Middle scenes: moderate pauses
- Last scene: hold for 2-3 seconds on the final state
- After typing: short pause to let viewer read
- After page navigation: wait for load + 1s to let viewer scan

**Tone by audience:**
- Prospects: focus on benefits, keep it simple, avoid jargon
- Developers: can use technical terms, show configuration, mention APIs
- Internal: can be more casual, reference team conventions

## Tips for Great Demos

1. **Start with data** — Don't demo on an empty app. Ensure test data exists.
2. **Show the happy path** — Save edge cases for documentation, not demos.
3. **One feature per video** — 90-second focused video > 10-minute tour.
4. **End on the result** — Show the created/completed thing, not a menu.
5. **Name things realistically** — "Login with valid credentials" > "Test 1".
6. **Clean up the UI** — Close unnecessary tabs, hide dev tools, use clean browser profile.
