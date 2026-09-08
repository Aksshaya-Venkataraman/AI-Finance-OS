# AI-Finance-OS
# Enterprise Data Model

## 1. Core Entities

The initial enterprise data model contains:

- User
- Organization
- OrganizationMembership
- Role

Future entities will include:

- FinancialAccount
- Transaction
- Invoice
- Bill
- Vendor
- Customer
- Integration
- Investigation
- InvestigationEvidence
- AuditLog

---

# 2. User

The User represents an individual person using
AI-Finance-OS.

Fields:

- id
- full_name
- email
- hashed_password
- is_active
- is_superuser
- created_at
- updated_at

A User does not directly own organization financial data.

Organization access is determined through membership.

---

# 3. Organization

An Organization represents one customer business.

Fields:

- id
- name
- legal_name
- country
- default_currency
- timezone
- is_active
- created_at
- updated_at

Example:

Organization:

Northstar Software Ltd

Country:

United Kingdom

Currency:

GBP

---

# 4. OrganizationMembership

OrganizationMembership connects users to organizations.

Fields:

- id
- organization_id
- user_id
- role
- is_active
- created_at
- updated_at

Relationship:

Organization
→ has many memberships

User
→ can have many memberships

This allows the system to support a user
belonging to multiple organizations in the future.

---

# 5. Role

Initial roles:

- OWNER
- FINANCE_MANAGER
- FINANCE_ANALYST

Roles determine what actions a user can perform.

The initial implementation may use an enum.

Example:

OWNER

FINANCE_MANAGER

FINANCE_ANALYST

A future version may introduce:

- Custom roles
- Fine-grained permissions
- Permission policies

---

# 6. Organization Relationships

One Organization can have:

- Many memberships
- Many financial accounts
- Many transactions
- Many invoices
- Many bills
- Many vendors
- Many customers
- Many integrations
- Many investigations
- Many audit logs

---

# 7. User Relationships

One User can have:

- Many organization memberships
- Many investigations
- Many audit events

The user should access organization resources
through their membership.

---

# 8. Tenant Isolation

Every organization-owned entity must contain:

organization_id

Examples:

transactions.organization_id

invoices.organization_id

vendors.organization_id

investigations.organization_id

audit_logs.organization_id

Queries must always be scoped to the authenticated
organization.

---

# 9. Referential Integrity

Foreign keys should be used wherever relationships exist.

Examples:

organization_memberships.organization_id
→ organizations.id

organization_memberships.user_id
→ users.id

transactions.organization_id
→ organizations.id

investigations.organization_id
→ organizations.id

---

# 10. Uniqueness Rules

User email:

Globally unique.

Organization name:

Not necessarily globally unique.

Membership:

A user should not have duplicate membership
in the same organization.

Therefore:

organization_id + user_id

should be unique together.

---

# 11. Deletion Strategy

Organizations and financial records should not
be casually hard-deleted.

The system should prefer soft deletion or
deactivation where appropriate.

Examples:

Organization:

is_active

User:

is_active

Membership:

is_active

Financial records should normally be retained
for auditability.

---

# 12. Financial Data Ownership

Financial records belong to an organization,
not directly to an individual user.

Example:

Organization
    ↓
Transaction

NOT:

User
    ↓
Transaction

This is critical for B2B SaaS.

---

# 13. Investigation Ownership

An Investigation belongs to:

- Organization
- User

Therefore:

Organization
    ↓
Investigation
    ↓
Created by User

This allows the organization to retain the
investigation even if the user later leaves
the organization.

---

# 14. Audit Ownership

Audit logs belong to an organization.

An audit event may also reference the user
who performed the action.

Example:

Organization
    ↓
AuditLog
    ↓
User

The organization remains the primary owner
of the audit record.

---

# 15. Initial Database Relationship

The first implementation should establish:

User
  ↓
OrganizationMembership
  ↓
Organization

with:

Role

attached to OrganizationMembership.

---

# 16. Future Financial Architecture

After the organization model is implemented,
financial entities will be introduced.

Planned relationship:

Organization
│
├── Chart of Accounts
├── Transactions
├── Invoices
├── Bills
├── Vendors
├── Customers
├── Payments
├── Budgets
└── Financial Periods

---

# 17. Future Integration Architecture

Organization
│
├── Xero Integration
├── Stripe Integration
├── CSV Import
├── Excel Import
└── Bank Integration

Integration credentials must never be exposed
to normal users.

Credentials should be encrypted and managed
through a secure secrets mechanism.

---

# 18. Design Principle

The database should represent the business,
not the AI.

The AI layer sits on top of the financial
data model.

Therefore:

Financial Data
→ Deterministic Analytics
→ AI Investigation
→ Evidence
→ Recommendation

The AI must not become the source of truth
for financial numbers.