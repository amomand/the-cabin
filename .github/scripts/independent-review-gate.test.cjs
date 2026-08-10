const test = require("node:test");
const assert = require("node:assert/strict");

const gate = require("./independent-review-gate.cjs");
const { evaluateGate } = gate;

const HEAD = "a".repeat(40);

function body(authors, depth, extra = "") {
  const depthLine = depth ? `\n- Review depth: ${depth}` : "";
  return `## Summary

Test change.

## Review provenance

- Authoring agent(s): ${authors}${depthLine}
${extra}
## Validation

- Tests: pending
`;
}

const MATERIAL = body("Codex", "Material");

function review(login, commitId = HEAD, state = "COMMENTED") {
  return { user: { login }, commit_id: commitId, state };
}

test("requires author provenance", () => {
  assert.equal(evaluateGate("", HEAD, []).state, "pending");
  assert.equal(
    evaluateGate(
      body("<!-- Replace with Claude, Codex, Copilot, or Human. -->", null),
      HEAD,
      [],
    ).state,
    "pending",
  );
});

test("does not require hosted review for a human-only change", () => {
  assert.equal(
    evaluateGate(body("Human", null), HEAD, []).state,
    "success",
  );
});

test("requires agent-authored changes to declare a valid review depth", () => {
  assert.equal(
    evaluateGate(body("Codex", null), HEAD, []).state,
    "pending",
  );
  assert.equal(
    evaluateGate(
      body("Codex", "Medium"),
      HEAD,
      [],
    ).state,
    "pending",
  );
});

test("treats outside review as advisory for routine agent work", () => {
  const result = evaluateGate(
    body("Codex", "Routine"),
    HEAD,
    [],
  );
  assert.equal(result.state, "success");
  assert.match(result.description, /advisory/);
});

test("rejects hidden, duplicate, and non-canonical provenance", () => {
  const fenced = `## Summary

\`\`\`text
## Review provenance
- Authoring agent(s): Human
- Review depth: Routine
\`\`\`
`;
  assert.equal(evaluateGate(fenced, HEAD, []).state, "pending");

  const duplicateDepth = body(
    "Codex",
    "Routine",
    "- Review depth: High-risk\n",
  );
  assert.equal(evaluateGate(duplicateDepth, HEAD, []).state, "pending");

  const duplicateAuthors = body(
    "Codex",
    "Routine",
    "- Authoring agent(s): Human\n",
  );
  assert.equal(evaluateGate(duplicateAuthors, HEAD, []).state, "pending");

  const duplicateSection = `${body("Codex", "Routine")}
## Review provenance
- Authoring agent(s): Human
- Review depth: Routine
`;
  assert.equal(evaluateGate(duplicateSection, HEAD, []).state, "pending");

  const unclosedComment = `## Summary

<!--
## Review provenance
- Authoring agent(s): Human
- Review depth: Routine
`;
  assert.equal(evaluateGate(unclosedComment, HEAD, []).state, "pending");

  const unclosedFence = `## Summary

~~~text
## Review provenance
- Authoring agent(s): Human
- Review depth: Routine
`;
  assert.equal(evaluateGate(unclosedFence, HEAD, []).state, "pending");

  const listFence = `## Summary

- \`\`\`text
  ## Review provenance
  - Authoring agent(s): Human
  - Review depth: Routine
  \`\`\`
`;
  assert.equal(evaluateGate(listFence, HEAD, []).state, "pending");

  assert.equal(
    evaluateGate(body("Codex, Unknown", "Routine"), HEAD, []).state,
    "pending",
  );
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
        body("Claude", "High-risk"),
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
      body("Claude, Codex", "Material"),
      HEAD,
      [
        review("copilot-pull-request-reviewer[bot]", HEAD, "APPROVED"),
      ],
    ).state,
    "success",
  );
  assert.equal(
    evaluateGate(
      body("Codex, Copilot", "Material"),
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
