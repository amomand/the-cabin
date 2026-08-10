const test = require("node:test");
const assert = require("node:assert/strict");

const gate = require("./independent-review-gate.cjs");
const { evaluateGate } = gate;

const HEAD = "a".repeat(40);
const MATERIAL = "- Authoring agent(s): Codex\n- Review depth: Material";

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

test("requires agent-authored changes to declare a valid review depth", () => {
  assert.equal(
    evaluateGate("- Authoring agent(s): Codex", HEAD, []).state,
    "pending",
  );
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): Codex\n- Review depth: Medium",
      HEAD,
      [],
    ).state,
    "pending",
  );
});

test("treats outside review as advisory for routine agent work", () => {
  const result = evaluateGate(
    "- Authoring agent(s): Codex\n- Review depth: Routine",
    HEAD,
    [],
  );
  assert.equal(result.state, "success");
  assert.match(result.description, /advisory/);
});

test("accepts an independent Copilot review of Codex work", () => {
  const result = evaluateGate(MATERIAL, HEAD, [
    review("copilot-pull-request-reviewer[bot]"),
  ]);
  assert.equal(result.state, "success");
});

test("rejects same-family and stale reviews", () => {
  assert.equal(
    evaluateGate(MATERIAL, HEAD, [
      review("chatgpt-codex-connector[bot]"),
    ]).state,
    "pending",
  );
  assert.equal(
    evaluateGate(MATERIAL, HEAD, [
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
      evaluateGate(
        "- Authoring agent(s): Claude\n- Review depth: High-risk",
        HEAD,
        [review(login)],
      ).state,
      "success",
    );
  }
});

test("requires a reviewer family absent from mixed authorship", () => {
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): Claude, Codex\n- Review depth: Material",
      HEAD,
      [
        review("copilot-pull-request-reviewer[bot]", HEAD, "APPROVED"),
      ],
    ).state,
    "success",
  );
  assert.equal(
    evaluateGate(
      "- Authoring agent(s): Codex, Copilot\n- Review depth: Material",
      HEAD,
      [
        review("copilot-pull-request-reviewer[bot]"),
        review("chatgpt-codex-connector[bot]"),
      ],
    ).state,
    "pending",
  );
});

test("accepts only explicit completed review states", () => {
  assert.equal(
    evaluateGate(MATERIAL, HEAD, [
      {
        user: { login: "copilot-pull-request-reviewer[bot]" },
        commit_id: HEAD,
      },
    ]).state,
    "pending",
  );
  for (const state of ["DISMISSED", "PENDING", null, "", "UNKNOWN"]) {
    assert.equal(
      evaluateGate(MATERIAL, HEAD, [
        review("copilot-pull-request-reviewer[bot]", HEAD, state),
      ]).state,
      "pending",
    );
  }
  for (const state of ["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]) {
    assert.equal(
      evaluateGate(MATERIAL, HEAD, [
        review("copilot-pull-request-reviewer[bot]", HEAD, state),
      ]).state,
      "success",
    );
  }
});

test("uses each allowed reviewer's latest state on the head", () => {
  assert.equal(
    evaluateGate(MATERIAL, HEAD, [
      review("copilot-pull-request-reviewer[bot]", HEAD, "COMMENTED"),
      review("copilot-pull-request-reviewer[bot]", HEAD, "DISMISSED"),
    ]).state,
    "pending",
  );
  assert.equal(
    evaluateGate(MATERIAL, HEAD, [
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
      body: MATERIAL,
      head: { sha: HEAD },
      html_url: "https://example.test/pull/42",
    },
  });

  assert.equal(status.state, "success");
  assert.equal(status.sha, HEAD);
  assert.equal(status.context, "independent-review");
});
