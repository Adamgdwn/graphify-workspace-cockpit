# Video Script: From One Folder to a Cross-Repo Decision Map

Last Updated: 2026-06-20T23:00:14-06:00

Reference video this responds to:
https://www.youtube.com/watch?v=mWLDn49_8HA
("Graphify + Obsidian + Claude Code = CHEAT CODE")

Premise: walk the build story in order — Graphify's original token-saving intent,
one folder, then the staged work it took to connect many folders, then the node
limit and why it exists, then the advanced features framed as *how each one
changes a coding decision*. The "why I didn't need Obsidian" argument is folded
in near the end, grounded in what Obsidian actually is, not a strawman.

Tone: direct, technical, first-person builder voice. No hype words. Show, don't
tell — if the demo proves it, don't re-explain it.

---

## YouTube Comment (short-form, drop on the reference video anytime)

> Good walkthrough. One thing worth adding: you don't actually need Obsidian as
> the middle layer to get cross-repo knowledge. Graphify is repo-scoped by
> default, but point `graphify update` at your workspace root and you get one
> unified graph spanning every repo at once. The reason Obsidian gets pulled in
> is aggregation — but its graph is a visual view of wikilinks, not a queryable
> graph, so an agent reading the vault is still reading Markdown files and paying
> tokens for it. Querying the graph directly keeps the whole point of Graphify
> intact: traverse to a scoped subgraph, read only that, skip the documents. I
> built a local browser cockpit on top of the unified graph — ask across repos,
> see the evidence, make a durable call, hand a tight context to the agent. Obsidian
> is still great for handwritten notes; it's just not required in this chain.

---

## Full Video Script (~8 min, timestamps are a guide)

### Hook (0:00–0:30)

[screen: the multi-repo map already open; semantic links lit only if the chosen
scope has actionable overlap]

There's a popular setup going around: Graphify, plus Obsidian, plus Claude Code,
as a way to give your AI a cross-repo brain. It works. But it's three moving
parts, and one of them — Obsidian — is only there to do a job Graphify can
already do by itself.

I want to show you the version with the middle layer removed, and I want to build
it up the way it actually came together: one folder, then many folders, then the
guardrails, then the features that change how I actually write code.

---

### 1 — What Graphify is for (0:30–1:15)

[screen: a terminal, then a small graph.json]

Start with the original intent, because everything else follows from it.

Graphify reads a codebase and produces a semantic graph — `graph.json`. Nodes are
files, functions, concepts, documents. Edges are the relationships between them.

The point of that graph is not the picture. The point is that you can *query* it
instead of *reading* everything. Ask "where does authentication live," and the
tool walks the graph, hands you the handful of nodes that matter, and you read
those — not forty files. That's the whole idea: spend tokens on the answer, not on
re-reading the repo every time you have a question.

Keep that in your head — query the graph, don't read the documents — because it's
the test I hold every feature against.

---

### 2 — One folder (1:15–2:00)

[screen: run Graphify on a single repo; open the resulting map]

Here it is at its simplest. One repo. One graph. I ask it a question, it gives me
the relevant slice, I get to work. For a single project, this is already a better
deal than scrolling through files.

[screen: click a node, show its neighbors]

Click anything and you see what it actually connects to. This is the unit
everybody starts with, and for one folder it just works.

The catch shows up the moment you have more than one folder.

---

### 3 — Many folders, and the staged work to connect them (2:00–4:00)

[screen: workspace root with many repos]

Most of us don't have one repo. I've got a whole workspace of them. And Graphify
is repo-scoped by default — run it ten times, you get ten graphs and no single
place to ask a question across all of them.

That's the exact gap Obsidian usually gets hired to fill. But the fix isn't a
second app — it's one command, and the whole trick is *where you aim it.*

Not at one repo. Not at your whole drive. At a single parent folder you pick.
Graphify walks every repo nested inside that folder and fuses them into *one*
graph. Mine sits at the top of my workspace, so it pulls in every project I've
got — and nothing outside that folder. It also skips the noise on its own: the
hidden git folders, anything secret like `.env` files, `node_modules`, build
output. What's left is the source — the part you actually reason about.

So when I say "the whole workspace," I mean exactly that one folder and
everything under it. Not the rest of the machine.

[screen: the broad workspace graph — deliberately show it looking dense]

Except — here's the honest part — pointing it at the whole workspace gives you a
hairball.
"Workspace graph" quietly turns into "every file is a node," and that buries the
signal you actually wanted. Getting from that hairball to something you can make
decisions from took real work, and it went in stages:

[screen: step through the map gaining structure as each is described]

- **Summary layer** — zoom out. Show whole repos as single blobs instead of every
  file. A map of neighborhoods, not a pile of streets.
- **Overlap** — light up where two repos are doing the same job. That's your
  duplication, right there in front of you.
- **Gap triage** — when two things look disconnected, label *why*: truly separate,
  hidden by a filter, or the tool just didn't read the link. A gap becomes an
  answer instead of a shrug.
- **Importance lens** — turn up the files that matter — the key docs, the
  contracts — and turn down the auto-generated noise.
- **Decision overlay** — color the map by the calls I've already made: invest,
  ship, archive. My judgment shows up on it, not just the code.
- **Layout** — lay the repos side by side, each with a big label that stays
  readable no matter how far I zoom. Now you can actually compare them.

[screen: the finished multi-repo comparison; show semantic links if the selected
scope earns them, otherwise show the semantic count/status copy]

The headline signal is right here when it exists: the **semantic links that cross
between repos** - the same concept showing up in two different projects. That's
the thing you can't see when each repo lives in its own graph, and it's the
reason to build one unified graph at all.

And the semantic layer had to evolve. The first version could say "these two
things are similar," but that is not enough. The bright green links now have to
answer a more practical question: *so what?* Is this duplicate work, a drift risk,
a missing bridge, a shared pattern, or a cross-app capability? Raw similarity can
still be stored, but the map only spends attention on links that might change a
decision. If the scope shows zero bright links, that may be the correct answer:
there may be raw matches, but no decision-grade overlap.

---

### 4 — Why there's a node limit, and what it protects (4:00–4:45)

[screen: try to open the full Evidence view on the whole workspace; show the cap notice]

Now the guardrail, because I built one in on purpose.

My real workspace graph is around forty thousand nodes. You cannot render forty
thousand nodes in a browser and call it usable — and I learned that the hard way.
Broad testing had the full-evidence view trying to draw over twenty-two thousand
nodes at once and dragging the browser to a crawl before I could even narrow the
scope.

So there's a hard cap: the full file-level Evidence view tops out at **15,000
visible nodes**. Past that, the backend refuses the request, and the map keeps you
in the overview-and-drill-down path instead — pick a region, then go deep.

[screen: drill from a region down into one repo]

This isn't a limitation I'm apologizing for. It's the same principle as the
queries: don't try to look at everything at once. Look at the right slice. The cap
protects the browser; the query model protects your token budget; both are saying
the same thing — *scope first.*

---

### 5 — The features, and the coding decision each one changes (4:45–6:45)

[screen: the cockpit, Command tab]

Now the part that actually pays off. I'm not going to read you a feature list — for
each one, watch the decision it changes.

- **Command** — the first screen isn't a graph, it's an attention list. Pending
  recommendations, untriaged overlaps, whether the graph is even fresh enough to
  trust. *The decision it changes:* what I work on next, before I've opened a
  single file.

- **Ask** — I type a question that spans repos: "what have I already built for
  PDF parsing?" It runs against the graph and comes back with an answer plus the
  evidence nodes behind it. *The decision it changes:* build-vs-reuse — answered in
  a few thousand tokens instead of an afternoon of grep.

  [screen: click an evidence node → lands in Map]

  And the evidence is clickable. The answer isn't a wall of text, it drops me
  exactly where it came from.

- **Map — Explore** — see what already exists across the whole workspace. *Changes:*
  whether I start something new or extend something that's there.

- **Map — Trace** — "why are these two things connected?" It walks the shortest
  path between them. *Changes:* I see the blast radius of a shared module *before*
  I edit it, not after something breaks.

- **Map — Overlap** — where are two repos solving the same problem? *Changes:* the
  consolidate-or-keep-separate call, with the duplication actually in front of me.

- **Decisions** — I record the human call: invest, client-ready, monitor, archive,
  paused. It persists, and it shows up on the map. *Changes:* future me — and any
  agent I hand this to — doesn't relitigate a decision I already made.

- **Recommendations** — the AI compresses the evidence into a proposed next step,
  with confidence, risk, and a decision packet showing where the work goes and how
  to roll it back. *Changes:* I'm approving or rejecting a grounded proposal, not
  generating one from scratch. The model proposes; I stay the governor.

- **Work Queue** — and even an accepted recommendation doesn't just run. It becomes
  a queued action behind a dry-run preview and an explicit approval. *Changes:*
  nothing touches the repos without me seeing the preview first.

[screen: pan back to the map]

Every one of those read the graph, not the files. That's the original intent,
still intact — I just wrapped it in a surface where the answers turn into
decisions.

---

### 6 — Why I didn't need Obsidian (6:45–7:40)

[screen: split — the reference video's Obsidian vault on one side, the cockpit on the other]

So, back to the setup I started with. Why isn't Obsidian in here?

Be fair about what Obsidian is genuinely good at first: it's a fantastic place for
*handwritten* knowledge — design notes, meeting records, the why-we-chose-this that
no code graph can infer. Backlinks, mobile capture, a huge plugin ecosystem. If
your second brain is mostly prose you wrote yourself, Obsidian earns its place.

But look at the job it's doing in *this* chain. It's the aggregation layer — the
single place to query across repos. And here's the thing most people don't notice:
Obsidian's graph is a *visual* force-directed view of wikilinks between Markdown
notes. It is not a queryable graph. There's no graph API that hands an agent a
scoped subgraph — the Obsidian team has said as much; the graph view is a picture
for humans, not an interface for machines.

Which means when Claude Code "uses" your vault, it's doing the one thing Graphify
was built to avoid: **reading Markdown files.** You're back to paying tokens to
read documents — just nicely linked ones.

[screen: the Ask tab returning a scoped answer]

The unified graph keeps the original deal. Traverse to the neighborhood that
matters, read only that, hand the agent a tight context. The aggregation Obsidian
was hired for, Graphify does in one command at the workspace root — and it does it
as a graph you can actually query, not a folder you have to read.

So: keep Obsidian for the notes you write by hand. You just don't need it standing
between Graphify and your agent.

---

### Close (7:40–8:00)

[screen: the multi-repo map; semantic overlay status visible, with links lit if
the selected scope has actionable overlap]

One graph across every repo. A cap that keeps you scoped. Features that turn the
graph into decisions instead of dumping it on you. And the original promise — query
the graph, don't read the repo — carried all the way through.

It's local, it's open, and if you already run Graphify, you're one command at your
workspace root away from this.

---

## Recording Notes

- **Read live numbers off the Command tab; don't hardcode them.** Counts drift
  every time the graph is rebuilt. The script deliberately uses round phrasing
  ("around forty thousand nodes," "over twenty-two thousand") so it stays true
  between refreshes. The one exact figure that's a *design constant*, not a live
  count, is the 15,000-node Evidence cap — that's safe to state precisely.
- **The node cap is real and demonstrable.** `FULL_GRAPH_NODE_LIMIT = 15000` in
  `frontend/src/tabs/Map.tsx`; the backend returns `413 GRAPH_FULL_TOO_LARGE` on
  oversized `/graph/full` requests with the message "Full evidence graph is too
  large for default browser rendering. Use the overview/drilldown map or narrow
  the workspace scope." You can trigger it live on the full workspace.
- **The scope claim in Section 3 is verifiable, so state it confidently.** The
  graph is built from exactly one root, recorded in
  `Tools/graphify/workspace/out/.graphify_root` (currently
  `/home/adamgoodwin/code`). It recurses every repo *under* that folder and
  nothing outside it; ignores live in `Tools/graphify/workspace/.graphifyignore`
  (git internals, `.env`/keys, `node_modules`, build output). Say "every repo
  under one folder I choose," never "the whole drive" — the latter is false.
- **The staged build (Section 3) maps to Slices 1–5** in
  `docs/relationship-map-plan.md` (summary layer → broad overlap → gap triage →
  importance lens → decision overlay) plus the comparison-layout + constant-size
  label fix. Use that doc if you want exact dates/commits on screen.
- **Pick the demo repos live.** The recorded sign-off used Timeshare-Connect /
  vector-conversion-tool / mermaid-tool as the comparison trio because they show a
  clean cross-repo semantic link. Use whatever set reads clearest on the day.
- **Semantic overlay is actionability-first now.** Bright green means a
  cross-folder or cross-repo link cleared the "so what?" filter: duplicate, gap,
  drift, shared pattern, intentional reference, or cross-app similarity. If the
  button shows something like `Semantic (0/14)`, read it as 0 actionable links out
  of 14 raw in-scope matches, not as a failure.
- **Do not force a semantic-link demo from a bad scope.** After the June 20 video
  shoot, the honest recording lesson is that many scopes should show zero
  actionable semantic overlap. For a visible semantic demo, use a current
  multi-repo scope that actually earns links; the Governed Agent Lab /
  chuwi-optimizer tuning scope promoted only a handful of `loop` and `memory`
  links after scaffolding and generic-symbol matches were demoted.
- **Out-of-scope semantic-cache warnings are narratable.** If the map says stored
  semantic edges are outside the Evidence scope, that means the semantic cache was
  built against a broader or different graph. Say "the stored cache is broader
  than this selected folder," then rerun Semantic Analysis for the recording scope
  if you need fresh cross-folder links.
- **Smoke-check before recording:**
  `source "$HOME/.nvm/nvm.sh" && node scripts/demo-path-smoke.mjs` — verifies
  backend health, graph summary, Ask evidence, and the core endpoints. Full demo
  preconditions are in `docs/demo-path-checklist.md`.
- **What to narrate vs. show:** Sections 1–2 can be mostly narrated over a small
  graph. Section 3's staged build is strongest if the map visibly gains structure
  as you describe each stage — pre-stage the views. Section 6 (Obsidian) is a
  talking-head + split-screen beat; nothing to demo live unless you have a vault
  on hand.
- **Obsidian claims are sourced** (see below) so the comparison holds up to a
  developer audience. Keep it fair: lead with what Obsidian is good at, then make
  the narrow, true point about the aggregation job.

---

## Sources for the Obsidian comparison (so the claims are defensible)

These back the Section 6 argument. The point is fairness — Obsidian is excellent
at human PKM; it just isn't a queryable graph for an agent.

- **Obsidian's graph is a visual, force-directed view of wikilinks/tags**, not a
  semantic graph with typed edges — Obsidian Graph view docs (obsidian.md/help).
- **No official graph-query / traversal API**, and likely never one ("very
  complicated internally") — Obsidian forum, "Graph Rendering API" and "Graph query
  language / API" threads; Neo4j integrations exist precisely because querying must
  happen *outside* Obsidian.
- **Typed links only via plugins** (Juggl, Breadcrumbs) and non-standard — juggl.io
  link-types; not consumable as a stable machine interface.
- **Agents "using" a vault read Markdown files** — the Obsidian + Claude Code
  "second brain" workflows point the agent at the vault folder and have it read /
  edit notes; the graph aids human navigation, not the agent's retrieval.
- **Graph-based retrieval is the token-efficient path** — traversal happens outside
  the LLM; only the scoped neighborhood's snippets are sent (Graph RAG / TERAG,
  arXiv:2509.18667). This is the same principle as Graphify's query model.

Full research with citations is in this session's tool-results if a deeper writeup
is ever needed.
