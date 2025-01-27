from enum import Enum


class Role(Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"

    def is_viewer(self) -> bool:
        return self in {Role.VIEWER, Role.EDITOR, Role.OWNER}

    def is_editor(self) -> bool:
        return self in {Role.EDITOR, Role.OWNER}
