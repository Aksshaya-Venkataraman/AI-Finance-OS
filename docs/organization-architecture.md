# AI-Finance-OS
# Organization & Access Architecture

## 1. Multi-Tenant Architecture

AI-Finance-OS is a multi-tenant B2B SaaS platform.

Each customer is represented by an Organization.

Every organization owns its users, financial data,
integrations, investigations and audit records.

---

## 2. Organization

An Organization represents a customer business.

Example:

Northstar Software Ltd

An organization contains:

- Organization profile
- Users
- Roles
- Financial data
- Integrations
- AI investigations
- Audit logs
- Documents

---

## 3. User Membership

A user belongs to an organization through an
organization membership.

A user should not directly own financial data.

Instead:

Organization
→ User Membership
→ Financial Data

This allows the system to support multiple users
within the same company.

---

## 4. Roles

Initial roles:

### Owner

Permissions:

- Manage organization
- Invite users
- Remove users
- Assign roles
- Connect integrations
- Disconnect integrations
- View financial data
- Run AI investigations
- View audit logs

### Finance Manager

Permissions:

- View financial data
- Run AI investigations
- View investigation evidence
- Manage financial analysis

Restrictions:

- Cannot delete organization
- Cannot transfer ownership
- Cannot manage organization ownership

### Finance Analyst

Permissions:

- View permitted financial data
- Run AI investigations
- View investigation results
- View evidence

Restrictions:

- Cannot manage users
- Cannot manage organization
- Cannot configure integrations

---

## 5. Tenant Isolation

Every organization-owned record must contain
an organization identifier.

Examples:

- transactions.organization_id
- invoices.organization_id
- vendors.organization_id
- customers.organization_id
- integrations.organization_id
- investigations.organization_id
- audit_logs.organization_id

Application queries must always enforce organization isolation.

Example:

A user belonging to Organization A requests transactions.

The application must effectively perform:

WHERE organization_id = current_user.organization_id

The organization identifier must never be trusted
from user-provided request data.

---

## 6. Access Control

Authorization should happen after authentication.

Authentication answers:

"Who is this user?"

Authorization answers:

"What is this user allowed to access?"

Example:

User
→ Authentication
→ Organization membership
→ Role
→ Permission
→ Resource access

---

## 7. Organization Ownership

Each organization has an owner.

The owner is responsible for:

- Organization management
- User invitations
- Role assignment
- Integration management
- Organization settings

---

## 8. User Invitations

Users should eventually be invited by an existing
organization member.

Initial workflow:

Owner
→ Enter user's email
→ Select role
→ Send invitation
→ User accepts invitation
→ User joins organization

---

## 9. Future Organization Model

The architecture should eventually support:

- Multiple organizations per user
- Organization switching
- Organization membership
- Custom roles
- Permission policies
- Organization-level settings
- Subscription plans
- Usage limits

These features do not need to be implemented
in the first version.

---

## 10. Security Principle

Never trust organization_id supplied by the client.

The server must determine the organization from
the authenticated user's membership.

Incorrect:

client.organization_id
→ database query

Correct:

authenticated user
→ membership
→ organization
→ database query

---

## 11. First Implementation Target

The first implementation should introduce:

Organization
→ User membership
→ Role

Then existing authentication will be connected
to organization membership.

Financial models will be added afterwards.