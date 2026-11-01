# Clarity gate

Fill in every line. A line counts as filled only if it comes from the user's words, the repo, or a source you checked (Neuronet, Jira, docs). Anything you inferred but didn't confirm counts as **blank**. Every blank becomes a question.

| # | Item | Filled from |
|---|------|-------------|
| 1 | **Goal**, in one sentence the user would agree with | |
| 2 | **Definition of done**: 2–6 checkable acceptance criteria | |
| 3 | **In scope / out of scope**: what must not change | |
| 4 | **Where**: repos, folders, files, systems touched (with paths) | |
| 5 | **Verification**: the exact commands, tests or manual checks that prove each criterion | |
| 6 | **Constraints**: deadline, total budget cap, style/conventions, dependencies that can't be added | |
| 7 | **Inputs**: tickets, specs, designs, prior decisions (links) | |
| 8 | **Outward actions wanted at the end**: commit? branch name? PR target? message to whom? | |
| 9 | **Risk**: anything irreversible, shared, or customer-facing | |
| 10 | **Unknowns the user may not know either**: list them, and agree how to resolve each (a spike task, or ask someone) | |

## Question bank (pick what applies, and make options concrete)
- "When this is done, what will you check first to know it worked?" This settles items 2 and 5.
- "Which of these files/modules is off-limits?" This settles item 3. Offer the candidates you found.
- "Should this match an existing pattern? I found X in `path` and Y in `path`." This settles item 6.
- "At the end, do you want a commit, a PR (to which base?), or just local changes to review?" This settles item 8.
- "Is there a total spend you don't want this run to exceed?" This settles item 6. The default is the sum of the task caps.
- "Is there a ticket or doc that defines this? If it disagrees with what you said, which wins?" This settles item 7.

## Stop conditions
- Never send more than 4 questions at once. Ask the questions whose answers change *what gets built* first.
- If the user says "use your judgment" on an item, write down your choice and show it in the restated goal so they can veto it.
- The gate passes only when items 1–5 and 8 are all filled and the user has said yes to the restated goal.
