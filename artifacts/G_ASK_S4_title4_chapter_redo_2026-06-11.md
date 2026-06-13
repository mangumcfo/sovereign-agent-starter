# Re-pass ask to G (x.com) — S4 keywords need X.com trend grounding (+ Title 4 chapter fix)

Two issues with the first S4 pass:

1. **(KM) IP-jargon, not searchable terms.** Many keywords are our *internal* vocabulary — "B32 token
   obligations", "cylinder token ledger", "K1 token issuance", "breath-gated", "Stillpoint Synod",
   "Atrium token ledger", "Harness token advantages", "LGP token", "receipted …". Those don't exist as
   searches on X.com or Amazon → zero discovery value. The pass needs to be re-grounded in **trending /
   viral keywords actually searched on X.com**.
2. **(Tiger) Title 4 chapter duplication.** In *"Legal Hardening, Forkability & Generational Token
   Systems"*, chapter clusters 1,3,4,5,6,7,8 were pasted from Title 1 (Substrate) by mistake.

## ⬇️ THE PROMPT — copy/paste to G

> **G — S4 keyword re-pass, this time grounded in X.com trends.** Thank you for the first cut — the
> *structure* is right, but most keywords are our internal jargon (B32, cylinder, K1, breath-gate,
> Stillpoint Synod, LGP, Atrium, Harness, "receipted", "sovereign token substrate"). Those have **no search
> volume** — nobody types them. Please redo the S4 keywords by **analyzing trending/viral keywords on
> X.com** (and the real Amazon/Google token-economy market) so every phrase is something buyers actually
> search in 2026.
>
> **First, recommend the market.** Before committing keywords, analyze X.com trends and tell me, **per
> title, which keyword market is the best fit** — e.g. crypto/Web3 mainstream (RWA tokenization, DAO
> treasury, tokenomics, stablecoin) vs the governance/RWA niche (private tokenization, permissioned ledger,
> family-office digital assets, on-chain compliance) — with a one-line rationale + the trend signal you saw.
> Then give the keywords for the market you recommend. (If a title splits between markets, say so.)
>
> Rules:
> - **No internal/coined terms.** Map each of our concepts to the mainstream phrase the market searches —
>   e.g. "B32 token obligations" → "tokenized asset ledger" / "RWA tokenization"; "breath-gated minting" →
>   "permissioned token issuance" / "human-in-the-loop crypto"; "Atrium dashboard" → "crypto portfolio
>   dashboard". Use what X.com actually trends, not our names for things.
> - Keep the **4 titles + chapter counts** (8/8/8/9) as given.
> - **7 KDP keywords + 3–5 searchable phrases per chapter**, each a real search term.
> - **Title 4 ("Legal Hardening, Forkability & Generational Token Systems")** — regenerate all 9 chapter
>   clusters from scratch on *its* subject (legal structuring, forkability, jurisdiction, inheritance/exit,
>   generational continuity) — the first pass duplicated Title 1 there.
>
> Return YAML: per title `market: <recommended>`, `market_rationale: <one line + trend signal>`,
> `keywords: [7]`, `chapters: [{n, keywords[]}]`.

## On return
G's trend-grounded YAML replaces the provisional capture in `G_S4_keywords_2026-06-11.yaml` → GB folds the
clean S4 set into `series_roadmap.yaml` → KM ratifies. **Holding the GB fold until then** — we don't fold
IP-jargon keywords that won't be found.
