# Video Script: "I Skipped Obsidian Entirely"

Last Updated: 2026-06-15T16:30:47-06:00

Reference video: https://www.youtube.com/watch?v=mWLDn49_8HA
("Graphify + Obsidian + Claude Code = CHEAT CODE")

Context: That video shows Graphify → Obsidian → Claude Code as a cross-repo
knowledge workflow. This script demos the cockpit as the simpler alternative:
one unified graph, one UI, no Obsidian install required. Cloud connectors for
SharePoint and OneNote are now built as opt-in sources.

---

## YouTube Comment (short-form, drop anytime)

> Great breakdown. Worth noting — if you want the cross-repo aggregation without
> Obsidian as the middle layer, that's actually solvable with Graphify alone. Run
> `graphify update` against your workspace root (not just a single repo) and you
> get one unified graph spanning everything. I built a cockpit UI on top of that —
> browser-based, no Obsidian install needed — with Command, Ask, Map, Decisions,
> Recommendations, Work Queue, and a floating assistant all querying the same
> live graph. The useful part is the decision flow: evidence, map context,
> human decisions, decision packets, recommendations, and dry-run-gated actions
> in one place.
> SharePoint and OneNote can fold in as opt-in cloud sources. Happy to share more when it's ready to show.

---

## Full Video Script

### Hook (0:00–0:30)

You just saw a video that shows you how to combine Graphify with Obsidian to get
a cross-repo knowledge layer Claude Code can query. It works. But it's three
moving parts — Graphify, Obsidian, and Claude Code — and Obsidian is doing one
specific job: aggregating multiple graphs into one place you can query.

I built something that removes that middle step entirely. Let me show you.

---

### The Problem It Solves (0:30–1:00)

The Obsidian layer exists because Graphify, out of the box, is repo-scoped. You
run it on one folder, you get one graph. If you have ten repos, you have ten
graphs and no single place to ask questions across all of them.

The fix isn't Obsidian. The fix is pointing Graphify at your workspace root —
the parent folder that contains all your repos — and building one graph from
everything. That's already a Graphify feature. Nobody's talking about it.

---

### The Cockpit Demo (1:00–3:30)

[open browser — show the cockpit UI]

This is the Graphify Workspace Cockpit. It's a local web app — no account, no
cloud, no Obsidian install.

[Command tab] The first screen is not a graph. It's an operator console. It
shows me where attention is needed: pending recommendations, accepted work that
hasn't been queued, dry-run-ready actions, untriaged overlaps, and whether the
graph is fresh enough to trust.

[Ask tab] Now watch this. I'm going to ask a question that spans multiple repos.
"What decisions have been made about the authentication layer across my projects?"
[show result — real graph-backed answer, node citations]

[click evidence node into Map] The evidence is clickable, so the answer is not
just text. It lands me directly on the map context that produced it.

[Map tab] Here's the graph view — this isn't a single repo. These are real edges
across the workspace. I can explore, trace why two things are connected, review
semantic overlaps, or inspect evidence for a decision.

[Overlap mode] This is where the tool starts acting less like a dashboard and
more like a decision surface. It can show me possible duplication across
clusters, triage those overlaps, and turn the ones worth acting on into
recommendations.

[Decisions tab] This is the human ledger. The model doesn't decide for me. I
classify an area as invest, client-ready, monitor, archive, or paused, and the
decision persists with rationale.

[Recommendations tab] Actionable next steps, grounded in what the graph actually shows.
The recommendation is not just "merge this." It has a decision packet: what
evidence supports it, what each side does, where the work should happen, what
the likely savings are, what risks remain, and where the approval gate is.

[Work Queue] And accepted recommendations still don't execute anything. They
become queued actions, each action has to pass a dry run, and execution remains
behind explicit human approval.

[Settings or export mention] The output can also be exported in a format my AI
agents can consume — no copy-paste into Obsidian, no manual wikilinks.

---

### The Obsidian Comparison (3:30–4:15)

What does Obsidian give you that this doesn't? A pretty graph view, backlinks,
and a place to write your own notes alongside the auto-generated ones. That's
genuinely useful — I'm not saying Obsidian is wrong.

But if what you actually need is: ask questions across all your repos, inspect
the evidence, make a durable call, and safely hand the next step to an agent —
you don't need Obsidian in that chain. You need a graph that spans everything
and a cockpit that turns that graph into decisions. That's this.

---

### What's Coming (4:15–4:45)

The next step is deciding which sources to connect. SharePoint and OneNote use
the same interface and the same Ask tab, so your questions can span code and
documents without adding a second knowledge app.

That's the thing I care about most: not just a bigger graph, but a better
decision loop. Code, docs, recommendations, decisions, and approved actions all
stay connected.

---

### Close (4:45–5:00)

Everything you saw here is open-source and running locally. Link in the
description. If you already use Graphify, you're one command away from this.

---

## Recording Notes

- The current local repo graph refresh reports 923 nodes and 7,879 links in
  `graphify-out/graph.json`; the live semantic edge cache used by overlap review
  still reports 14,501 semantic edges when available.
- Cloud connectors are now built and opt-in. Only include them in the recording
  if the demo environment has SharePoint or OneNote configured.
- The rest of the cockpit (Command, Ask, Map, Decisions, Recommendations, Work
  Queue, Settings, AI assistant, decision packet panel, demo-mode banner) is demo-ready now against the
  real graph.
