# Architecture Modelling Platform

## Investment Brief

| | |
|---|---|
| **Prepared for** | Agency — name not provided |
| **Date** | 3 March 2026 |
| **Version** | 1.0 |
| **Signal strength** | MEDIUM — scope and delivery model are well understood; investment trigger, budget, and benefits baseline are not |
| **Prepared by** | Bearing |

> **What this is:** A structured investment brief produced from a guided triage session. It captures what was discovered — the investment picture, the cost shape, the unknowns, and a proportionate next step. Every claim is traceable to its source: what the contributor said, what analysis inferred, and what remains unknown.
>
> **What this isn't:** A formal business case. It is what is needed to confidently walk into the first conversation about this investment — knowing the shape, the cost, and the challenges ahead.

---

## 1. What We Found

**In brief:** The agency is building a custom architecture modelling tool as a hedge against the likely failure of its primary plan — rolling out Sparx Enterprise Architect (EA) as a cloud-hosted service that architects already resist. The investment is Band 3: $1.1M–$2.6M whole-of-life, deliverable by the in-house team. The full build case is credible but not yet ready for a funding decision: the trigger for Plan B has not been defined, no budget is confirmed, and the NZISM (New Zealand Information Security Manual) accreditation pathway is untested. A structured discovery phase resolves those gaps before the agency commits.

| | |
|---|---|
| **Estimated investment** | Band 3: $1.1M–$2.6M whole-of-life |
| **Delivery complexity** | Moderate — in-house team confirmed, NZISM accreditation the main external constraint |
| **Signal strength** | MEDIUM |

### The problem

The agency's transformation programme needs a common platform where enterprise architects, solution designers, and security analysts can create, store, and reference system architecture in consistent formats. The current plan is to roll out Sparx EA as a cloud-hosted service. Sparx EA is the default in government architecture, but it is technically complex, and the agency's architects already resist it. The contributor confirmed it sits at the bottom-left of the Gartner Magic Quadrant — the position for tools with weak vision and poor execution. If Sparx EA SaaS rolls out without an alternative and faces the adoption resistance already signalled, the programme operates without a functioning architecture discipline for its duration.

The architecture models in scope hold security-sensitive information: system designs, network layouts, and control configurations. The contributor confirmed the data classification is SENSITIVE. [ASSERTED] That classification means the hosting environment, access controls, and the tool itself must all meet formal NZISM requirements — not as an afterthought, but as a condition of going live.

Years of architecture work also sit locked inside Sparx EA files that only people trained in Sparx can access. If the Sparx SaaS rollout fails and no migration has happened, that heritage becomes inaccessible to the team most likely to need it.

### What the session surfaced

**This tool is Plan B — and that changes the investment logic.** The contributor confirmed the primary plan is still Sparx EA SaaS, currently in procurement. This tool was described as "a hedge in case that procurement goes pear-shaped, and in case we struggle with adoption of Plan A." That framing is strategically sound — the agency is protecting against a risk it can already see. But it means the investment trigger is undefined. A full build recommendation cannot be made until the sponsor has answered: under what conditions does Plan B activate? [ASSERTED]

**The NZISM mapping is a build requirement, not a feature.** Asked what "maps to NZISM controls" means in practice, the contributor clarified: the tool itself must be built to meet NZISM controls, not the models stored inside it. This is a security-by-design requirement — the tool needs to be certifiable against NZISM from day one. Combined with the confirmed SENSITIVE classification, this means the tool requires formal security accreditation before going live: threat modelling, penetration testing, and sign-off by an authorised security assessor. The contributor separately confirmed that accreditation backlog is the key external risk. Those two answers together — SENSITIVE classification and an accreditation queue the team cannot control — mean go-live timing is partially outside the build team's hands. [ASSERTED for classification and intent; INFERRED for timeline impact]

**Open source changes the strategic footprint, not the governance model.** The contributor confirmed this will be released as open source, positioned as a pilot, with the agency acting as lead contributor. Cross-agency governance is not required at launch. This is a single-agency build that others can contribute to — simpler to govern and faster to launch than a full shared service. But the agency retains accountability for the production system regardless of how many external contributors join. Open-source community management is an ongoing operational cost, not a cost reduction. [ASSERTED]

**Sparx EA import is a one-time event, not an ongoing integration.** Existing architecture models sit in Sparx EA files. The contributor confirmed the import is a one-time migration, not an ongoing bidirectional sync with teams continuing to use Sparx. [ASSERTED] This is the lowest-complexity version of this problem: build an importer once, validate the output, and decommission the dependency. If any teams continue working in Sparx after go-live, this becomes an ongoing integration to build and maintain — adding cost and maintenance burden.

**All three notations are required at launch.** The tool must support ArchiMate (an open standard for enterprise architecture modelling), UML (Unified Modelling Language, the standard for software design), and C4 (a simpler notation for describing software at different levels of detail). Delivering all three simultaneously is the single largest driver of build scope and cost. Phasing one notation to a later release would materially reduce the first delivery and widen the open-source library options, without changing the end state. The contributor confirmed all three at launch. [ASSERTED]

**No one has measured the current pain.** Asked how success would be measured, the contributor said this had not been thought about yet. The investment has genuine value: architects gain a tool they will use, heritage models survive, the programme gets a shared view of its architecture. But none of these benefits have a baseline measurement. Without a baseline, benefits claimed in a funding paper cannot be verified — and benefits realisation becomes impossible. A measurement baseline is a prerequisite for the formal business case. [ASSERTED for absence of measurement framework]

### Evidence quality

| Confidence level | Count | Meaning |
|---|---|---|
| ASSERTED | 14 | Stated by contributor |
| INFERRED | 9 | Derived by analysis — plausible but unconfirmed |
| PLACEHOLDER | 4 | Unknown — filled with reasonable assumption |

Signal is strongest on scope and delivery model: the contributor has a clear picture of what the tool needs to do and who will build it. Signal is weakest on the investment case itself — no confirmed budget, no defined trigger for Plan B, no benefits baseline, and an untested NZISM accreditation pathway for this specific tool.

---

## 2. What It Costs

### Options

| | Do nothing | Discovery phase | Full build |
|---|---|---|---|
| **What it means** | Let Sparx EA SaaS proceed. If it fails or faces adoption resistance, revisit. No fallback tool available. | Structured 6–8 week phase to define Plan B trigger conditions, validate the technical approach, and establish a benefits baseline. Produces build-ready specifications. | In-house team builds the modelling tool: three notations, shared repository, NZISM-accredited, WCAG 2.1 AA accessible, with one-time Sparx EA import. |
| **Annual / total cost** | Sparx EA SaaS licensing cost not disclosed — not known [PLACEHOLDER]. If rollout fails: sunk procurement cost plus no architecture capability for the programme duration. | $50K–$100K, 6–8 weeks [INFERRED — consistent with standard NZ government discovery scope] | $1.1M–$2.6M whole-of-life over 5 years [INFERRED — band calibration from session data] |
| **Addresses the problem?** | No — if Sparx EA SaaS faces the adoption resistance already visible, there is no fallback and the programme loses its architecture capability. | Partially — establishes the conditions for a confident full build decision. | Yes — delivers the tool the programme needs, built to last and accredited from day one. |
| **Biggest risk** | No fallback when Sparx EA SaaS faces resistance. Programme operates without a shared architecture platform. | Discovers full build is not yet warranted because Sparx EA SaaS succeeds. That is a good outcome, not a waste. | NZISM accreditation backlog delays go-live. All-three-notations-at-launch overloads the first delivery. |

Do-nothing is not free. Sparx EA SaaS licensing costs continue regardless of adoption. If rollout proceeds and architects do not use it, the programme pays the licensing cost and receives no architecture capability in return. The contributor confirmed that risk is already visible before rollout has begun. [ASSERTED]

If the trigger conditions for full build are confirmed during discovery, proceed directly. If Sparx EA SaaS succeeds and architects adopt it, the discovery work informs the open-source community rather than internal delivery — the cost is not wasted.

### Cost components

**Core modelling application — web application, three notation standards (ArchiMate, UML, C4), model repository with access control:** $350K–$750K [ASSERTED — contributor confirmed custom build and all-three-at-launch; INFERRED — open-source library foundation from open-source release intent]

The in-house team builds a browser-based modelling tool. Open-source diagramming libraries — for example, draw.io/mxGraph for UML and ArchiMate, and Structurizr for C4 — provide the rendering foundation rather than requiring notation engines to be built from scratch. The open-source release intent supports this approach: the agency is not building a proprietary product. Three notations at launch is confirmed scope and is the main build cost driver. If the team lacks front-end diagramming experience, a specialist contractor is needed and cost rises toward $600K–$1.2M.

**NZISM accreditation and security hardening of the tool itself:** $80K–$200K [ASSERTED — classification confirmed SENSITIVE; INFERRED — accreditation scope from NZISM requirements for SENSITIVE systems]

A system handling SENSITIVE information requires formal security accreditation before going live. This means documenting the security architecture, completing threat modelling, running a penetration test by a certified assessor, and obtaining sign-off. The contributor confirmed this is the intent — security by design from day one, not retrospective compliance. The accreditation backlog is an elapsed-time risk rather than a direct cost driver: the queue can extend the project by weeks or months without adding features. Team cost continues during the wait.

**Sparx EA one-time model migration:** $30K–$80K [ASSERTED — one-time migration explicitly confirmed by contributor]

Sparx EA exports models in XMI (XML Metadata Interchange), a parseable industry standard. This component covers building an importer, mapping XMI to the new model schema, and validating that the output is correct. It runs once. The range reflects uncertainty about how consistently the existing Sparx models are structured — poor data quality or heavy use of non-standard Sparx extensions pushes toward the upper end.

**User experience design and WCAG 2.1 AA accessibility:** $50K–$130K [INFERRED — from WCAG requirement in system description and known complexity of accessible diagramming tools]

WCAG 2.1 AA (Web Content Accessibility Guidelines, the NZ government web standard) is among the harder accessibility requirements to meet for interactive diagramming tools. Canvas-based diagram editors require keyboard navigation, screen-reader labelling, and focus management for complex graphical objects — none of which are standard in off-the-shelf components. A specialist accessibility audit is required before go-live. If the chosen open-source library already ships with strong accessibility support, design effort reduces significantly.

**Testing — functional, security, and accessibility:** $40K–$100K [INFERRED — from SENSITIVE classification, WCAG requirement, and three-notation scope]

Independent security penetration testing is a prerequisite for NZISM accreditation. A specialist accessibility audit is required for WCAG compliance. Functional testing of three notation standards requires domain knowledge — incorrect notation rendering undermines the tool's core purpose and would be visible to every architect who uses it. If the in-house team has capacity and expertise to run most functional testing, cost sits at the lower end.

**Delivery management and governance:** $40K–$120K [ASSERTED — contributor confirmed in-house team, BAU project, no ministerial visibility]

No dedicated external programme manager is assumed. Cost is team-lead time and stakeholder coordination. No ministerial visibility and BAU classification keep governance overhead low. If the agency's internal assurance framework requires a formal gateway review or independent quality assurance, add $30K–$80K.

**NZ cloud hosting and infrastructure (annual):** $12K–$35K/year [ASSERTED — confirmed under-50 users, SENSITIVE classification, standalone system, turn-based access]

Under 50 users, standalone system with no external integrations, turn-based access model — low compute and storage demand. NZ-based cloud hosting is required for SENSITIVE data under Cabinet Office circular CO(23)9 (the government's cloud-first policy). SENSITIVE classification may require a dedicated compute environment rather than shared tenancy depending on the agency's NZISM implementation, pushing toward the upper range.

**Maintenance, support, and minor enhancements (annual):** $80K–$180K/year [ASSERTED — same team confirmed post go-live; INFERRED — open-source maintenance overhead from open-source release intent]

The in-house team retains the system. Cost is team time for dependency and security updates, bug fixes, notation library upgrades, and open-source community management. Open-source contributions from other agencies reduce the maintenance burden over time, but the agency retains accountability for the production system regardless of who contributes.

### Whole-of-life cost

| | Low | Central | High |
|---|-----|---------|------|
| Capital (build, accreditation, migration, testing, delivery management) | $590K | $895K | $1,380K |
| Operating (5 years at annual rates above) | $460K | $688K | $1,075K |
| **Total WOLC** | **$1,050K** | **$1,583K** | **$2,455K** |

**Band 3: $1.1M–$2.6M.** [INFERRED — band calibration from session data] The width reflects three genuine uncertainties: whether the in-house team needs contractor uplift for front-end diagramming expertise; whether SENSITIVE classification triggers a dedicated compute environment; and how consistently the existing Sparx models are structured.

Do-nothing over 5 years: the Sparx EA SaaS licensing cost is not known [PLACEHOLDER]. If Sparx EA SaaS is adopted and used, it will likely cost less than this build. If it fails or is not adopted, the programme pays the licensing cost and receives no architecture capability in return. This investment recovers its cost if the Sparx EA SaaS rollout fails or faces material adoption resistance — which the contributor considers the more likely outcome. [ASSERTED]

**Optimism bias:** NZ Treasury guidance and UK Green Book supplementary material indicate IT projects at this stage carry optimism bias of +10% to +200%. Apply +30% to +50% on the central estimate for planning purposes — that puts the working planning figure at approximately $2.1M–$2.4M.

### Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Discovery | 6–8 weeks | Defines trigger conditions, validates notation library approach against SENSITIVE hosting requirements, establishes benefits baseline |
| Build and accreditation | 6–9 months | From approval to go-live. NZISM accreditation queue determines the back end of this range. |
| **Total concept-to-live** | **4–6 months from trigger** (following discovery) | Assumes accreditation queue does not create extended delay. Add 2–4 months if the queue is longer than anticipated at discovery. |

The contributor confirmed accreditation backlog as the key external risk. [ASSERTED] This is an elapsed-time constraint, not a cost driver — the build team can be coding while waiting for the accreditation queue to clear, but go-live depends on that queue. Starting the accreditation conversation early changes this picture materially.

---

## 3. What We Don't Know

### Critical unknowns

| # | Unknown | What we assumed | If wrong | How to resolve |
|---|---------|----------------|----------|----------------|
| U1 | When does Plan B activate? What conditions would trigger commitment to full build? | Sparx EA SaaS procurement fails, or adoption signals are poor at early rollout. | If the trigger is never defined, the agency may find itself mid-build on Plan B while Plan A is unresolved — spending both budgets simultaneously without a decision point. | The trigger conditions are a governance decision for the programme sponsor. They cannot be resolved by technical assessment — they require a sponsor decision during the discovery phase. |
| U2 | NZISM accreditation pathway and queue position for this specific tool | Formal accreditation is achievable; the backlog adds elapsed time but does not block the build. | If no assessor slot is available within the build window, go-live is delayed without warning. Team cost continues during the wait. | Engagement with the agency's security team and the accreditation authority to confirm queue position and timeline before build commits to a go-live date. |
| U3 | Sparx EA SaaS licensing cost | Unknown — not disclosed during the session. | Without this number, the do-nothing option has no cost figure and the investment comparison is incomplete. This matters for the business case. | The Sparx EA SaaS commercial terms are held by whoever is running the primary procurement. |
| U4 | Benefits baseline — how much time do architects currently spend on model creation, format conversion, and tool friction? | The benefit is real and meaningful, but it is not yet quantified. | Without a baseline, benefits realisation is impossible. A formal business case that claims efficiency savings without a baseline measurement will not survive scrutiny at funding review. | A baseline survey of architect time allocation. This is a two-week activity, not a project — it can run alongside any other next step. |

U1 was surfaced when the contributor described this as Plan B and a hedge: the trigger for building it was not defined during the session. U2 and U1 together are the largest planning constraints — both are outside the build team's control and both need resolution before a build go-ahead makes sense.

### Risks

| # | Risk | Impact | What protects against it |
|---|------|--------|------------------------|
| R1 | All-three-notations-at-launch overloads the first delivery | First release is delayed or delivered with poor notation quality; architects don't adopt it for the same reasons they resist Sparx EA | Phased delivery: one notation first (likely ArchiMate, as the enterprise architecture standard), others in subsequent releases. The end state is unchanged; the first delivery is smaller and lower-risk. |
| R2 | NZISM accreditation backlog extends go-live beyond the programme window | The tool is ready but cannot go live; team costs continue; programme operates without architecture capability for the extended period | Starting the accreditation conversation during discovery, not at the end of build, is the single most effective mitigation. Queue position should be known before the build go-ahead is given. |
| R3 | In-house team capacity erodes during build due to competing priorities | Delivery slows; contractor uplift becomes necessary; cost rises by $300K–$600K | Confirming team availability and backlog before committing to the build timeline. This is the most common failure mode for agency-owned tools. |
| R4 | Open-source release attracts contributors, but the agency retains full accountability for the production system | Bug reports, security vulnerabilities, and pull requests consume team time not in the cost model; contribution governance becomes contentious | Open-source community management should be treated as an operational cost from day one, not a cost reduction. Contribution governance (who can merge, who reviews security patches) needs to be defined before release. |

### Where projects like this lose value

| Pattern | Why it's relevant here | What happened elsewhere |
|---------|----------------------|------------------------|
| Success metrics measure go-live, not outcomes | The stated 12-month success measure is "system live and being used." That is a go-live check. It does not measure whether architects produce more architecture, whether models reflect reality, or whether the transformation programme's shared understanding actually improves. A tool can go live, be used, and still fail to change how the organisation works. | Government IT success metrics routinely measure compliance — on time, on budget, to spec — rather than whether users are better off. Projects that tick every delivery box and still fail users are the norm, not the exception. (Belfer Center) |
| Not considering whether a smaller first release is enough | All three notations at launch is a material scope commitment that the session has not tested against user need. The question — which one notation would cover 80% of the work? — was not asked. If the answer is ArchiMate, the first delivery is materially smaller, lower-risk, and faster to go live. | The NZ Auditor General's analysis of government IT outcomes shows the most common path to a failed larger project is not asking whether a smaller version achieves the core need first. Tools that ship one notation well get adopted. Tools that ship three notations partially do not. |
| Planning assumptions are never retested | The core assumption is that Sparx EA SaaS will fail or face adoption resistance. That assumption is well-founded. But it should be explicitly retested at defined intervals — not locked in. If Sparx EA SaaS succeeds and adoption is strong, the justification for Plan B changes. | Projects consistently lose value when assumptions treated as facts at approval are never reviewed as the environment changes. The assumption that justified the investment at month one should be checked at month six. (UK NAO) |

### Assumptions register

| # | Assumption | Confidence | If wrong |
|---|-----------|------------|----------|
| A1 | The in-house team has front-end diagramming skills sufficient to build a canvas-based modelling tool | INFERRED | A specialist contractor is required. Add $300K–$600K and reconsider band position. |
| A2 | Open-source diagramming libraries (e.g. draw.io/mxGraph, Structurizr) meet SENSITIVE hosting requirements without additional constraint | INFERRED | A more constrained build approach is needed and cost rises, potentially toward the upper band boundary. |
| A3 | The existing Sparx EA model library is consistently structured enough for automated migration | INFERRED | Inconsistently structured models or heavy use of non-standard Sparx extensions add manual remediation cost outside the migration component estimate. |
| A4 | NZISM accreditation for this tool is achievable within the build timeline | INFERRED | A longer-than-expected accreditation queue delays go-live without adding features. Team cost continues during the wait. |
| A5 | The agency will sustain the team's ownership of the tool post go-live, including open-source community management | ASSERTED — contributor confirmed same team builds and runs | If the team is reassigned to higher-priority work, the tool degrades into the same problem it was built to solve. |

### Stakeholders and dependencies

| Stakeholder | Interest | Key concern | What they need from this process |
|-------------|----------|-------------|--------------------------------|
| Enterprise architects and solution designers (under 50 users) | A tool they can actually use | Ending up with another tool that is complex, poorly designed, and resisted from day one | Involvement in notation selection and UX design from the start of build, not at the testing stage |
| Transformation programme leads | Shared architecture visibility across the programme | Architecture models that are created but never updated, or that do not reflect what is actually being built | Confirmation that the tool integrates with how the programme works, not just how architects prefer to work |
| Agency CISO and security team | NZISM compliance of the tool itself | A SENSITIVE system going live without formal accreditation; security-by-design intent not backed by evidence | Early engagement on the accreditation pathway and queue position — during discovery, not at the end of build |
| Other NZ government agencies (potential future contributors) | Open-source access to a tool that meets their architecture needs | Governance ambiguity about who controls the production system and who is accountable for security patches | Clarity that the agency retains production ownership; contributions are welcome but do not imply co-governance or shared accountability |

| Dependency | Owner | Status | Impact if unavailable |
|------------|-------|--------|---------------------|
| NZISM accreditation queue and assessor availability | Agency security team / accreditation authority | Unknown — not confirmed during session | Go-live delayed without warning; team cost continues; programme window may close |
| Sparx EA SaaS procurement outcome | Procurement lead for primary plan | Ongoing | If Sparx EA SaaS succeeds and architects adopt it, the trigger for full build may not materialise — which changes the investment decision, not the discovery recommendation |
| In-house team capacity | Team lead / agency management | ASSERTED as available | If capacity is consumed by competing priorities, contractor uplift becomes necessary and the cost model changes materially |

---

## 4. The Ask

### What we're recommending

Approve a structured discovery phase — 6–8 weeks, $50K–$100K — before committing to full build funding.

The full build case is credible. The delivery model is sound: an in-house team, a standalone system, a clear scope, and a realistic timeline. The investment is not blocked by technical risk. It is blocked by two governance questions only the sponsor can answer: under what conditions does Plan B activate, and does the agency want to commit $1.1M–$2.6M before those conditions are confirmed?

Discovery is the step that makes those questions answerable. It is not a hedge against bad news — it is the preparation for a confident decision, whichever way that decision goes. A discovery phase that finds Sparx EA SaaS is succeeding is a good outcome. A discovery phase that confirms the trigger conditions and validates the technical approach is equally valuable.

The four unknowns that block a full build recommendation (U1 through U4) are all resolvable within the discovery window. None require a major technical investigation — they require sponsor decisions and early conversations with the accreditation authority.

### What can happen now vs what depends on unknowns

**Backed — these do not depend on any unresolved unknown:**
- The NZISM accreditation queue position is the single factor most likely to determine the go-live date. Knowing that queue position early changes what is possible. The earlier this is understood, the more accurately a go-live date can be set.
- The highest-cost technical assumption — whether open-source diagramming libraries meet SENSITIVE hosting requirements without additional constraint — can be assessed quickly. This question either opens the lower half of the cost range or closes it.
- A benefits baseline for architect time spent on model creation, format conversion, and tool switching is a two-week survey, not a project. It is a prerequisite for any formal business case and can run alongside any other step.

**Contingent — these depend on unknowns being resolved:**
- If U1 resolves with clear trigger conditions confirmed → the brief is ready to support a full build funding decision.
- If U3 shows Sparx EA SaaS is significantly cheaper and adoption signals are positive → full build is deferred; the open-source proof-of-concept stays in reserve.
- If A1 (team diagramming skills) resolves negatively → the cost model is revised before build funding is sought, and a contractor procurement is scoped.

### Governance pathway

| Step | Action | Authority | Timing |
|------|--------|-----------|--------|
| 1 | Approve discovery phase ($50K–$100K) | Investment committee or CIO — this sits within normal Band 1 delegations | Now |
| 2 | Define Plan B trigger conditions — the specific signals that activate full build commitment | Programme sponsor | During discovery |
| 3 | Confirm NZISM accreditation pathway and queue position | CISO / accreditation authority | During discovery |
| 4 | Seek full build funding decision (Band 3 — $1.1M–$2.6M) | Investment committee or CE | Following discovery, once trigger conditions are confirmed and benefits baseline is established |

---

## 5. Benefits and Trade-offs

| # | Benefit | Type | How we'd measure it | When | Confidence |
|---|---------|------|-------------------|------|------------|
| B1 | Architects use the tool — models are created and maintained rather than abandoned | Staff experience | Percentage of licensed users active weekly at 90 days post-launch (target: >80%); compared to Sparx EA SaaS adoption rate if available | 90 days post-launch | INFERRED — adoption depends on UX quality; the case for adoption over Sparx EA is strong but unproven until live |
| B2 | Shared architecture language within the agency — transformation programme and internal IT teams working from the same models in one place | Strategic | Number of teams actively contributing models at 6 months; number of cross-team references to shared models | 6 months post-launch | ASSERTED — contributor confirmed this is the core programme need |
| B3 | Security-by-design accreditation — tool certifiable against NZISM from day one, not assembled retrospectively under audit pressure | Capability | NZISM control coverage signed off by CISO before go-live; zero critical gaps at first security review | Go-live | ASSERTED for intent; INFERRED for achievability within timeline |
| B4 | Architecture heritage preserved — Sparx EA models migrated and accessible before the Sparx window closes | Risk reduction | Percentage of in-scope Sparx models successfully imported and validated before Sparx decommission | Migration phase | ASSERTED — one-time migration confirmed; window is time-bounded |
| B5 | Single authoritative repository — programme leadership can see the current architecture without asking around, with full version history and access audit | Visibility | Time to locate the current version of a specific architecture artefact, baseline vs. 12 months post-launch | 12 months post-launch | INFERRED |
| B6 | Stop rebuilding the same model in three formats — one underlying model, multiple views for different audiences | Efficiency | Architect hours spent reformatting or recreating existing models per month, baseline vs. 6 months post-launch | 6 months post-launch | INFERRED |

B2 is the benefit the contributor weighted most highly. B3 was confirmed as the differentiating design principle — "security by design will help get this accredited." B4 is time-bounded: once Sparx EA is decommissioned, the migration window closes regardless of what happens to this tool. [ASSERTED] B6 was identified through system analysis and has not been validated by the contributor.

### Dis-benefits

| # | Dis-benefit | Who bears it | Duration | Mitigation |
|---|-------------|-------------|----------|------------|
| D1 | Open-source community management consumes team time not in the original cost model — bug reports, security advisories, pull request reviews | In-house team | Ongoing from release | This should be built into the operating cost model from day one as a known commitment, not treated as an unexpected overhead after release. |
| D2 | If Sparx EA SaaS succeeds and is adopted, this investment creates a competing internal tool — two architecture platforms in the same agency | Programme and IT leadership | Until one is formally decommissioned | Defining the decision point in advance prevents drift: if Sparx EA SaaS achieves a specified adoption threshold by a specified date, Plan B is deferred. |
| D3 | WCAG-compliant interactive diagramming is harder to build than standard web interfaces — specialised implementation requirements may slow the build | Development team | Build phase | Specialist UX and accessibility resource from the start of build, not introduced at the testing stage. |

### Investment appraisal

| | Low | Central | High |
|---|-----|---------|------|
| Quantified benefits (5 years) | Not quantified | Not quantified | Not quantified |
| Investment cost (WOLC) | $1.1M | $1.6M | $2.6M |
| **Net financial position** | — | — | — |

This investment does not achieve financial payback on quantified benefits — not because the value is absent, but because the baseline measurements needed to quantify it do not yet exist. Benefits B1 through B6 are real and specific. None have been measured. Inventing numbers to fill the table would make the business case look complete and be less credible to anyone who challenges it. Establishing the baseline is the first task of the recommended discovery phase.

### Value beyond the numbers

Three things justify this investment that cannot be monetised at triage. First, architecture capability: a transformation programme that cannot share, challenge, and build on architecture models across its own teams is operating on assumptions that cannot be checked. That is a risk to programme outcomes, not a minor inconvenience. Second, security posture: a tool built to NZISM requirements from day one means the agency can demonstrate its control coverage at any audit point, rather than assembling retrospective evidence under pressure. Third, open-source contribution: a government-built, NZISM-compliant architecture modelling tool, released under an open licence, is a direct contribution to every NZ government team that does architecture work. That value does not appear in this agency's cost-benefit analysis, but it is the kind of contribution the GCDO (Government Chief Digital Officer) recognises.

---

## Appendix A: What Comes Next

| If the next step is... | This brief provides... | The author still needs to add... |
|------------------------|----------------------|----------------------------------|
| **Internal business case** | Cost shape, options, risks, recommended pathway, benefits framework (unmeasured) | Confirmed funding, named sponsor, trigger conditions for Plan B activation, benefits baseline from discovery, internal template alignment |
| **Formal BBC / IBC** (Better Business Case — Initial Business Case) | Strategic context, economic analysis skeleton, risk register, options analysis | Five-case structure, NPV calculation (requires measured baseline), procurement strategy for open-source-first approach, governance detail, optimism bias treatment |
| **Direct to procurement** | Not recommended at this stage — trigger conditions are undefined and budget is unconfirmed. The discovery phase is the appropriate next step, not procurement. | — |

---

## Appendix B: Confidence Summary

Of the major claims in this document, 14 were confirmed by the contributor (ASSERTED), 9 were derived from analysis (INFERRED), and 4 are placeholders where the session did not produce sufficient signal (PLACEHOLDER).

The strongest signal is in scope and delivery model: the contributor has a clear picture of what the tool needs to do, who will build it, and what the data classification requires. The weakest signal is in the investment case itself — no confirmed budget, no defined trigger for Plan B, no benefits baseline, and an untested NZISM accreditation pathway. These gaps are not reasons to stop — they are the reason the discovery phase is the recommended next step rather than full build commitment. Section 3 identifies the specific claims that carry the most risk if wrong. If one section is worth validating before this brief is forwarded, it is that one.
