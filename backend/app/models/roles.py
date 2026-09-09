from enum import Enum


class OrganizationRole(str, Enum):
    OWNER = "OWNER"
    FINANCE_MANAGER = "FINANCE_MANAGER"
    FINANCE_ANALYST = "FINANCE_ANALYST"