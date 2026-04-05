from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.gmail.gmail")
logger.debug("Loaded tool module: gmail.gmail")

import os
import ssl
import smtplib
import imaplib
import email
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from datetime import datetime, timezone
from pathlib import Path
from app.utils.groq import tool

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


def _load_env():
    if load_dotenv is None:
        return
    tool_dir = Path(__file__).resolve().parent        # .../gmail/tool
    gmail_dir = tool_dir.parent                       # .../gmail
    toolsf_dir = gmail_dir.parent                     # .../toolsf
    app_dir = toolsf_dir.parent                       # .../app
    candidates = [
        gmail_dir / ".env",           # app/toolsf/gmail/.env  (preferred)
        toolsf_dir / ".env",          # app/toolsf/.env
        app_dir / ".env",             # app/.env
        app_dir / "utils" / ".env",   # app/utils/.env
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(str(p))


_load_env()


def _get_creds(user: str | None):
    user = user or os.getenv("GMAIL_USER", "")
    app_password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not user or not app_password:
        raise ValueError("Missing GMAIL_USER or GMAIL_APP_PASSWORD (16-digit app password).")
    return user, app_password


def _format_imap_date(d: str) -> str:
    # Expect YYYY-MM-DD
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%d-%b-%Y")


def _extract_parts(msg, include_body: bool, include_html: bool, include_attachments: bool, download_dir: str | None):
    text_parts = []
    html_parts = []
    attachments = []
    for part in msg.walk():
        ctype = part.get_content_type()
        disp = str(part.get("Content-Disposition", "")).lower()
        if ctype == "text/plain" and "attachment" not in disp and include_body:
            payload = part.get_payload(decode=True) or b""
            text_parts.append(payload.decode(errors="ignore"))
        elif ctype == "text/html" and "attachment" not in disp and include_html:
            payload = part.get_payload(decode=True) or b""
            html_parts.append(payload.decode(errors="ignore"))
        elif "attachment" in disp and include_attachments:
            filename = part.get_filename() or "attachment.bin"
            data = part.get_payload(decode=True) or b""
            saved_path = ""
            if download_dir:
                ddir = Path(download_dir).expanduser()
                ddir.mkdir(parents=True, exist_ok=True)
                out = ddir / filename
                out.write_bytes(data)
                saved_path = str(out.resolve())
            attachments.append({"filename": filename, "size": len(data), "path": saved_path})
    return {
        "text": "\n".join(text_parts).strip(),
        "html": "\n".join(html_parts).strip(),
        "attachments": attachments,
    }


def _build_message(
    user: str,
    to: list[str],
    subject: str,
    body: str,
    html: str = "",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str = "",
    headers: dict | None = None,
    attachments: list[str] | None = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = ", ".join(to or [])
    if cc:
        msg["Cc"] = ", ".join(cc)
    if reply_to:
        msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    if headers:
        for k, v in headers.items():
            msg[str(k)] = str(v)

    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    for path in attachments or []:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Attachment not found: {p}")
        data = p.read_bytes()
        maintype = "application"
        subtype = "octet-stream"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=p.name)
    return msg


@tool(
    name="gmail_send",
    description="Send an email via Gmail (SMTP with 16-digit app password).",
    params={
        "to": {"type": "array", "description": "To recipients list"},
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Plain text body"},
        "html": {"type": "string", "description": "HTML body (optional)"},
        "cc": {"type": "array", "description": "CC recipients (optional)"},
        "bcc": {"type": "array", "description": "BCC recipients (optional)"},
        "reply_to": {"type": "string", "description": "Reply-To address (optional)"},
        "from_email": {"type": "string", "description": "Sender email (optional, defaults env)"},
        "attachments": {"type": "array", "description": "File paths to attach (optional)"},
        "headers": {"type": "object", "description": "Extra headers dict (optional)"},
        "smtp_host": {"type": "string", "description": "SMTP host (default smtp.gmail.com)"},
        "smtp_port": {"type": "integer", "description": "SMTP port (default 465)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_send(
    to: list[str],
    subject: str,
    body: str,
    html: str = "",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str = "",
    from_email: str = "",
    attachments: list[str] | None = None,
    headers: dict | None = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    timeout: int = 20,
):
    user, pw = _get_creds(from_email)
    msg = _build_message(
        user=user,
        to=to,
        subject=subject,
        body=body,
        html=html,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        headers=headers,
        attachments=attachments,
    )

    recipients = list(to or []) + list(cc or []) + list(bcc or [])
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
        server.login(user, pw)
        server.send_message(msg, from_addr=user, to_addrs=recipients)
    return {"ok": True, "sent_to": recipients}


@tool(
    name="gmail_send_later",
    description="Schedule an email to be sent later (stored locally if not due yet).",
    params={
        "send_at": {"type": "string", "description": "When to send (ISO 8601, e.g. 2026-04-01T18:30:00Z)"},
        "to": {"type": "array", "description": "To recipients list"},
        "subject": {"type": "string", "description": "Email subject"},
        "body": {"type": "string", "description": "Plain text body"},
        "html": {"type": "string", "description": "HTML body (optional)"},
        "cc": {"type": "array", "description": "CC recipients (optional)"},
        "bcc": {"type": "array", "description": "BCC recipients (optional)"},
        "reply_to": {"type": "string", "description": "Reply-To address (optional)"},
        "from_email": {"type": "string", "description": "Sender email (optional, defaults env)"},
        "attachments": {"type": "array", "description": "File paths to attach (optional)"},
        "headers": {"type": "object", "description": "Extra headers dict (optional)"},
        "smtp_host": {"type": "string", "description": "SMTP host (default smtp.gmail.com)"},
        "smtp_port": {"type": "integer", "description": "SMTP port (default 465)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_send_later(
    send_at: str,
    to: list[str],
    subject: str,
    body: str,
    html: str = "",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str = "",
    from_email: str = "",
    attachments: list[str] | None = None,
    headers: dict | None = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    timeout: int = 20,
):
    # Parse send_at
    send_dt = datetime.fromisoformat(send_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if send_dt <= now:
        return gmail_send(
            to=to,
            subject=subject,
            body=body,
            html=html,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            from_email=from_email,
            attachments=attachments,
            headers=headers,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            timeout=timeout,
        )

    user, pw = _get_creds(from_email)
    msg = _build_message(
        user=user,
        to=to,
        subject=subject,
        body=body,
        html=html,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        headers=headers,
        attachments=attachments,
    )

    queue_dir = Path(__file__).resolve().parent / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    fname = f"scheduled_{send_dt.timestamp():.0f}.eml"
    out = queue_dir / fname
    out.write_bytes(msg.as_bytes())

    meta = {
        "send_at": send_dt.isoformat(),
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "timeout": timeout,
        "from_email": user,
    }
    (queue_dir / f"{fname}.meta").write_text(str(meta), encoding="utf-8")

    return {"ok": True, "scheduled": send_dt.isoformat(), "queued_file": str(out.resolve())}


@tool(
    name="gmail_send_pending",
    description="Send any scheduled emails that are due (from local queue).",
    params={
        "from_email": {"type": "string", "description": "Sender email (optional, defaults env)"},
        "smtp_host": {"type": "string", "description": "SMTP host (default smtp.gmail.com)"},
        "smtp_port": {"type": "integer", "description": "SMTP port (default 465)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_send_pending(
    from_email: str = "",
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    timeout: int = 20,
):
    user, pw = _get_creds(from_email)
    queue_dir = Path(__file__).resolve().parent / "queue"
    if not queue_dir.exists():
        return {"ok": True, "sent": 0}

    now = datetime.now(timezone.utc)
    sent = 0
    for eml in sorted(queue_dir.glob("scheduled_*.eml")):
        try:
            ts = float(eml.stem.split("_", 1)[1])
        except Exception:
            continue
        if datetime.fromtimestamp(ts, tz=timezone.utc) > now:
            continue
        msg = email.message_from_bytes(eml.read_bytes())
        recipients = []
        for hdr in ("To", "Cc", "Bcc"):
            if msg.get(hdr):
                recipients += [x.strip() for x in msg.get(hdr, "").split(",") if x.strip()]
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout) as server:
            server.login(user, pw)
            server.send_message(msg, from_addr=user, to_addrs=recipients)
        eml.unlink(missing_ok=True)
        meta = eml.with_suffix(".eml.meta")
        meta.unlink(missing_ok=True)
        sent += 1

    return {"ok": True, "sent": sent}


@tool(
    name="gmail_list_folders",
    description="List Gmail folders/labels via IMAP.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_list_folders(
    email: str = "",
    imap_host: str = "imap.gmail.com",
    timeout: int = 20,
):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    status, data = mail.list()
    mail.logout()
    if status != "OK":
        return []
    return [d.decode(errors="ignore") for d in data]


@tool(
    name="gmail_fetch",
    description="Fetch emails via IMAP.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "query": {"type": "string", "description": "IMAP search query (optional)"},
        "unseen_only": {"type": "boolean", "description": "Only unread (default false)"},
        "since": {"type": "string", "description": "Since date YYYY-MM-DD (optional)"},
        "before": {"type": "string", "description": "Before date YYYY-MM-DD (optional)"},
        "limit": {"type": "integer", "description": "Max messages (default 10)"},
        "mark_read": {"type": "boolean", "description": "Mark as read (default false)"},
        "include_body": {"type": "boolean", "description": "Include plain text body (default true)"},
        "include_html": {"type": "boolean", "description": "Include HTML body (default false)"},
        "include_attachments": {"type": "boolean", "description": "Include attachments list (default false)"},
        "download_dir": {"type": "string", "description": "Download attachments to dir (optional)"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_fetch(
    email: str = "",
    folder: str = "INBOX",
    query: str = "",
    unseen_only: bool = False,
    since: str = "",
    before: str = "",
    limit: int = 10,
    mark_read: bool = False,
    include_body: bool = True,
    include_html: bool = False,
    include_attachments: bool = False,
    download_dir: str = "",
    imap_host: str = "imap.gmail.com",
    timeout: int = 20,
):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)

    criteria = []
    if unseen_only:
        criteria.append("UNSEEN")
    if since:
        criteria.append(f'SINCE "{_format_imap_date(since)}"')
    if before:
        criteria.append(f'BEFORE "{_format_imap_date(before)}"')
    if query:
        criteria.append(query)
    if not criteria:
        criteria = ["ALL"]
    search_query = " ".join(criteria)
    status, data = mail.search(None, search_query)
    if status != "OK":
        mail.logout()
        return []
    ids = data[0].split()
    ids = ids[-int(limit) :] if limit else ids

    results = []
    for msg_id in ids:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        parts = _extract_parts(
            msg,
            include_body=include_body,
            include_html=include_html,
            include_attachments=include_attachments,
            download_dir=download_dir or None,
        )
        results.append(
            {
                "id": msg_id.decode(errors="ignore"),
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "date": msg.get("Date", ""),
                "text": parts["text"],
                "html": parts["html"],
                "attachments": parts["attachments"],
            }
        )
        if mark_read:
            mail.store(msg_id, "+FLAGS", "\\Seen")

    mail.logout()
    return results


@tool(
    name="gmail_fetch_headers",
    description="Fetch email headers only (lightweight).",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "query": {"type": "string", "description": "IMAP search query (optional)"},
        "limit": {"type": "integer", "description": "Max messages (default 10)"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_fetch_headers(
    email: str = "",
    folder: str = "INBOX",
    query: str = "",
    limit: int = 10,
    imap_host: str = "imap.gmail.com",
    timeout: int = 20,
):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    status, data = mail.search(None, query or "ALL")
    if status != "OK":
        mail.logout()
        return []
    ids = data[0].split()
    ids = ids[-int(limit) :] if limit else ids
    results = []
    for msg_id in ids:
        status, msg_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER])")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        results.append(
            {
                "id": msg_id.decode(errors="ignore"),
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "date": msg.get("Date", ""),
            }
        )
    mail.logout()
    return results


@tool(
    name="gmail_get_raw",
    description="Fetch the raw RFC822 email content by message id.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "msg_id": {"type": "string", "description": "IMAP message id"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_get_raw(email: str = "", folder: str = "INBOX", msg_id: str = "", imap_host: str = "imap.gmail.com", timeout: int = 20):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    status, msg_data = mail.fetch(msg_id, "(RFC822)")
    mail.logout()
    if status != "OK":
        return ""
    return msg_data[0][1].decode(errors="ignore")


@tool(
    name="gmail_mark_read",
    description="Mark a message as read.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "msg_id": {"type": "string", "description": "IMAP message id"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_mark_read(email: str = "", folder: str = "INBOX", msg_id: str = "", imap_host: str = "imap.gmail.com", timeout: int = 20):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    mail.store(msg_id, "+FLAGS", "\\Seen")
    mail.logout()
    return {"ok": True}


@tool(
    name="gmail_mark_unread",
    description="Mark a message as unread.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "msg_id": {"type": "string", "description": "IMAP message id"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_mark_unread(email: str = "", folder: str = "INBOX", msg_id: str = "", imap_host: str = "imap.gmail.com", timeout: int = 20):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    mail.store(msg_id, "-FLAGS", "\\Seen")
    mail.logout()
    return {"ok": True}


@tool(
    name="gmail_delete",
    description="Delete a message (moves to Trash).",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Mailbox folder (default INBOX)"},
        "msg_id": {"type": "string", "description": "IMAP message id"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_delete(email: str = "", folder: str = "INBOX", msg_id: str = "", imap_host: str = "imap.gmail.com", timeout: int = 20):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    mail.store(msg_id, "+FLAGS", "\\Deleted")
    mail.expunge()
    mail.logout()
    return {"ok": True}


@tool(
    name="gmail_move",
    description="Move a message to another folder/label.",
    params={
        "email": {"type": "string", "description": "Gmail address (optional, defaults env)"},
        "folder": {"type": "string", "description": "Source mailbox folder (default INBOX)"},
        "msg_id": {"type": "string", "description": "IMAP message id"},
        "target_folder": {"type": "string", "description": "Target folder/label"},
        "imap_host": {"type": "string", "description": "IMAP host (default imap.gmail.com)"},
        "timeout": {"type": "integer", "description": "Timeout seconds (default 20)"},
    },
)
def gmail_move(email: str = "", folder: str = "INBOX", msg_id: str = "", target_folder: str = "", imap_host: str = "imap.gmail.com", timeout: int = 20):
    user, pw = _get_creds(email)
    mail = imaplib.IMAP4_SSL(imap_host, timeout=timeout)
    mail.login(user, pw)
    mail.select(folder)
    mail.copy(msg_id, target_folder)
    mail.store(msg_id, "+FLAGS", "\\Deleted")
    mail.expunge()
    mail.logout()
    return {"ok": True}
