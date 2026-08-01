# Blog series demo assets

`contract.pdf` is the sample document used in the upload/download examples
throughout the series (Part 3 onwards). It is an entirely fictional Master
Services Agreement between two invented companies, written to be useful in
later parts too: it is dense with extractable entities (parties, people,
dates, dollar amounts, SLA percentages, milestones) for the LLM summary /
topics / entity-extraction parts, and its Provider-side signatory is
**Alice Zhang** to line up with the "Alice's contracts" ownership examples
introduced in Part 4.

Regenerate after editing `contract.md`:

```bash
pandoc contract.md -o contract.pdf --pdf-engine=pdflatex
```
