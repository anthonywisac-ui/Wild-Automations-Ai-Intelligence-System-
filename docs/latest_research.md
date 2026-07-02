Production-Grade Notes: Dify, OmniRoute, Perplexica, Playwright, Supabase, WhatsApp API
Latest production-grade signals are: Dify is seeing active breakage around upgrades and workflow/runtime behavior, Perplexica has open issues around search/provider compatibility and settings drift, OmniRoute’s setup docs are current but still evolving, Playwright scraping at scale needs browser/resource discipline, Supabase’s public issues show ongoing operational/account-access concerns, and WhatsApp API limits are still governed by throughput, quality, and media/interactive-message constraints.

Dify deployment
Dify’s issue tracker shows a large volume of current open items, including deployment-adjacent failures such as frontend errors after deployment, API crashes on refresh, workflow/log loading problems, document ingestion waiting states, and a compatibility-breaking knowledge issue in versions prior to 1.9.1 becoming unusable after upgrading to 1.9.2. A concrete breaking-change example is the iteration node output change in Dify 1.9.1, where output moved from a flat array of objects to an array of arrays of objects. Another upgrade hazard is the Dify v1.4.1 and plugin daemon v0.1.3 incompatibility, where both sides changed response structures and could not be upgraded independently without breaking the system. For production, the practical lesson is to pin Dify and plugin-daemon versions together, test knowledge base reindexing after upgrades, and stage workflow-heavy deployments before rolling out broadly.

OmniRoute setup
OmniRoute’s setup and user guides are current and emphasize provider configuration, combos, CLI tool integration, and deployment flows. The docs suggest the project is actively maintained and that the setup path is not just a quick-start but a configurable routing layer with pricing-aware provider selection and deployment guidance. I did not find a prominent breaking-change issue in the available results, so the main production concern is keeping provider configs and routing combos aligned with the latest docs. For real-world usage, this usually means validating provider fallbacks, retries, and cost/latency behavior in a staging environment before putting OmniRoute in front of live traffic.

Perplexica integration
Perplexica’s issue tracker is active, with open reports around streamed response auto-scroll, settings changes not sticking, “latest version” regressions, citations hallucination, and backend/provider compatibility problems. A notable integration breakage is the vLLM endpoint issue where Perplexica throws TypeError: Cannot read properties of undefined (reading 'message') during search operations, pointing to response-shape assumptions in the LangChain/OpenAI path. This is a practical warning for anyone integrating Perplexica with custom OpenAI-compatible backends: provider responses need to be tested against the exact parsing logic and streaming expectations. In production, keep a fallback provider, verify citation quality, and test upgrades against your model backend before changing versions.

Playwright scraping at scale
For large-scale scraping, the most useful production advice is to manage browser count carefully, reuse contexts where possible, parallelize with backpressure, and minimize unnecessary asset loading. The current scraping guides also emphasize anti-bot measures, CAPTCHA handling, infinite-scroll logic, proxies, and stealth techniques as part of real-scale operation. The key performance tradeoff is that Playwright is powerful but expensive per page, so failures usually come from excessive concurrency, poor session reuse, or loading full media when only text is needed. In practice, the stable pattern is queue-based crawling with strict concurrency caps and per-domain rate controls.

Supabase best practices
The public Supabase issue tracker shows ongoing operational issues, including payment-method problems, GitHub OAuth reconnection access loss, and reported correctness issues in best-practices references. That means production teams should not treat “best practices” as static; they should verify database, auth, and billing workflows against the current platform behavior and their own recovery procedures. The most production-relevant takeaway from the visible issues is to harden account recovery, auth-provider fallback, and support for admin access continuity. Since the issue tracker is active, schema migrations, auth flows, and project access controls deserve routine validation in staging and disaster-recovery drills.

WhatsApp limits
The clearest current limits surfaced in the available sources are around throughput, quality rating, pricing/billing behavior, opt-in compliance, verification, and message-type restrictions. The 2026 technical overview describes throughput ceilings such as 80 MPS, 30 MPS, and 1,000 MPS depending on account tier and architecture, while quality rating can throttle capacity. Media support is also constrained: stickers, specific audio/image/video formats, and file-size limits vary, and some connector implementations disable emoji or outbound sticker support altogether. For real-world systems, this means you should design for rate limiting, backoff, template compliance, and message-type fallbacks rather than assuming unlimited chat throughput.

Production checklist
Pin versions for Dify and plugin-related components, and validate upgrade paths in staging first.

For Perplexica, test every model provider you use, especially OpenAI-compatible backends like vLLM.

For Playwright, keep concurrency low enough to avoid browser exhaustion and bot-detection spikes.

For Supabase, rehearse auth recovery and project access continuity, not just schema changes.

For WhatsApp, build around rate limits, quality throttling, and media restrictions.