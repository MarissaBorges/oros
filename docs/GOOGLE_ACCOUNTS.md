# Google account integration

OpenJarvis already contains Gmail, Google Calendar, Google Contacts, Google
Drive, and Google Tasks connectors. OROS should use those implementations
instead of creating a separate OAuth stack.

## Setup

1. Create an OAuth desktop client in Google Cloud.
2. Download the credentials JSON outside the repository.
3. Configure the connector with `jarvis connect gdrive`, `jarvis connect gmail`,
   or the matching UI Data Sources workflow.
4. Approve the minimum scopes required for the task.

Recommended separation:

- Gmail: read, label, archive, and draft; sending only after approval.
- Calendar: read by default; create/update/delete only after approval.
- Drive: read/search; writes only inside an approved folder.
- Contacts: read/search; writes after approval.
- Tasks: create and update; deletion after approval.

Never store refresh tokens, client secrets, or access tokens in OROS source
code or screenshots.
