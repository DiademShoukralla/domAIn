# domAIn

domAIn is a multi-agent decision system built with LangGraph. Several persona-based agents (UX/end-user, dev experience, business/product) query a shared indexed knowledge layer and collaboratively review proposals and PRs, writing their reasoning back as decisions.

The knowledge layer stores the codebase, business documentation, and Architecture Decision Records (ADRs) as docs-as-code in this repository. Roadmap context is read from Linear. The council writes updates to business docs and ADRs by opening pull requests — never directly — so merged content is always human-reviewed source of truth.
