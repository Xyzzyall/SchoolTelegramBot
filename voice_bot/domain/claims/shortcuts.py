from voice_bot.domain.claims.base import ClaimDefinition
from voice_bot.domain.claims.non_auth_claim import NonAuthClaim
from voice_bot.domain.claims.role_claim import RoleClaim
from voice_bot.domain.roles import UserRoles

CLAIM_SYSADMIN = ClaimDefinition(RoleClaim, {"roles": {UserRoles.sysadmin}})
CLAIM_SCHEDULE = ClaimDefinition(RoleClaim, {"roles": {UserRoles.schedule}})

CLAIM_STUDENT = ClaimDefinition(RoleClaim, {"roles": {UserRoles.student}})

CLAIM_NOT_AUTH = ClaimDefinition(NonAuthClaim)
