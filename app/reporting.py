"""Reporting: the mp-active-users half of this project, fixed.

What changed versus the original export.py:

* the summary counts are actually printed in the PDF (the original computed
  them and then never used them);
* the charts the original defined but never called are embedded in the PDF;
* the report date is today, not a hardcoded 2025-02-26;
* the output paths are arguments, not a hardcoded macOS directory;
* the CSV split covers every user -- members in one file, guests in the
  other -- instead of silently dropping internal users whose domain did
  not match the hardcoded employer domain.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import date
from pathlib import Path

from .directory import DirectoryUser

INTERNAL_COLUMNS = [
    "Display name", "User principal name", "Object Id", "First name",
    "Last name", "When created", "Department", "CountryOrRegion", "Licenses",
]


def summarize(users: list[DirectoryUser]) -> dict:
    members = [u for u in users if not u.is_external_user]
    guests = [u for u in users if u.is_external_user]
    license_counts: Counter[str] = Counter()
    for user in users:
        for lic in user.license_list:
            license_counts[lic] += 1
    monthly: Counter[str] = Counter()
    for user in users:
        if user.when_created:
            monthly[user.when_created.strftime("%Y-%m")] += 1
    return {
        "total": len(users),
        "members": len(members),
        "guests": len(guests),
        "licensed": sum(1 for u in users if u.is_licensed),
        "unlicensed": sum(1 for u in users if not u.is_licensed),
        "license_counts": dict(license_counts.most_common()),
        "monthly_counts": dict(sorted(monthly.items())),
        "members_list": members,
        "guests_list": guests,
    }


def _chart_png_monthly(monthly: dict[str, int]) -> bytes | None:
    if not monthly:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(list(monthly.keys()), list(monthly.values()), marker="o")
    ax.set_title("Users created per month")
    ax.set_ylabel("Users")
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def _chart_png_licenses(license_counts: dict[str, int]) -> bytes | None:
    if not license_counts:
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    items = list(license_counts.items())[:10]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.barh([name for name, _ in items], [count for _, count in items])
    ax.set_title("License distribution (top 10)")
    ax.set_xlabel("Users")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def save_users_to_csv(users: list[DirectoryUser], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTERNAL_COLUMNS)
        writer.writeheader()
        for user in users:
            writer.writerow({
                "Display name": user.display_name,
                "User principal name": user.user_principal_name,
                "Object Id": user.object_id,
                "First name": user.first_name or "",
                "Last name": user.last_name or "",
                "When created": user.when_created.isoformat() if user.when_created else "",
                "Department": user.department or "",
                "CountryOrRegion": user.country_or_region or "",
                "Licenses": user.licenses or "",
            })


def split_users_to_csv(users: list[DirectoryUser], internal_path: str | Path,
                       external_path: str | Path) -> tuple[int, int]:
    """Write members and guests to two CSVs. Every user lands in exactly one."""
    summary = summarize(users)
    save_users_to_csv(summary["members_list"], internal_path)
    save_users_to_csv(summary["guests_list"], external_path)
    return len(summary["members_list"]), len(summary["guests_list"])


def export_to_pdf(users: list[DirectoryUser], path: str | Path) -> dict:
    """Build the PDF report. Returns the summary dict it printed."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    summary = summarize(users)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    elements = []

    def styled_table(header: list[str], rows: list[list[str]]):
        data = [header] + rows
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ]))
        return table

    elements.append(Paragraph("User Analysis Report", styles["Title"]))
    elements.append(Spacer(1, 0.25 * inch))
    elements.append(Paragraph(f"Generated on: {date.today().isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 0.25 * inch))

    elements.append(Paragraph("Summary", styles["Heading1"]))
    elements.append(styled_table(
        ["Metric", "Count"],
        [
            ["Total users", str(summary["total"])],
            ["Members (internal)", str(summary["members"])],
            ["Guests (external)", str(summary["guests"])],
            ["Licensed", str(summary["licensed"])],
            ["Unlicensed", str(summary["unlicensed"])],
        ],
    ))
    elements.append(Spacer(1, 0.25 * inch))

    if summary["license_counts"]:
        elements.append(Paragraph("Licenses", styles["Heading1"]))
        elements.append(styled_table(
            ["License", "Users"],
            [[name, str(count)] for name, count in summary["license_counts"].items()],
        ))
        png = _chart_png_licenses(summary["license_counts"])
        if png:
            elements.append(Image(io.BytesIO(png), width=6.5 * inch, height=2.8 * inch))
    if summary["monthly_counts"]:
        elements.append(Paragraph("Users created per month", styles["Heading1"]))
        elements.append(styled_table(
            ["Month", "Users"],
            [[month, str(count)] for month, count in summary["monthly_counts"].items()],
        ))
        png = _chart_png_monthly(summary["monthly_counts"])
        if png:
            elements.append(Image(io.BytesIO(png), width=6.5 * inch, height=2.8 * inch))

    for title, group in (("Members", summary["members_list"]),
                         ("Guests", summary["guests_list"])):
        elements.append(PageBreak())
        elements.append(Paragraph(title, styles["Heading1"]))
        elements.append(styled_table(
            ["Display Name", "User Principal Name"],
            [[u.display_name, u.user_principal_name] for u in group],
        ))

    SimpleDocTemplate(str(path), pagesize=letter).build(elements)
    return summary
