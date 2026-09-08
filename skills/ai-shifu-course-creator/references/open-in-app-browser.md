# Open in App Browser

Open the supplied URL in the host application's built-in browser, in a visible tab or panel that the user can directly click, type into, and continue using. The calling workflow owns the URL, when to open it, and any task-specific explanation or next steps.

## Required References

None.

## Open the URL

1. Use the URL supplied by the user or calling workflow unchanged, including its query string and fragment. If no URL is available, obtain it from that workflow or ask for it.
2. If the user asked not to open pages or browsers, skip the browser call and provide the clickable Markdown link.
3. Inspect the current host's built-in browser tabs when available. If a tab already has the exact supplied URL, including its query string and fragment, reuse and focus that tab without reloading it. Otherwise, open the URL in a **new visible tab**. Never navigate an existing tab to a different URL: it may contain the user's unfinished work. A matching title, domain, or course is not a URL match.
4. Interpret the result using the table below. Always include the same URL as a clickable Markdown link in the reply, even when a browser panel or tool result is already visible. Let the calling workflow supply the link label and task-specific explanation.

Use the current tool schema to select an existing matching tab or explicitly create a new one, and keep it open for the user. If tab inspection is unavailable, use explicit new-tab creation. If no available capability can preserve existing tabs, keep the link available for manual opening instead. Do not substitute a web fetch, hidden or headless browser, external browser, or system `open` command.

## Host Browser Guidance

Use only tools exposed by the current host; UI labels below are destinations, not tool names to invent.

| Host | Opening guidance |
| --- | --- |
| Codex | With CUA, follow its initialization instructions and inspect the in-app tabs using `cua.getState()` or `cua.listTabs`. Reuse an exact URL match; otherwise call `cua.createBrowserTab("iab", url, { visible: true })` with the supplied URL. Use `open_in_codex` only to show a verified matching tab by its `target.tabId`, or when its current documented behavior guarantees new-tab creation. Passing only `target.url` is not by itself a new-tab guarantee. |
| Claude Code Desktop | Open the URL in the **Code → Browser** pane using an available host capability. For manual opening, click the reply link and choose **Open in app**. |
| WorkBuddy | Open the URL in **概览 → 浏览器** in the right-side results area using an available host capability. |
| 豆包工作 / Doubao Work | Open the URL in **豆包浏览器** on desktop; on the web, use a live remote browser the user can view and take over. |
| Other hosts | Use an available built-in browser capability only if it exposes a visible, interactive page to the user. |

## Opening Result

| Result | Action |
| --- | --- |
| Confirmed opened | Report that the page opened. This does not prove that the page loaded successfully or that the underlying task completed. |
| Queued, such as `status=queued` | Say that opening is pending, keep the link, and do not retry or claim the page already opened. |
| Unavailable, failed, or unconfirmed | Briefly explain that opening is unavailable, failed, or could not be confirmed, and keep the link available for manual opening. Do not automatically retry with another browser. |
| Skipped at the user's request | Provide the link without claiming the page opened or treating the opt-out as an error. |

A browser failure does not undo completed work or justify repeating the operation that produced the URL. Return control to the calling workflow so it can continue its own next step.
