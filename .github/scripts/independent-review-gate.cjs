const REVIEWER_FAMILIES = new Map([
  ["copilot-pull-request-reviewer[bot]", "Copilot"],
  ["chatgpt-codex-connector[bot]", "Codex"],
]);

const AUTHOR_FAMILIES = ["Claude", "Codex", "Copilot", "Human"];
const ROUTINE_LABEL = "review:routine";
const COMPLETED_REVIEW_STATES = new Set([
  "APPROVED",
  "CHANGES_REQUESTED",
  "COMMENTED",
]);

function authorFamilies(body) {
  const withoutComments = (body || "").replace(/<!--[\s\S]*?-->/g, "");
  const match = withoutComments.match(/^\s*-?\s*Authoring agent\(s\):\s*(.+)$/im);
  if (!match) {
    return new Set();
  }
  return new Set(
    AUTHOR_FAMILIES.filter((family) =>
      new RegExp(`\\b${family}\\b`, "i").test(match[1]),
    ),
  );
}

function hasRoutineLabel(labels) {
  return (labels || []).some((label) => {
    const name = typeof label === "string" ? label : label?.name;
    return name?.toLowerCase() === ROUTINE_LABEL;
  });
}

function evaluateGate(body, headSha, reviews, labels = []) {
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

  if (hasRoutineLabel(labels)) {
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
  const result = evaluateGate(pull.body, pull.head.sha, reviews, pull.labels);
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
module.exports.authorFamilies = authorFamilies;
module.exports.hasRoutineLabel = hasRoutineLabel;
module.exports.evaluateGate = evaluateGate;
module.exports.REVIEWER_FAMILIES = REVIEWER_FAMILIES;
module.exports.ROUTINE_LABEL = ROUTINE_LABEL;
module.exports.COMPLETED_REVIEW_STATES = COMPLETED_REVIEW_STATES;
