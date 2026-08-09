const test = require("node:test");
const assert = require("node:assert/strict");

const gate = require("./independent-review-gate.cjs");
const { evaluateGate } = gate;

const HEAD = "a".repeat(40);

function review(login, commitId = HEAD, state = "COMMENTED") {
  return { user: { login }, commit_id: commitId, state };
}

test("requires author provenance", () => {
  assert.equal(evaluateGate("", HEAD, []).state, "pending");
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): <!-- Replace with Claude, Codex, Copilot, or Human. -->",
      HEAD,
      [],
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

test("can evaluate a pull request supplied by a trusted workflow", async () => {
  let status;
  await gate({
    github: {
      paginate: async () => [review("copilot-pull-request-reviewer[bot]")],
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
      head: { sha: HEAD },
      html_url: "https://example.test/pull/42",
    },
  });

  assert.equal(status.state, "success");
  assert.equal(status.sha, HEAD);
  assert.equal(status.context, "independent-review");
});
