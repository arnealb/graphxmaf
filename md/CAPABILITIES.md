# Agent Capabilities Overview

This MCP server exposes your Microsoft 365 data (mail, calendar, files, contacts, people) via the Microsoft Graph API. Below is a description of everything a user can ask the agent.

---

## Identity

### Who am I?
Returns the display name and email address of the currently authenticated user.

**Example prompts:**
- "Who am I?"
- "What is my email address?"
- "Show me my account info."

---

## People

### Find a person
Search for people by name within your organisation's directory.

**Example prompts:**
- "Find John Doe."
- "Look up people named Sarah."
- "Who is Jan Peeters?"

---

## Email

### List inbox
Returns the most recent emails from your inbox, including subject, sender, and received date.

**Example prompts:**
- "Show me my emails."
- "List my inbox."
- "What are my latest messages?"

### Search emails
Filter emails by one or more criteria. All filters are optional and can be combined.

| Filter | Description | Example value |
|---|---|---|
| `sender` | Filter by sender name or email address | `"jan@example.com"` |
| `subject` | Filter by subject line (partial match) | `"project update"` |
| `received_after` | Only show emails received after this date | `"2024-01-01"` |
| `received_before` | Only show emails received before this date | `"2024-12-31"` |

**Example prompts:**
- "Find emails from jan@example.com."
- "Show me emails with 'invoice' in the subject."
- "Search for emails received after January 2024."
- "Find emails from Sarah about the budget received last month."

### Read an email
Open and read the full body of a specific email. Requires a message ID (returned by list or search).

**Example prompts:**
- "Read that email." *(after a search/list)*
- "Open the email with ID `<message_id>`."
- "What does that message say?"

---

## Files (OneDrive)

### Search files
Search for files or folders in your OneDrive by name or content keyword. Optionally scope the search to a specific drive or folder.

**Example prompts:**
- "Find files named 'budget'."
- "Search for PowerPoint files about Q3."
- "Look for the contract document."
- "Find files in my OneDrive related to the project."

---

## Contacts

### List contacts
Returns all contacts from your Outlook contact list, including name and email address.

**Example prompts:**
- "Show me my contacts."
- "List all my contacts."
- "Who is in my contact list?"

---

## Calendar

### List calendar
Returns upcoming and recent past calendar events, including subject, start time, and end time.

**Example prompts:**
- "Show me my calendar."
- "What meetings do I have?"
- "List my upcoming events."

### Search calendar events
Filter calendar events by one or more criteria. All filters are optional and can be combined.

| Filter | Description | Example value |
|---|---|---|
| `text` | Search by keyword in event title or description | `"standup"` |
| `location` | Filter by meeting location | `"Brussels"` |
| `attendee` | Filter by attendee name or email | `"jan@example.com"` |
| `start_after` | Only show events starting after this date | `"2024-06-01"` |
| `start_before` | Only show events starting before this date | `"2024-06-30"` |

**Example prompts:**
- "Find meetings about the sprint review."
- "Search for events in Brussels."
- "Show me all meetings with Jan next week."
- "What events do I have between June 1 and June 15?"
- "Find all standups after March 1."

---

## Summary Table

| Category | What you can ask | Tool |
|---|---|---|
| Identity | Who am I / my email | `whoami` |
| People | Find a person by name | `findpeople` |
| Email | List inbox | `list_email` |
| Email | Search by sender / subject / date | `search_email` |
| Email | Read full email body | `read_email` |
| Files | Search OneDrive by keyword | `search_files` |
| Contacts | List all contacts | `list_contacts` |
| Calendar | List upcoming & past events | `list_calendar` |
| Calendar | Search events by keyword / location / attendee / date | `search_calendar` |
