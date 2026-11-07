# HotpotQA support-order: supplemental response adjudication

## Scope and rubric

This is a manual, offline review of the 15 unique questions in the incomplete
support-order pilot (30 responses, paired conditions). It supplements rather
than replaces the historical exact-match, title-F1, and joint-exact scores in
[`hotpotqa-support-order-partial.md`](hotpotqa-support-order-partial.md). Each
response was compared with its question, reference answer, supplied candidate
passages, and supporting facts. No outside retrieval was used.

Answer labels: **correct** means the response answers the requested proposition
and is semantically consistent with the reference; **partial** means it gives a
relevant entity but omits a required distinction/value; **incorrect** means it
conflicts with the reference or answers the wrong type of question; **ungradable**
means the answer could not be reliably recovered. Evidence labels assess whether
the model-selected supplied passages support the answer, not whether the title
set matches the dataset annotation: **sufficient**, **partial**, **insufficient**,
or **ungradable**. The error notes are interpretations, not additional automated
scores.

This is a single-reviewer adjudication, not blinded or independently replicated.
The pilot questions were already inspected during this audit, so this review is
exploratory and must not be used to tune a confirmatory evaluation. Ambiguous
items are explicitly marked; no aggregate accuracy estimate or ordering effect
is inferred.

## Case-level review

| Batch / case ID | Reference | Support first: answer / evidence | Support last: answer / evidence | Adjudication notes |
|---|---|---|---|---|
| b00 `5a8b20335542996c9b8d5fb3` | Shortest NBA player ever | Partial / partial | Partial / partial | Both identify Muggsy Bogues but omit the requested distinction. First cites only the player page; last cites both gold titles but adds an unrelated 19-rebound claim not supported by the selected passages. |
| b00 `5a85fc995542996432c5715f` | Joseph Leo Mankiewicz | Correct / partial | Correct / partial | “Joseph L. Mankiewicz” is a semantic match; first is terse, last states the comparison. The supplied Tony Kaye passage does not report his award count, so the comparison is not fully established by selected evidence. Exact match penalizes the valid name variant. |
| b00 `5ade99235542997c77adee7f` | Midland, Michigan, United States | Incorrect / insufficient | Incorrect / insufficient | Both answer Indianapolis, apparently confusing subsidiary Dow AgroSciences with parent Dow Chemical. Neither cites the supplied Dow Chemical passage that gives Midland. |
| b00 `5ab296a6554299194fa93415` | Chess | Correct / insufficient | Correct / partial | Both choose chess. The support-first response cites only Cartagena, not the passage saying chess is played worldwide; support-last cites Chess. “More popular” is not quantitatively operationalized, so the latter passage gives suggestive scale but not a direct comparative measurement. |
| b00 `5ac1b1345542994ab5c67dd0` | 1736 | Incorrect / partial | Incorrect / partial | Both avoid the requested year. Support-first describes the person as Field Marshal; support-last paraphrases that the rank was highest during his tenure. The cited rank passage contains the year, but neither output states it. |
| b01 `5ae3d0bb5542990afbd1e1e5` | Yes | Correct / partial | Correct / partial | Both correctly say yes, but cite `Dee Dee Ramone and the Chinese Dragons` rather than the supplied `Dee Dee Ramone` page. That band page says the group was fronted by him and identifies him as guitarist/vocalist, but does not establish songwriter; title-F1 misses a semantically related page, while the selected page only partially supports the full claim. |
| b01 `5ac401bb55429919431738f4` | Ub Iwerks | Incorrect / insufficient | Incorrect / insufficient | Both answer Leslie Iwerks, confusing the granddaughter/filmmaker with Ub Iwerks. Support-first selects passages that explicitly attribute Mickey’s origins and Oswald’s creation to Les Clark/Ub Iwerks, contradicting its answer; support-last selects Leslie Iwerks, whose passage says she is Ub’s granddaughter. |
| b01 `5a80caac554299260e20a161` | No | Incorrect / ungradable | Incorrect / ungradable | Both raw content strings assert “Yes,” which conflicts with the reference. The support-last response is malformed JSON: its `supporting_titles` value is not a valid list, so the citation field is ungradable; the answer text itself remains readable. Support-first cites Prince and Patty Jenkins, but the selected Patty passage only identifies her as a director/screenwriter, not as a Hall of Fame inductee. |
| b01 `5ab6993f554299110f219a2b` | Sierra Nevada mountains | Correct / sufficient | Correct / sufficient | Both give the accepted geographic name and cite Granada, whose supplied passage explicitly locates the city at the foot of Sierra Nevada. The scorer’s gold-title recall penalizes omission of the Felipe Alcaraz page, although the cited Granada passage directly supports the mountains answer. |
| b01 `5a8da97c554299068b959d84` | Western Institute of Technology | Incorrect / insufficient | Incorrect / insufficient | Both say Fairleigh Dickinson University while citing WIT. The supplied WIT passage places it in Iloilo City, Philippines; the cited evidence does not support FDU’s answer or establish a comparative campus count. |
| b02 `5a8e3ea95542995a26add48d` | Greenwich Village, New York City | Correct / sufficient | Incorrect / insufficient | Support-first gives the city/neighborhood and cites Adriana Trigiani, whose passage says she is based in Greenwich Village. Support-last gives the director’s name instead of the requested location and cites the film page, which does not establish her residence. |
| b02 `5a81d54a55429903bc27b9d4` | No | Incorrect / partial | Correct / partial | First says both musicians were in The Click Five; second correctly distinguishes Jeff Martin (The Tea Party) from Kyle Patrick (The Click Five). Both cite only The Click Five page, which supports Kyle’s membership but does not establish Jeff’s non-membership; the latter answer is right, but its evidence is incomplete under the closed-passage task. |
| b02 `5adf8c375542995534e8c7dd` | 1972 | Incorrect / insufficient | Incorrect / insufficient | Both answer 1965, confusing the World Series year with Sandy Koufax’s Hall of Fame election year, and cite only the World Series page rather than the supplied Koufax page. |
| b02 `5ab6087a554299110f2199be` | Yes | Correct / ambiguous | Correct / ambiguous | Both match the reference and cite both case pages. The wording “regard the rights of U.S. citizens” is broad: the Korematsu passage concerns Japanese Americans regardless of citizenship, while Chaplinsky concerns First Amendment speech. Treat this as reference-consistent but semantically ambiguous, not a confidently established factual success or hallucination. |
| b02 `5adbf44355429944faac23ce` | Honolulu | Incorrect / insufficient | Incorrect / insufficient | Both answer Hawaii, a state rather than the requested county. The correct supplied passage identifies the City and County of Honolulu, but neither response selects it. Support-first also includes a literal `## ` prefix in its title string; this is a title-format artifact separate from the answer error. |

## What this review changes—and does not change

The review demonstrates several distinct reasons exact metrics can mislead in
this small pilot: semantically equivalent answers can fail string EM; a correct
answer can receive poor title scores when a related passage title differs from
the gold title; and a gold-title match does not guarantee that the selected
passages support the answer. Conversely, incorrect answers can select gold
titles. The malformed b01 response is a parse failure (server finish reason
`stop`), not a server-reported truncation; its readable answer text can be
reviewed separately from its invalid citation structure.

These case judgments do not retroactively change any historical score, establish
causality for passage order, or estimate general HotpotQA performance. Before
using a semantic/evidence rubric confirmatorily, freeze its definitions, have
independent reviewers annotate a separate held-out set, measure agreement, and
resolve disagreements without tuning on these 15 inspected cases.
