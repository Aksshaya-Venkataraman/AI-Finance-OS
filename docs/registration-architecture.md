# AI-Finance-OS
# Registration Architecture

## 1. Initial Registration Model

During the initial version of AI-Finance-OS,
a new user registration creates:

1. User
2. Organization
3. Organization Membership

The registering user becomes the organization Owner.

---

## 2. Registration Flow

User submits registration:

UserCreate
    ↓
Validate email
    ↓
Create User
    ↓
Create Organization
    ↓
Create OrganizationMembership
    ↓
Role = OWNER
    ↓
Commit transaction

---

## 3. Organization Name

The initial organization name can be generated
from the user's name.

Example:

User:

Aksshaya Venkataraman

Organization:

Aksshaya Venkataraman's Organization

The organization name can be changed later.

---

## 4. Transaction Safety

User, Organization and Membership creation
must occur within the same database transaction.

If any step fails:

The entire registration should be rolled back.

We must not create:

- A user without an organization
- An organization without an owner
- A membership pointing to a failed user

---

## 5. Initial Owner

The registering user receives:

OWNER

role.

The Owner can later:

- Invite users
- Assign roles
- Manage integrations
- View organization data
- Run AI investigations
- Manage organization settings

---

## 6. Future Registration Model

The production B2B model should support:

### New organization

User
→ Create Organization
→ Become Owner

### Existing organization

Owner
→ Invite User
→ User accepts invitation
→ Membership created

A user may eventually belong to multiple organizations.

---

## 7. Security Requirement

Organization membership must be created
server-side.

The client must never be allowed to choose:

- organization_id
- membership owner
- organization owner
- privileged role

The server determines these values.

---

## 8. Database Transaction

Registration should behave atomically:

BEGIN

Create User

Create Organization

Create Membership

COMMIT

If an error occurs:

ROLLBACK

---

## 9. First Implementation Goal

Modify the existing registration service so that
a successful registration creates:

User
+
Organization
+
OWNER Membership

Existing login functionality must continue working.