# UCI South German Credit inquiry: read-only send checklist

Status: **not authorized for sending**. This checklist freezes the reviewed
draft identity and the unresolved delivery controls. It is not a send command,
authorization, network probe, or approval to create an account or public case.

Reviewed content baseline:
`docs/alternative-data-credit-assessment@83bc839a9b9dbff3abcfec463dbab5f24744b23b`.

## Recipient channel and source evidence

- Intended publisher: UCI Machine Learning Repository.
- Official contact landing page: <https://archive.ics.uci.edu/contact>.
- Repository evidence: the approved candidate record
  `docs/data-sources/pending/uci-south-german-credit-2019.md` and the reviewed
  draft both identify that HTTPS page as UCI's official contact route.
- Delivery mechanism: **unresolved**. The existing evidence establishes the
  official landing page, but does not establish its current form action,
  required account, destination mailbox, or ticket visibility. No network call
  may be made merely to resolve these fields under this checklist.
- Recipient address or form endpoint: **unset and blocking**. It must be fixed
  from independently reviewed official evidence before a send authorization.

## Frozen subject and body

Source file:
`docs/data-sources/contact-drafts/uci-south-german-credit-request.md`.

Canonicalization is UTF-8 with LF line endings:

- Subject bytes are the exact characters after `Suggested subject: `, without
  a trailing LF.
- Body bytes begin with `Hello UCI Machine Learning Repository team,` and end
  with `Thank you.` followed by one LF. They are the content under
  `## Message draft`, excluding the blank line immediately after that heading
  and the blank line immediately before `## Send gate and response handling`.
- No form-added signature, salutation change, wrapping change, tracking
  parameter, attachment, or omitted question is part of the reviewed payload.

Frozen identities:

- Subject: `South German Credit package response headers, version, and provenance metadata`
- Subject SHA-256: `811065e2ed3d8d60f13aea3a1af06628d08d2b98c14581da59474abd08cbfc75`
- Body byte count: `3123`
- Body SHA-256: `55145d11856aa4d6d67174b12fed4c1b77b642cba262b3a904f3c852b6bcb528`

Before any authorized send, an independent reviewer must reproduce both hashes
from the reviewed commit. Any byte change requires a new content review and a
new single-send authorization.

## Sender identity and visibility

- Sender identity: **unset and blocking**. No individual, bot, shared mailbox,
  or project account is authorized by this checklist.
- The sender must be named by custice in the later single-send authorization
  and must use an identity they are authorized to represent.
- Public-case behavior: **unknown and blocking**. The approved evidence does
  not establish whether submission creates a public ticket, public profile, or
  searchable archive. A send is prohibited until the reviewed channel evidence
  says either that the exchange is private or that custice explicitly accepts
  the documented public exposure.
- The sender must not include credentials, local paths, Run IDs, authorization
  artifacts, audit hashes, consumer data, or other nonpublic operational data.

## Reply archive and privacy boundary

- Raw replies and attachments must remain outside Git under the fixed local
  root `/home/kouji175/dev-court/uci-south-german-credit-live/correspondence/`.
- A send authorization must assign a unique case ID below that root before
  submission. The case directory must be `0700`; raw message and attachment
  files must be `0600`. The root and case directory are not created by this
  checklist.
- Do not commit respondent names, email addresses, signatures, message headers,
  unpublished attachments, or verbatim private correspondence.
- The repository may later contain only a separately reviewed, minimized
  evidence note: publisher/organization role, received timestamp, answered
  question IDs, nonpersonal factual conclusions, and citations or hashes needed
  for provenance. Ambiguous or unanswered items remain unresolved.
- Attachments do not become trusted package bytes. They require a separate
  quarantine, content, license, privacy, and admission review.
- A reply cannot authorize a new live retrieval, modify the allowlist, admit or
  promote data, write data into the repository, or permit redistribution.

## Fail-closed authorization gate

Sending remains prohibited unless a later, explicit instruction from custice
binds all of the following in one authorization:

1. the reviewed commit and both payload SHA-256 values above;
2. the exact official recipient endpoint or address and its source evidence;
3. the named sender identity;
4. the documented private/public visibility decision;
5. the reply case ID and archive path;
6. one send attempt, with no automatic retry, follow-up, or attachment upload.

Until those values are independently reviewed and explicitly authorized, keep
the draft unchanged and do not contact the publisher.
