"""
Document action definitions — the complete set of operations that can be
authorized by the central policy service.

Every endpoint that touches a document must use one of these actions.
"""

import enum


class DocumentAction(str, enum.Enum):
    # Read operations
    LIST = "document:list"                          # list/discover document
    METADATA_READ = "document:metadata_read"        # read name, category, description
    CONTENT_READ = "document:content_read"          # read/preview file content
    DOWNLOAD = "document:download"                  # download file bytes
    VERSION_LIST = "document:version_list"          # list version history
    GRANT_LIST = "document:grant_list"              # list who has access (owner only)

    # Write operations
    EDIT_METADATA = "document:edit_metadata"        # edit name, description, category
    UPLOAD_VERSION = "document:upload_version"      # upload a new version

    # Owner-only operations
    SHARE = "document:share"                        # create a grant
    REVOKE = "document:revoke"                      # revoke a grant
    DELETE = "document:delete"                      # soft-delete
    RESTORE = "document:restore"                    # restore from soft-delete


# Maps each action to the minimum permission required
# Owner always has all permissions — this table applies to grant-based access
ACTION_REQUIRED_PERMISSION = {
    DocumentAction.LIST: "read",
    DocumentAction.METADATA_READ: "read",
    DocumentAction.CONTENT_READ: "read",
    DocumentAction.DOWNLOAD: "read",
    DocumentAction.VERSION_LIST: "read",
    DocumentAction.GRANT_LIST: None,      # owner-only, no grant suffices
    DocumentAction.EDIT_METADATA: "edit",
    DocumentAction.UPLOAD_VERSION: "edit",
    DocumentAction.SHARE: None,           # owner-only
    DocumentAction.REVOKE: None,          # owner-only
    DocumentAction.DELETE: None,          # owner-only
    DocumentAction.RESTORE: None,         # owner-only
}

# Actions that require ownership (grants alone are never sufficient)
OWNER_ONLY_ACTIONS = {
    DocumentAction.GRANT_LIST,
    DocumentAction.SHARE,
    DocumentAction.REVOKE,
    DocumentAction.DELETE,
    DocumentAction.RESTORE,
}
