# PIHU Google Workspace MCP Server

An autonomous, multi-account Model Context Protocol (MCP) server providing deep integration with **Google Workspace** services (Gmail, Google Calendar, Google Drive, Google Docs, and Google Tasks) for **PIHU OS**.

---

## 🌟 Key Features

- **Multi-Account OAuth 2.0**: Connect multiple Google accounts simultaneously with primary account switching.
- **Gmail Automation**: Send emails, search threads, draft responses, and read incoming messages.
- **Unified Contact Resolution**: Send emails directly by specifying a contact's name (e.g. *"Email Anin regarding project update"*), automatically resolving email addresses from the local People Directory (`~/.pihu/contacts.json`).
- **Google Calendar Management**: Schedule meetings, list events, create smart reminders, and check conflict free/busy slots.
- **Google Drive & Docs**: Search files, read document contents, append notes, and create new documents.
- **Voice & Intent Driven**: Autonomous dispatch via PIHU Voice Assistant.

---

## 🏛️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PIHU OS Client Interfaces                       │
│  [Desktop App UI]   [PIHU CLI]   [REPL Mode]   [Voice Action Engine]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Tool Invocation
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Google Workspace MCP Server (FastMCP)                │
│   • OAuth 2.0 Token Manager (~/.pihu/google_tokens.json)               │
│   • Google API Client (Gmail v1, Calendar v3, Drive v3, Docs v1)       │
│   • Local People Directory Resolver (~/.pihu/contacts.json)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (OAuth 2.0 Bearer)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Google Cloud APIs Subsystem                     │
│    • Gmail API  • Google Calendar API  • Drive API  • Docs API         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Authentication & Setup

### 1. Configure OAuth Credentials
Set your Google Cloud OAuth Client ID and Secret in your environment or `~/.pihu/.env`:

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

### 2. Connect Your Google Account
- **Via PIHU Desktop Settings**:
  Open **Settings > Connections > Google Workspace** and click **Connect Google Account**.
- **Via PIHU CLI**:
  ```bash
  pihu mcp install google-workspace
  ```
- **Via Voice Assistant**:
  Say: *"PIHU, connect my Google account"*.

---

## 🧰 FastMCP Tools Catalog

### 📧 Gmail Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `send_email` | `recipient: str, subject: str, body: str, account?` | Sends an email. Supports recipient email addresses or saved contact names. |
| `search_emails` | `query: str, max_results?: int, account?` | Searches mailbox using standard Gmail search syntax (e.g. `from:boss is:unread`). |
| `read_email` | `message_id: str, account?` | Retrieves full body text, headers, and attachments for a specific message. |
| `list_drafts` | `max_results?: int, account?` | Lists current draft emails. |

### 📅 Calendar Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `list_events` | `time_min?: str, time_max?: str, max_results?: int` | Lists upcoming events and meetings within a date range. |
| `create_event` | `summary: str, start_time: str, end_time: str, attendees?` | Creates a new calendar event with optional attendee invitations. |
| `delete_event` | `event_id: str` | Removes an event from the primary calendar. |

### 📁 Drive & Docs Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `search_drive` | `query: str, page_size?: int` | Searches Google Drive files and folders. |
| `read_doc` | `document_id: str` | Reads and extracts plain text from a Google Doc. |
| `create_doc` | `title: str, content: str` | Creates a new Google Document with specified initial content. |

---

## 🗣️ Voice Commands Examples

- *"Send an email to Anin saying we are deploying PIHU OS v1.0 today"*
- *"What meetings do I have scheduled for tomorrow afternoon?"*
- *"Schedule a meeting with Mayank tomorrow at 3 PM called Sprint Review"*
- *"Search my Google Drive for the Q3 roadmap document"*
