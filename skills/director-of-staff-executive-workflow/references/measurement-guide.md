# Measuring cost per accepted result

A model-call price is not the total cost of executive AI work. Measure the complete workflow, including failures.

## Record for each prospective work order

- Task identity and category; acceptance criteria frozen before starting.
- Manual baseline minutes for the same task, with the baseline method documented.
- AI execution and elapsed time, with local hardware, electricity, and service overhead estimated transparently.
- Number of local and paid-model calls; input/output tokens where available.
- Human review minutes, remediation/rework minutes, and exception-handling minutes.
- Whether the reviewer accepted the outcome and why.
- Any prohibited action, hallucination, unsupported claim, or missing dependency.

**Human minutes saved per accepted result** = baseline manual human minutes minus actual human preparation, review, exception, and rework minutes. Report the numerator and denominator, and exclude unaccepted outcomes from the accepted-results average while still counting their labor and inference cost in total study cost.

**Cost per accepted result** = total measured model, infrastructure, human labor, and rework cost over the full pilot divided by number of accepted work orders. If there are zero accepted results, report *not defined* instead of zero.

Use small initial samples as feasibility checks. Do not generalize percentage savings across customers or industries without representative prospective data.

## Sample measurement row (fictional)

Task: SYNTH-001; manual baseline 18 minutes; AI runtime 2 minutes; human preparation/review 7 minutes; rework 3 minutes; accepted after review; measured human minutes saved 8. This is **illustrative only**, not a Director performance claim.
