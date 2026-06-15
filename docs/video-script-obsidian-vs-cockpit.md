# Video Script: "I Skipped Obsidian Entirely"

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
> Recommendations, and a Work Queue all querying the same live graph. SharePoint
> and OneNote can fold in as opt-in cloud sources. Happy to share more when it's ready to show.

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

[Ask tab] Watch this. I'm going to ask a question that spans multiple repos.
"What decisions have been made about the authentication layer across my projects?"
[show result — real graph-backed answer, node citations]

[Map tab] Here's the graph view — this isn't a single repo. These are real edges
across the workspace. Every node is a concept, file, or decision. Every edge is a
real relationship Graphify found.

[Decisions tab] These aren't notes I wrote. These were extracted from the graph —
architectural decisions surfaced automatically.

[Recommendations tab] Actionable next steps, grounded in what the graph actually shows.

[Work Queue] And this exports directly in a format my AI agents can consume — no
copy-paste into Obsidian, no manual wikilinks.

---

### The Obsidian Comparison (3:30–4:15)

What does Obsidian give you that this doesn't? A pretty graph view, backlinks,
and a place to write your own notes alongside the auto-generated ones. That's
genuinely useful — I'm not saying Obsidian is wrong.

But if what you actually need is: ask questions across all your repos, get
structured answers, and pipe the output into the next step of your workflow —
you don't need Obsidian in that chain. You need a graph that spans everything
and a UI that queries it. That's this.

---

### What's Coming (4:15–4:45)

The next step is deciding which sources to connect. SharePoint and OneNote use
the same interface and the same Ask tab, so your questions can span code and
documents without adding a second knowledge app.

That's the thing Obsidian can't easily do — pull live cloud content into the
same queryable structure as your codebase.

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
  Queue, Settings, AI assistant, demo-mode banner) is demo-ready now against the
  real graph.
