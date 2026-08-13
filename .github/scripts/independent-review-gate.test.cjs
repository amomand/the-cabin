const test = require("node:test");
const assert = require("node:assert/strict");

const gate = require("./independent-review-gate.cjs");
const { evaluateGate } = gate;

const HEAD = "a".repeat(40);

function review(login, commitId = HEAD, state = "COMMENTED") {
  return { user: { login }, commit_id: commitId, state };
}

test("requires author provenance", () => {
  assert.equal(evaluateGate("", HEAD, [], ["review:routine"]).state, "pending");
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): <!-- Replace with Claude, Codex, Copilot, or Human. -->",
      HEAD,
      [],
      ["review:routine"],
    ).state,
    "pending",
  );
});

test("does not require hosted review for a human-only change", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Human", HEAD, []).state,
    "success",
  );
});

test("treats outside review as advisory only with the routine label", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, []).state,
    "pending",
  );
  const result = evaluateGate(
    "- Authoring agent(s): Codex",
    HEAD,
    [],
    [{ name: "review:routine" }],
  );
  assert.equal(result.state, "success");
  assert.match(result.description, /advisory/);
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): Codex",
      HEAD,
      [],
      ["REVIEW:ROUTINE"],
    ).state,
    "success",
  );
});

test("accepts an independent Copilot review of Codex work", () => {
  const result = evaluateGate("- Authoring agent(s): Codex", HEAD, [
    review("copilot-pull-request-reviewer[bot]"),
  ]);
  assert.equal(result.state, "success");
});

test("rejects same-family and stale reviews", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, [
      review("chatgpt-codex-connector[bot]"),
    ]).state,
    "pending",
  );
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, [
      review("copilot-pull-request-reviewer[bot]", "b".repeat(40)),
    ]).state,
    "pending",
  );
});

test("accepts either hosted family for Claude work", () => {
  for (const login of [
    "copilot-pull-request-reviewer[bot]",
    "chatgpt-codex-connector[bot]",
  ]) {
    assert.equal(
      evaluateGate("- Authoring agent(s): Claude", HEAD, [review(login)]).state,
      "success",
    );
  }
});

test("requires a reviewer family absent from mixed authorship", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Claude, Codex", HEAD, [
      review("copilot-pull-request-reviewer[bot]", HEAD, "APPROVED"),
    ]).state,
    "success",
  );
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex, Copilot", HEAD, [
      review("copilot-pull-request-reviewer[bot]"),
      review("chatgpt-codex-connector[bot]"),
    ]).state,
    "pending",
  );
});

test("accepts only explicit completed review states", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, [
      {
        user: { login: "copilot-pull-request-reviewer[bot]" },
        commit_id: HEAD,
      },
    ]).state,
    "pending",
  );
  for (const state of ["DISMISSED", "PENDING", null, "", "UNKNOWN"]) {
    assert.equal(
      evaluateGate("- Authoring agent(s): Codex", HEAD, [
        review("copilot-pull-request-reviewer[bot]", HEAD, state),
      ]).state,
      "pending",
    );
  }
  for (const state of ["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]) {
    assert.equal(
      evaluateGate("- Authoring agent(s): Codex", HEAD, [
        review("copilot-pull-request-reviewer[bot]", HEAD, state),
      ]).state,
      "success",
    );
  }
});

test("uses each allowed reviewer's latest state on the head", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, [
      review("copilot-pull-request-reviewer[bot]", HEAD, "COMMENTED"),
      review("copilot-pull-request-reviewer[bot]", HEAD, "DISMISSED"),
    ]).state,
    "pending",
  );
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, [
      review("copilot-pull-request-reviewer[bot]", HEAD, "DISMISSED"),
      review("copilot-pull-request-reviewer[bot]", HEAD, "COMMENTED"),
    ]).state,
    "success",
  );
});

test("can evaluate a pull request supplied by a trusted workflow", async () => {
  let status;
  await gate({
    github: {
      paginate: async () => [],
      rest: {
        pulls: { listReviews() {} },
        repos: {
          createCommitStatus: async (value) => {
            status = value;
          },
        },
      },
    },
    context: {
      payload: {},
      repo: { owner: "example", repo: "the-cabin" },
    },
    core: { info() {} },
    pullRequest: {
      number: 42,
      body: "- Authoring agent(s): Codex",
      labels: [{ name: "review:routine" }],
      head: { sha: HEAD },
      html_url: "https://example.test/pull/42",
    },
  });

  assert.equal(status.state, "success");
  assert.equal(status.sha, HEAD);
  assert.equal(status.context, "independent-review");
});

function openPull(number, sha, body = "- Authoring agent(s): Codex") {
  return {
    number,
    body,
    labels: [],
    head: { sha },
    html_url: `https://example.test/pull/${number}`,
  };
}

function sweepHarness({ pulls, reviews = {}, published = {} }) {
  const created = [];
  const warnings = [];
  const rest = {
    pulls: {
      list() {},
      listReviews() {},
    },
    repos: {
      getCombinedStatusForRef: async ({ ref }) => ({
        data: { statuses: published[ref] ? [published[ref]] : [] },
      }),
      createCommitStatus: async (value) => {
        created.push(value);
      },
    },
  };
  const github = {
    rest,
    paginate: async (endpoint, params) => {
      if (endpoint === rest.pulls.list) {
        return pulls;
      }
      if (endpoint === rest.pulls.listReviews) {
        const entry = reviews[params.pull_number];
        if (entry instanceof Error) {
          throw entry;
        }
        return entry || [];
      }
      throw new Error("unexpected endpoint");
    },
  };
  return {
    created,
    warnings,
    github,
    context: { payload: {}, repo: { owner: "example", repo: "the-cabin" } },
    core: {
      info() {},
      warning(message) {
        warnings.push(message);
      },
    },
  };
}

test("the sweep evaluates every open pull request", async () => {
  const other = "b".repeat(40);
  const harness = sweepHarness({
    pulls: [openPull(1, HEAD), openPull(2, other)],
    reviews: { 1: [review("copilot-pull-request-reviewer[bot]")] },
  });

  const count = await gate.sweep(harness);

  assert.equal(count, 2);
  assert.deepEqual(
    harness.created.map((status) => [status.sha, status.state]),
    [
      [HEAD, "success"],
      [other, "pending"],
    ],
  );
  assert.equal(harness.created[0].context, "independent-review");
});

test("the sweep leaves an unchanged status alone", async () => {
  const harness = sweepHarness({
    pulls: [openPull(1, HEAD)],
    published: {
      [HEAD]: {
        context: "independent-review",
        state: "pending",
        description: "awaiting an independent review of the current head",
      },
    },
  });

  await gate.sweep(harness);

  assert.deepEqual(harness.created, []);
});

test("the sweep rewrites a status whose verdict has moved", async () => {
  const harness = sweepHarness({
    pulls: [openPull(1, HEAD)],
    reviews: { 1: [review("copilot-pull-request-reviewer[bot]")] },
    published: {
      [HEAD]: {
        context: "independent-review",
        state: "pending",
        description: "awaiting an independent review of the current head",
      },
    },
  });

  await gate.sweep(harness);

  assert.equal(harness.created.length, 1);
  assert.equal(harness.created[0].state, "success");
});

test("one unevaluable pull request does not stop the sweep", async () => {
  const other = "b".repeat(40);
  const harness = sweepHarness({
    pulls: [openPull(1, HEAD), openPull(2, other)],
    reviews: { 1: new Error("boom") },
  });

  const count = await gate.sweep(harness);

  assert.equal(count, 2);
  assert.deepEqual(
    harness.created.map((status) => status.sha),
    [other],
  );
  assert.match(harness.warnings[0], /#1 could not be evaluated: boom/);
});
