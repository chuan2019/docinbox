---
title: ""
geometry: margin=2.5cm
fontsize: 11pt
colorlinks: false
header-includes:
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \fancyhead[L]{\small MSA-2026-0417 --- Meridian Analytics / Cobalt Peak Logistics}
  - \fancyhead[R]{\small CONFIDENTIAL}
  - \fancyfoot[C]{\small Page \thepage\ of \pageref{LastPage} \quad---\quad Fictional document for tutorial purposes only}
  - \usepackage{lastpage}
---

\begin{center}
{\LARGE \textbf{MASTER SERVICES AGREEMENT}}\\[4pt]
{\large Agreement No. MSA-2026-0417}
\end{center}

\vspace{6pt}

This Master Services Agreement (the "**Agreement**") is entered into as of **17 April 2026** (the "**Effective Date**") by and between:

**Meridian Analytics Pty Ltd**, a company incorporated in New South Wales, Australia, with its registered office at Level 12, 88 Harbour Street, Sydney NSW 2000, Australia ("**Provider**"); and

**Cobalt Peak Logistics LLC**, a limited liability company organized under the laws of the State of Colorado, with its principal place of business at 4200 Summit Ridge Drive, Denver, CO 80202, United States ("**Client**").

Provider and Client are each a "**Party**" and together the "**Parties**".

# 1. Purpose and Scope

1.1 Provider shall design, build, and operate a document intelligence platform (the "**Platform**") that ingests Client's shipping manifests, customs declarations, and freight invoices, extracts structured data from them, and produces daily operational summaries.

1.2 The Platform shall support ingestion of PDF, PNG, and TIFF documents at a volume of up to **250,000 documents per calendar month**, with automatic classification into at least twelve document categories agreed in Schedule A.

1.3 Any services outside the scope of this Agreement shall be agreed in a written Statement of Work signed by both Parties.

# 2. Term

2.1 This Agreement commences on the Effective Date and continues for an initial term of **twenty-four (24) months**, expiring on **16 April 2028** (the "**Initial Term**"), unless terminated earlier in accordance with Section 9.

2.2 Following the Initial Term, this Agreement renews automatically for successive twelve (12) month periods unless either Party gives written notice of non-renewal at least **ninety (90) days** before the end of the then-current term.

# 3. Fees and Payment

3.1 Client shall pay Provider a fixed implementation fee of **USD 180,000**, payable in three equal installments of USD 60,000 upon completion of Milestones M1, M2, and M3 as defined in Section 4.

3.2 From the Go-Live Date, Client shall pay Provider a monthly subscription fee of **USD 22,500**, plus a usage fee of **USD 0.04 per document** processed above the monthly volume of 250,000 documents.

3.3 All invoices are payable within **thirty (30) days** of the invoice date. Late payments accrue interest at 1.5% per month or the maximum rate permitted by law, whichever is lower.

3.4 All fees are exclusive of taxes. Client is responsible for all applicable sales, use, and value-added taxes, excluding taxes on Provider's net income.

# 4. Milestones and Delivery

4.1 Provider shall deliver the Platform in accordance with the following schedule:

| Milestone | Description | Target Date |
|-----------|-------------------------------------------------|-------------------|
| M1 | Ingestion pipeline and secure document store | 30 June 2026 |
| M2 | Extraction models for all Schedule A categories | 30 September 2026 |
| M3 | Operational dashboards and daily summary reports | 15 December 2026 |
| Go-Live | Production cutover and hypercare start | 12 January 2027 |

4.2 A Milestone is accepted when it passes the acceptance tests set out in Schedule B, or thirty (30) days after delivery if Client has not rejected it in writing with specific deficiencies, whichever occurs first.

# 5. Service Levels

5.1 From the Go-Live Date, Provider shall make the Platform available at least **99.5%** of the time in each calendar month, measured excluding scheduled maintenance windows announced at least seventy-two (72) hours in advance.

5.2 Provider shall process 95% of submitted documents within **five (5) minutes** of receipt, and shall achieve a field-level extraction accuracy of at least **97%** across the categories in Schedule A, measured quarterly against a jointly agreed sample.

5.3 If availability falls below 99.5% in any calendar month, Client is entitled to a service credit of 5% of that month's subscription fee for each full percentage point of shortfall, up to a maximum of 25%.

# 6. Data Protection and Security

6.1 As between the Parties, Client owns all documents submitted to the Platform and all data extracted from them ("**Client Data**"). Provider acquires no rights in Client Data except the limited right to process it to provide the services.

6.2 Provider shall store Client Data encrypted at rest using AES-256 and in transit using TLS 1.2 or higher, and shall retain Client Data only in data centers located in the United States and Australia.

6.3 Provider shall notify Client of any confirmed security incident affecting Client Data within **forty-eight (48) hours** of confirmation, and shall cooperate reasonably with Client's investigation.

6.4 Upon termination, Provider shall return or destroy all Client Data within sixty (60) days, except for backup copies retained for up to ninety (90) days under Provider's standard rotation, which remain subject to this Section 6.

# 7. Confidentiality

7.1 Each Party shall protect the other Party's Confidential Information with at least the same degree of care it uses for its own confidential information, and never less than reasonable care, and shall use it only to perform this Agreement.

7.2 These obligations survive for **five (5) years** after termination of this Agreement, and indefinitely for trade secrets.

# 8. Intellectual Property

8.1 Provider retains all rights in the Platform, its underlying models, and any improvements developed during the term. Client receives a non-exclusive, non-transferable license to use the Platform during the term for its internal business operations.

8.2 Custom report templates developed specifically for Client under a Statement of Work are assigned to Client upon payment in full.

# 9. Termination

9.1 Either Party may terminate this Agreement for material breach if the breach is not cured within thirty (30) days of written notice.

9.2 Client may terminate for convenience after the Initial Term on ninety (90) days' written notice.

9.3 Either Party may terminate immediately if the other Party becomes insolvent, makes an assignment for the benefit of creditors, or enters bankruptcy proceedings that are not dismissed within sixty (60) days.

# 10. Limitation of Liability

10.1 Neither Party is liable for indirect, incidental, special, or consequential damages, or for lost profits, even if advised of the possibility of such damages.

10.2 Each Party's aggregate liability under this Agreement is capped at the fees paid or payable by Client in the **twelve (12) months** preceding the event giving rise to the claim, except for breaches of Section 6 (Data Protection) or Section 7 (Confidentiality), where the cap is two times that amount.

# 11. General

11.1 This Agreement is governed by the laws of the State of Colorado, without regard to its conflict of laws rules. The Parties submit to the exclusive jurisdiction of the state and federal courts located in Denver, Colorado.

11.2 Neither Party may assign this Agreement without the other Party's prior written consent, except to an affiliate or in connection with a merger or sale of substantially all assets.

11.3 This Agreement, together with its Schedules, is the entire agreement between the Parties regarding its subject matter and supersedes all prior discussions and agreements.

\vspace{18pt}

**IN WITNESS WHEREOF**, the Parties have executed this Agreement as of the Effective Date.

\vspace{14pt}

\noindent
\begin{tabular}{@{}p{0.48\textwidth}p{0.48\textwidth}@{}}
\textbf{Meridian Analytics Pty Ltd} & \textbf{Cobalt Peak Logistics LLC} \\[16pt]
Signature: \hrulefill & Signature: \hrulefill \\[10pt]
Name: Alice Zhang & Name: Marcus Whitfield \\
Title: Chief Executive Officer & Title: VP, Supply Chain Operations \\
Date: 17 April 2026 & Date: 17 April 2026 \\
\end{tabular}

\vspace{16pt}

\begin{center}
\small\itshape
This document is entirely fictional and was created as sample data for a software tutorial series.\\
All companies, people, addresses, and figures are invented; any resemblance to real entities is coincidental.
\end{center}
