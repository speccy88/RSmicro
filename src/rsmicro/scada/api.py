from enum import StrEnum
class Role(StrEnum): VIEWER="VIEWER"; OPERATOR="OPERATOR"; ENGINEERING="ENGINEERING"
WRITE_ROLES={Role.OPERATOR,Role.ENGINEERING}; FORCE_ROLES={Role.ENGINEERING}
def require(role,operation):
 allowed=FORCE_ROLES if operation in ("force_tag","clear_force","clear_all_forces") else WRITE_ROLES if operation=="write_tag" else set(Role)
 if Role(role) not in allowed: raise PermissionError(f"{role} may not perform {operation}")
