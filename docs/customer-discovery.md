# AI-Finance-OS
## Customer Discovery: Northstar Software Ltd

## 1. Customer

Northstar Software Ltd is a fictional UK-based B2B SaaS company.

Employees: approximately 100

Finance team: 4 people

Accounting platform: Xero

Payment platform: Stripe

Primary currency: GBP

---

## 2. Customer Persona

Primary user:

CFO / Finance Director

Secondary users:

Finance Manager
FP&A Analyst
Finance Analyst

---

## 3. Customer Problem

The finance team spends significant time investigating
unexpected changes in expenses and financial performance.

The team currently relies heavily on spreadsheets,
manual filtering and financial reports.

---

## 4. Primary Use Case

The CFO wants to ask:

"Why did our operating expenses increase this month?"

AI-Finance-OS should investigate the underlying
financial data and provide an evidence-backed explanation.

---

## 5. Expected Outcome

The system should identify:

- Total expense change
- Percentage change
- Major expense categories
- Major vendors
- Relevant transactions
- Period-over-period variance
- Possible causes
- Supporting evidence
- Recommended investigation
- Confidence level

---

## 6. Business Value

The goal is to reduce the amount of manual investigation
required by the finance team.

The system should help finance professionals move from:

Data collection
→
Manual analysis
→
Manual investigation

to:

Question
→
Automated investigation
→
Evidence
→
Decision

---

## 7. Initial Integration

Primary:

Xero

Secondary:

Stripe

Future:

CSV
Excel
Bank feeds
Other accounting platforms

---

## 8. Security Requirements

The system must support:

- Tenant isolation
- Authentication
- Authorization
- Role-based access control
- Audit logging
- Secure integration credentials
- Data access controls

---

## 9. AI Requirements

The AI must not invent financial numbers.

Financial calculations must come from
deterministic application logic.

AI responses should reference the underlying
financial evidence used to generate the answer.

---

## 10. First Success Criteria

A finance user should be able to:

1. Create an organization
2. Invite users
3. Connect financial data
4. Synchronize transactions
5. Ask a financial question
6. Receive an evidence-backed answer
7. Inspect the underlying evidence
8. Record the investigation