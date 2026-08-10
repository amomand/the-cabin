const REVIEWER_FAMILIES = new Map([
  ["copilot-pull-request-reviewer[bot]", "Copilot"],
  ["chatgpt-codex-connector[bot]", "Codex"],
]);

const AUTHOR_FAMILIES = ["Claude", "Codex", "Copilot", "Human"];
const REVIEW_DEPTHS = new Map([
  ["routine", "Routine"],
  ["material", "Material"],
  ["high-risk", "High-risk"],
  ["high risk", "High-risk"],
]);
const COMPLETED_REVIEW_STATES = new Set([
  "APPROVED",
  "CHANGES_REQUESTED",
  "COMMENTED",
]);

function visibleMarkdown(body) {
  let text = body || "";
  let withoutComments = "";
  let cursor = 0;
  while (cursor < text.length) {
    const start = text.indexOf("<!--", cursor);
    if (start === -1) {
      withoutComments += text.slice(cursor);
      break;
    }
    withoutComments += text.slice(cursor, start);
    const end = text.indexOf("-->", start + 4);
    if (end === -1) {
      break;
    }
    cursor = end + 3;
  }

  const visible = [];
  let fence = null;
  for (const line of withoutComments.split("\n")) {
    const marker = line.match(/^ {0,3}(`{3,}|~{3,})/);
    if (!fence && marker) {
      fence = { character: marker[1][0], length: marker[1].length };
      continue;
    }
    if (fence) {
      const closing = line.match(/^ {0,3}(`{3,}|~{3,})\s*$/);
      if (
        closing &&
        closing[1][0] === fence.character &&
        closing[1].length >= fence.length
      ) {
        fence = null;
      }
      continue;
    }
    visible.push(line);
  }
  return visible.join("\n");
}

function reviewProvenanceSection(body) {
  const visible = visibleMarkdown(body);
  const heading = /^##[ \t]+Review provenance[ \t]*$/gim;
  const matches = [...visible.matchAll(heading)];
  if (matches.length !== 1) {
    return null;
  }
  const rest = visible.slice(matches[0].index + matches[0][0].length);
  const nextSection = rest.search(/^##[ \t]+/m);
  return nextSection === -1 ? rest : rest.slice(0, nextSection);
}

function provenanceField(body, label) {
  const section = reviewProvenanceSection(body);
  if (section === null) {
    return null;
  }
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const field = new RegExp(
    `^-[ \\t]+${escaped}:[ \\t]*(.+?)[ \\t]*$`,
    "gim",
  );
  const matches = [...section.matchAll(field)];
  return matches.length === 1 ? matches[0][1].trim() : null;
}

function authorFamilies(body) {
  const value = provenanceField(body, "Authoring agent(s)");
  if (!value) {
    return new Set();
  }
  const canonical = new Map(
    AUTHOR_FAMILIES.map((family) => [family.toLowerCase(), family]),
  );
  const names = value.split(",").map((name) => name.trim().toLowerCase());
  if (
    names.length === 0 ||
    names.some((name) => !canonical.has(name)) ||
    new Set(names).size !== names.length
  ) {
    return new Set();
  }
  return new Set(names.map((name) => canonical.get(name)));
}

function reviewDepth(body) {
  const value = provenanceField(body, "Review depth");
  if (!value) {
    return null;
  }
  return REVIEW_DEPTHS.get(value.toLowerCase()) || null;
}

function evaluateGate(body, headSha, reviews) {
  const authors = authorFamilies(body);
  if (authors.size === 0) {
    return {
      state: "pending",
      description: "record the PR authoring agent family",
    };
  }

  const agentAuthors = new Set(
    [...authors].filter((family) => family !== "Human"),
  );
  if (agentAuthors.size === 0) {
    return {
      state: "success",
      description: "human-authored change; hosted review is not required",
    };
  }

  const depth = reviewDepth(body);
  if (!depth) {
    return {
      state: "pending",
      description: "record Routine, Material, or High-risk review depth",
    };
  }
  if (depth === "Routine") {
    return {
      state: "success",
      description: "routine change; outside review is advisory",
    };
  }

  const allowedReviewers = new Set(
    [...REVIEWER_FAMILIES]
      .filter(([, family]) => !agentAuthors.has(family))
      .map(([login]) => login),
  );
  if (allowedReviewers.size === 0) {
    return {
      state: "pending",
      description: "no independent hosted reviewer remains for these authors",
    };
  }

  const latestByReviewer = new Map();
  for (const review of reviews) {
    if (
      review.commit_id === headSha &&
      allowedReviewers.has(review.user?.login)
    ) {
      latestByReviewer.set(review.user.login, review);
    }
  }
  const completed = [...latestByReviewer.values()].find((review) =>
    COMPLETED_REVIEW_STATES.has((review.state || "").toUpperCase()),
  );
  if (!completed) {
    return {
      state: "pending",
      description: "awaiting an independent review of the current head",
    };
  }

  return {
    state: "success",
    description: `${completed.user.login} reviewed the current head`,
    review: completed,
  };
}

async function run({ github, context, core, pullRequest }) {
  const pull = pullRequest || context.payload.pull_request;
  if (!pull) {
    throw new Error("independent-review gate requires a pull request event");
  }

  const reviews = await github.paginate(github.rest.pulls.listReviews, {
    owner: context.repo.owner,
    repo: context.repo.repo,
    pull_number: pull.number,
    per_page: 100,
  });
  const result = evaluateGate(pull.body, pull.head.sha, reviews);
  await github.rest.repos.createCommitStatus({
    owner: context.repo.owner,
    repo: context.repo.repo,
    sha: pull.head.sha,
    state: result.state,
    context: "independent-review",
    description: result.description,
    target_url: pull.html_url,
  });
  core.info(`${result.state}: ${result.description}`);
}

module.exports = run;
module.exports.visibleMarkdown = visibleMarkdown;
module.exports.reviewProvenanceSection = reviewProvenanceSection;
module.exports.provenanceField = provenanceField;
module.exports.authorFamilies = authorFamilies;
module.exports.reviewDepth = reviewDepth;
module.exports.evaluateGate = evaluateGate;
module.exports.REVIEWER_FAMILIES = REVIEWER_FAMILIES;
module.exports.REVIEW_DEPTHS = REVIEW_DEPTHS;
module.exports.COMPLETED_REVIEW_STATES = COMPLETED_REVIEW_STATES;
