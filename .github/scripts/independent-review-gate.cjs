const REVIEWER_FAMILIES = new Map([
  ["copilot-pull-request-reviewer[bot]", "Copilot"],
  ["chatgpt-codex-connector[bot]", "Codex"],
]);

const AUTHOR_FAMILIES = ["Claude", "Codex", "Copilot", "Human"];
const ROUTINE_LABEL = "review:routine";
const STATUS_CONTEXT = "independent-review";
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

async function publishedStatus({ github, context, sha }) {
  const response = await github.rest.repos.getCombinedStatusForRef({
    owner: context.repo.owner,
    repo: context.repo.repo,
    ref: sha,
    per_page: 100,
  });
  return (
    (response.data.statuses || []).find(
      (status) => status.context === STATUS_CONTEXT,
    ) || null
  );
}

async function run({ github, context, core, pullRequest, onlyWhenChanged }) {
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

  if (onlyWhenChanged) {
    const published = await publishedStatus({
      github,
      context,
      sha: pull.head.sha,
    });
    if (
      published &&
      published.state === result.state &&
      published.description === result.description
    ) {
      core.info(`#${pull.number} unchanged: ${result.state}`);
      return result;
    }
  }

  await github.rest.repos.createCommitStatus({
    owner: context.repo.owner,
    repo: context.repo.repo,
    sha: pull.head.sha,
    state: result.state,
    context: STATUS_CONTEXT,
    description: result.description,
    target_url: pull.html_url,
  });
  core.info(`#${pull.number} ${result.state}: ${result.description}`);
  return result;
}

// Hosted reviewers submit reviews as bot actors, whose events do not reliably
// start a workflow run, so a review of an unchanged head would otherwise leave
// the gate pending until someone re-ran it by hand. The sweep re-evaluates
// every open pull request on a schedule and only writes a status when the
// verdict actually moves.
async function sweep({ github, context, core }) {
  const pulls = await github.paginate(github.rest.pulls.list, {
    owner: context.repo.owner,
    repo: context.repo.repo,
    state: "open",
    per_page: 100,
  });

  for (const pull of pulls) {
    try {
      await run({
        github,
        context,
        core,
        pullRequest: pull,
        onlyWhenChanged: true,
      });
    } catch (error) {
      core.warning(`#${pull.number} could not be evaluated: ${error.message}`);
    }
  }

  core.info(`swept ${pulls.length} open pull request(s)`);
  return pulls.length;
}

module.exports = run;
module.exports.sweep = sweep;
module.exports.authorFamilies = authorFamilies;
module.exports.hasRoutineLabel = hasRoutineLabel;
module.exports.evaluateGate = evaluateGate;
module.exports.REVIEWER_FAMILIES = REVIEWER_FAMILIES;
module.exports.ROUTINE_LABEL = ROUTINE_LABEL;
module.exports.STATUS_CONTEXT = STATUS_CONTEXT;
module.exports.COMPLETED_REVIEW_STATES = COMPLETED_REVIEW_STATES;
