# AI-Finance-OS
# Product Requirements

## 1. Product

AI-Finance-OS is an enterprise AI Finance Operations platform
for UK/EU businesses.

The platform connects financial data, deterministic financial
analytics and AI agents to help finance teams investigate
financial questions.

---

## 2. Organization

Every customer belongs to an Organization.

An Organization represents one business/customer.

An Organization owns:

- Users
- Financial data
- Integrations
- AI investigations
- Audit logs
- Financial documents

Financial data must never be accessible across organizations.

---

## 3. Users

Users belong to an Organization.

Initial user roles:

### Owner

Full organization access.

Can:

- Manage organization
- Invite users
- Remove users
- Manage roles
- Connect integrations
- View financial data
- Run AI investigations
- View audit logs

### Finance Manager

Can:

- View financial data
- Run AI investigations
- View investigation evidence
- Manage financial analysis

Cannot:

- Delete organization
- Manage organization ownership

### Finance Analyst

Can:

- View permitted financial data
- Run investigations
- View investigation results
- View supporting evidence

Cannot:

- Manage organization
- Manage users
- Configure integrations

---

## 4. Financial Data

The platform should eventually support:

- Transactions
- Accounts
- Invoices
- Bills
- Vendors
- Customers
- Payments
- Budgets
- Financial periods
- Currencies

All financial records belong to an Organization.

---

## 5. Integrations

Initial integration:

Xero

Second integration:

Stripe

Future integrations:

- CSV
- Excel
- Bank feeds
- QuickBooks
- Other accounting platforms

The integration layer must normalize external financial data
into the AI-Finance-OS internal financial data model.

---

## 6. AI Investigation

The primary workflow is:

User asks:

"Why did our operating expenses increase this month?"

AI-Finance-OS should:

1. Understand the question
2. Identify the relevant financial period
3. Retrieve financial data
4. Calculate financial metrics
5. Identify significant changes
6. Identify categories responsible for the change
7. Identify major vendors
8. Retrieve supporting transactions
9. Investigate possible causes
10. Produce an evidence-backed explanation
11. Provide recommendations
12. Provide confidence level
13. Allow the user to inspect the evidence

---

## 7. Deterministic Financial Analysis

Financial calculations must be performed by
application logic.

The AI must not calculate financial numbers itself.

Examples:

- Revenue growth
- Expense growth
- Percentage variance
- Category variance
- Vendor variance
- Cash-flow change
- Budget variance

The AI interprets the calculated results.

---

## 8. Evidence

Every AI investigation should maintain evidence.

Evidence may include:

- Transactions
- Invoices
- Vendors
- Accounts
- Financial reports
- Calculated metrics
- Company documents

The user must be able to inspect the evidence supporting
an AI-generated conclusion.

---

## 9. Investigation Record

Every investigation should be stored.

An investigation should contain:

- User
- Organization
- Question
- Time period
- Analysis performed
- Evidence
- AI response
- Recommendations
- Confidence
- Timestamp

---

## 10. Auditability

Important actions must be recorded.

Examples:

- User login
- Integration connection
- Data synchronization
- Investigation started
- Investigation completed
- Investigation failed
- User changes
- Permission changes

---

## 11. Security

The platform must support:

- Authentication
- Authorization
- Role-based access control
- Organization isolation
- Audit logging
- Secure credentials
- Data access controls

---

## 12. First Product Success Criteria

A finance user can:

1. Create an organization
2. Invite another user
3. Assign a role
4. Connect Xero
5. Synchronize financial data
6. Ask a financial question
7. Receive an evidence-backed answer
8. Inspect supporting evidence
9. Save the investigation
10. Review the investigation later