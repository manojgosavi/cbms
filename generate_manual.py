"""
CBMS User Manual — PDF generator.

Usage:
    python generate_manual.py

Output:
    CBMS_User_Manual.pdf  (in current directory)

Requires:  pip install reportlab
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, ListFlowable, ListItem,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── Colour palette ────────────────────────────────────────────────────────────
BLUE_DARK   = colors.HexColor("#1F4E79")
BLUE_MID    = colors.HexColor("#2E75B6")
BLUE_LIGHT  = colors.HexColor("#BDD7EE")
BLUE_PALE   = colors.HexColor("#DEEAF1")
GREEN_LIGHT = colors.HexColor("#E2EFDA")
GREY_LIGHT  = colors.HexColor("#F2F2F2")
GREY_TEXT   = colors.HexColor("#595959")
WHITE       = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 2.2 * cm


# ── Style sheet ───────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        base.add(ParagraphStyle(name=name, **kw))

    add("ManualTitle",
        fontSize=28, leading=34, textColor=BLUE_DARK,
        fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=6)

    add("ManualSubtitle",
        fontSize=13, leading=18, textColor=BLUE_MID,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4)

    add("ManualVersion",
        fontSize=10, leading=14, textColor=GREY_TEXT,
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=30)

    add("H1",
        fontSize=18, leading=24, textColor=WHITE,
        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=10,
        backColor=BLUE_DARK, leftIndent=-MARGIN+0.5*cm,
        rightIndent=-MARGIN+0.5*cm, borderPadding=(6, 8, 6, 8))

    add("H2",
        fontSize=13, leading=18, textColor=BLUE_DARK,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4,
        borderPadding=(2, 0, 2, 0))

    add("H3",
        fontSize=11, leading=15, textColor=BLUE_MID,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=3)

    add("Body",
        fontSize=10, leading=15, textColor=colors.black,
        fontName="Helvetica", spaceAfter=6, alignment=TA_JUSTIFY)

    add("Note",
        fontSize=9, leading=13, textColor=GREY_TEXT,
        fontName="Helvetica-Oblique", spaceAfter=6,
        leftIndent=12, borderPadding=4)

    add("Tip",
        fontSize=9.5, leading=14, textColor=colors.HexColor("#1D4E1A"),
        fontName="Helvetica", spaceAfter=8,
        backColor=GREEN_LIGHT, leftIndent=8, borderPadding=(4,6,4,6))

    add("Warning",
        fontSize=9.5, leading=14, textColor=colors.HexColor("#7B3F00"),
        fontName="Helvetica", spaceAfter=8,
        backColor=colors.HexColor("#FFF3CC"),
        leftIndent=8, borderPadding=(4,6,4,6))

    add("CodeBlock",
        fontSize=9, leading=13, textColor=colors.HexColor("#1A1A1A"),
        fontName="Courier", spaceAfter=6,
        backColor=GREY_LIGHT, leftIndent=12, borderPadding=(4,6,4,6))

    # Table cell styles — must be Paragraph objects to enable word-wrap
    add("TH",
        fontSize=9, leading=12, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    add("TD",
        fontSize=9, leading=13, textColor=colors.black,
        fontName="Helvetica", alignment=TA_LEFT, wordWrap="CJK")
    add("TDMono",
        fontSize=8.5, leading=12, textColor=colors.HexColor("#1A1A1A"),
        fontName="Courier", alignment=TA_LEFT)

    add("TOCEntry1",
        fontSize=11, leading=16, fontName="Helvetica-Bold",
        textColor=BLUE_DARK, leftIndent=0)

    add("TOCEntry2",
        fontSize=10, leading=14, fontName="Helvetica",
        textColor=colors.black, leftIndent=16)

    return base


# ── Helpers ───────────────────────────────────────────────────────────────────

def h1(text, styles):
    return Paragraph(f"&nbsp;&nbsp;{text}", styles["H1"])

def h2(text, styles):
    return Paragraph(text, styles["H2"])

def h3(text, styles):
    return Paragraph(text, styles["H3"])

def body(text, styles):
    return Paragraph(text, styles["Body"])

def note(text, styles):
    return Paragraph(f"ℹ️  {text}", styles["Note"])

def tip(text, styles):
    return Paragraph(f"✅  {text}", styles["Tip"])

def warn(text, styles):
    return Paragraph(f"⚠️  {text}", styles["Warning"])

def code(text, styles):
    return Paragraph(text.replace(" ", "&nbsp;").replace("\n", "<br/>"), styles["CodeBlock"])

def sp(n=1):
    return Spacer(1, n * 0.35 * cm)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BLUE_LIGHT, spaceAfter=6)

def bullet_list(items, styles):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["Body"]), leftIndent=20) for item in items],
        bulletType="bullet", bulletFontSize=8, bulletColor=BLUE_MID,
        leftIndent=12, spaceAfter=6,
    )

def _cell(val, style):
    """Convert any value to a Paragraph so ReportLab wraps it properly."""
    text = str(val) if val is not None else ""
    # Newlines → <br/> for multi-line cells
    text = text.replace("\n", "<br/>")
    return Paragraph(text, style)


def table(headers, rows, col_widths=None, styles=None):
    """Build a styled table with word-wrapping cells."""
    # styles is injected at call-site; fall back to simple ParagraphStyle if absent
    if styles:
        th_style = styles["TH"]
        td_style = styles["TD"]
    else:
        th_style = ParagraphStyle("_th", fontSize=9, fontName="Helvetica-Bold",
                                  textColor=WHITE, alignment=TA_CENTER)
        td_style = ParagraphStyle("_td", fontSize=9, fontName="Helvetica",
                                  textColor=colors.black, alignment=TA_LEFT)

    wrapped_headers = [_cell(h, th_style) for h in headers]
    wrapped_rows    = [[_cell(c, td_style) for c in row] for row in rows]
    data = [wrapped_headers] + wrapped_rows

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  BLUE_DARK),
        ("BACKGROUND",   (0,1), (-1,-1), WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GREY_LIGHT]),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",   (0,0), (-1,0),  6),
        ("BOTTOMPADDING",(0,0), (-1,0),  6),
        ("TOPPADDING",   (0,1), (-1,-1), 5),
        ("BOTTOMPADDING",(0,1), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("BOX",          (0,0), (-1,-1), 0.8, BLUE_MID),
    ]))
    return t


# ── Page template ─────────────────────────────────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Header bar
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, h - 1.1*cm, w, 1.1*cm, fill=True, stroke=False)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, h - 0.72*cm, "CBMS — Central Biorepository Management Software")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - MARGIN, h - 0.72*cm, "User Manual  v1.0.0")
    # Footer
    canvas.setFillColor(BLUE_LIGHT)
    canvas.rect(0, 0, w, 0.9*cm, fill=True, stroke=False)
    canvas.setFillColor(BLUE_DARK)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, 0.32*cm, "CBMS User Manual — Confidential")
    canvas.drawRightString(w - MARGIN, 0.32*cm, f"Page {doc.page}")
    canvas.restoreState()

def on_first_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, 0, w, 0.9*cm, fill=True, stroke=False)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - MARGIN, 0.32*cm, "Page 1")
    canvas.restoreState()


# ── Manual content ────────────────────────────────────────────────────────────

def build_manual(output_path="CBMS_User_Manual.pdf"):
    styles = make_styles()
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.6*cm, bottomMargin=1.4*cm,
        title="CBMS User Manual",
        author="CBMS",
        subject="Central Biorepository Management Software — User Manual v1.0.0",
    )

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 3*cm),
        Paragraph("CBMS", styles["ManualTitle"]),
        Paragraph("Central Biorepository Management Software", styles["ManualSubtitle"]),
        Spacer(1, 0.5*cm),
        HRFlowable(width="60%", thickness=2, color=BLUE_MID,
                   hAlign="CENTER", spaceAfter=16),
        Paragraph("User Manual", styles["ManualSubtitle"]),
        Paragraph("Version 1.0.0  ·  2026", styles["ManualVersion"]),
        Spacer(1, 2*cm),
    ]

    cover_table = Table(
        [["For internal use by authorised research staff only."]],
        colWidths=[PAGE_W - 2*MARGIN],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), BLUE_PALE),
        ("TEXTCOLOR",    (0,0), (-1,-1), BLUE_DARK),
        ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Oblique"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("BOX",          (0,0), (-1,-1), 1, BLUE_MID),
    ]))
    story.append(cover_table)
    story.append(PageBreak())

    # ── Table of contents ─────────────────────────────────────────────────────
    story.append(h1("Table of Contents", styles))
    story.append(sp())
    toc_items = [
        ("1. Overview", ""),
        ("2. Installation", "macOS · Windows · First Launch"),
        ("3. Login & User Roles", ""),
        ("4. Dashboard", "KPI numbers · Cohort flowchart"),
        ("5. Studies Tab", "Create and manage studies"),
        ("6. Participants Tab", "Register · Import from Excel · Export"),
        ("7. Samples Tab", "Add samples · Manage aliquots"),
        ("8. Storage Tab", "Hierarchy · Box grid · Place aliquots"),
        ("9. Search Tab", "Filters · Block · Unblock · Ship · Navigate to box"),
        ("10. Shipments Tab", "Create and view shipments"),
        ("11. Catalogue Tab", "Pivot table · Filters · Export"),
        ("12. Admin Tab", "Users · Audit Log · Backup"),
        ("13. Excel Import Reference", "Column spec · Validation rules"),
        ("14. Backup & Recovery", "Manual backup · Restore"),
        ("15. Keyboard Shortcuts", ""),
        ("16. Troubleshooting", ""),
    ]
    for title, subtitle in toc_items:
        line = f"<b>{title}</b>"
        if subtitle:
            line += f"  <font color='#595959' size='9'>— {subtitle}</font>"
        story.append(Paragraph(line, styles["TOCEntry1"]))
        story.append(sp(0.4))
    story.append(PageBreak())

    # ── 1. Overview ───────────────────────────────────────────────────────────
    story += [
        h1("1. Overview", styles), sp(),
        body("CBMS (Central Biorepository Management Software) is a local desktop "
             "application for managing the full lifecycle of biological samples in "
             "HIV and infectious-disease research cohort studies. It runs entirely "
             "on a single workstation with no internet connection required.", styles),
        sp(),
        h2("What CBMS manages", styles),
        bullet_list([
            "<b>Participants</b> — demographic registration and visit records",
            "<b>Samples & Aliquots</b> — collection, typing, and aliquot tracking",
            "<b>Storage</b> — 6-level freezer hierarchy down to individual box positions",
            "<b>Shipments</b> — shipping aliquots to researchers with full history",
            "<b>Catalogue</b> — pivot-table view of available sample inventory",
            "<b>Audit trail</b> — every action logged with timestamp and user",
            "<b>User access control</b> — three roles with distinct permissions",
        ], styles),
        sp(),
        h2("Tab layout", styles),
        table(
            ["Tab", "Purpose", "Keyboard shortcut"],
            [
                ["Dashboard",    "KPI summary + cohort flowchart",       "Ctrl+1"],
                ["Studies",      "Create and manage study projects",      "Ctrl+2"],
                ["Participants", "Register and search participants",      "Ctrl+3"],
                ["Samples",      "Add samples and aliquots per visit",   "Ctrl+4"],
                ["Storage",      "Visual box grid — place & move aliquots","Ctrl+5"],
                ["Search",       "Multi-criteria search across all data", "Ctrl+F"],
                ["Shipments",    "Create and track shipments",           "Ctrl+6"],
                ["Catalogue",    "Sample-type pivot table & export",     "Ctrl+7"],
                ["Admin",        "Users, audit log, backup",             "Ctrl+8"],
            ],
            col_widths=[3.5*cm, 9.6*cm, 3.5*cm],
            styles=styles,
        ),
        PageBreak(),
    ]

    # ── 2. Installation ───────────────────────────────────────────────────────
    story += [
        h1("2. Installation", styles), sp(),

        h2("macOS", styles),
        body("Requirements: macOS 11 or later, Python 3.10+ (only needed to build; "
             "the distributed app bundle is self-contained).", styles),
        sp(0.5),
        h3("Option A — Run the installer script (recommended)", styles),
        bullet_list([
            "Open Terminal.",
            "Navigate to the CBMS project folder:",
            "Run the installer:",
        ], styles),
        code("cd /path/to/cbms_with_excel_import_clean\nchmod +x install_and_build.sh\n./install_and_build.sh", styles),
        body("The script will install all dependencies, build <b>dist/CBMS.app</b>, "
             "and create <b>dist/CBMS-v1.0.0.dmg</b>.", styles),
        sp(0.5),
        h3("Option B — Install from DMG", styles),
        bullet_list([
            "Double-click <b>CBMS-v1.0.0.dmg</b>.",
            "Drag <b>CBMS</b> to the <b>Applications</b> folder.",
            "Eject the disk image.",
            "Right-click CBMS in Applications → <b>Open</b> → click <b>Open</b> "
            "when macOS warns about an unsigned app.",
        ], styles),
        tip("After the first successful open, the app launches normally by double-clicking.", styles),
        sp(),

        h2("Windows", styles),
        body("Requirements: Windows 10 or later, Python 3.10+ (only needed to build).", styles),
        sp(0.5),
        h3("Option A — Run the installer script", styles),
        bullet_list([
            "Double-click <b>install_and_build.bat</b>.",
            "The script installs all dependencies and produces <b>dist\\CBMS.exe</b>.",
            "Copy <b>CBMS.exe</b> to any location and double-click to run.",
        ], styles),
        h3("Option B — Run without building", styles),
        code("venv\\Scripts\\activate\npython main.py", styles),
        sp(),

        h2("First Launch", styles),
        body("On first launch CBMS automatically creates the database at "
             "<b>data/cbms.db</b> and seeds a default administrator account:", styles),
        table(
            ["Field", "Default value"],
            [["Username", "admin"], ["Password", "Admin@1234"]],
            col_widths=[5*cm, 11.6*cm],
            styles=styles,
        ),
        sp(0.5),
        warn("Change the admin password immediately after first login via Admin → Users.", styles),
        PageBreak(),
    ]

    # ── 3. Login & Roles ──────────────────────────────────────────────────────
    story += [
        h1("3. Login & User Roles", styles), sp(),
        body("Enter your username and password at the login screen. "
             "Contact your system administrator if you need an account created.", styles),
        sp(),
        h2("Roles and permissions", styles),
        table(
            ["Role", "Who holds it", "Key permissions"],
            [
                ["PI",       "Principal Investigator",   "Full access — create studies, manage users, delete records, ship samples"],
                ["Manager",  "Study Coordinator",        "Register participants, import data, block/ship aliquots, manage users"],
                ["Lab Tech", "Bench Technician",         "Add samples, place aliquots in storage, unblock aliquots, run searches"],
            ],
            col_widths=[2.5*cm, 5.5*cm, 8.6*cm],
            styles=styles,
        ),
        sp(),
        note("Buttons requiring a higher permission are disabled (greyed out), not hidden. "
             "This lets all users see what operations exist.", styles),
        PageBreak(),
    ]

    # ── 4. Dashboard ─────────────────────────────────────────────────────────
    story += [
        h1("4. Dashboard", styles), sp(),
        body("The Dashboard opens on login and gives a real-time snapshot of the biorepository.", styles),
        sp(),
        h2("KPI strip", styles),
        body("Six numbers are displayed across the top:", styles),
        bullet_list([
            "<b>Participants</b> — total registered across all studies",
            "<b>Samples</b> — total sample records",
            "<b>Aliquots</b> — total aliquot tubes",
            "<b>Available</b> — aliquots currently available for use",
            "<b>Blocked</b> — aliquots reserved for a researcher",
            "<b>Shipped</b> — aliquots included in completed shipments",
        ], styles),
        sp(),
        h2("Cohort flowchart", styles),
        body("Below the KPI strip is a cohort workflow table. Use the <b>Cohort</b> "
             "dropdown (top-right of the flowchart area) to select a specific cohort. "
             "The table shows participant counts and vial counts per visit and sample type.", styles),
        PageBreak(),
    ]

    # ── 5. Studies Tab ────────────────────────────────────────────────────────
    story += [
        h1("5. Studies Tab", styles), sp(),
        body("A Study (or Project) is the top-level container. All participants, "
             "samples, and visit definitions belong to a study.", styles),
        sp(),
        h2("Creating a study", styles),
        bullet_list([
            "Click <b>＋ New Study</b>.",
            "Enter the <b>Project ID</b> (short code, e.g. COH) — this prefixes all sample IDs.",
            "Enter the <b>Project Name</b> and optional description.",
            "Click <b>Save</b>.",
        ], styles),
        tip("The Project ID cannot be changed after creation. Choose it carefully.", styles),
        sp(),
        h2("Visit definitions", styles),
        body("Each study has visit definitions (Screening, Enrollment, Follow-up). "
             "These must exist before importing samples via Excel.", styles),
        PageBreak(),
    ]

    # ── 6. Participants Tab ───────────────────────────────────────────────────
    story += [
        h1("6. Participants Tab", styles), sp(),
        body("The Participants tab lists all registered participants with search and filter controls.", styles),
        sp(),
        h2("Registering a participant manually", styles),
        bullet_list([
            "Select a study from the <b>Study</b> dropdown.",
            "Click <b>＋ Register Participant</b>.",
            "Fill in PID, Age, Gender, Population, Disease, Site, Cohort Name.",
            "Click <b>Save</b>.",
        ], styles),
        sp(),
        h2("Importing participants from Excel", styles),
        body("Use the Excel bulk import to load hundreds of rows at once.", styles),
        bullet_list([
            "Click <b>📥 Import from Excel</b>.",
            "Select the study to import into.",
            "Choose your <b>.xlsx</b> file (must follow the 21-column format — see Section 13).",
            "Review the validation summary. Fix any flagged rows before proceeding.",
            "Click <b>Import</b> to commit all rows in one transaction.",
        ], styles),
        warn("If any row fails validation the entire import is cancelled. No partial imports are written.", styles),
        sp(),
        h2("Searching and filtering", styles),
        bullet_list([
            "Use the <b>Study</b> dropdown to filter by study.",
            "Type in the <b>PID</b> search box for partial matches.",
            "Results are paginated (100 per page) — use <b>◀ Prev / Next ▶</b> to navigate.",
        ], styles),
        sp(),
        h2("Exporting participants", styles),
        body("Click <b>📤 Export to Excel</b> to save all filtered participants "
             "(all pages, not just the visible page) to an <b>.xlsx</b> file.", styles),
        PageBreak(),
    ]

    # ── 7. Samples Tab ────────────────────────────────────────────────────────
    story += [
        h1("7. Samples Tab", styles), sp(),
        body("The Samples tab shows samples and aliquots for selected participant(s).", styles),
        sp(),
        h2("Selecting participants", styles),
        bullet_list([
            "Choose a <b>Study</b> from the top dropdown.",
            "The participant list loads sorted alphabetically (A→Z).",
            "Type in <b>Search PID…</b> to filter the list in real time.",
            "Check one or more participant checkboxes — their samples merge into the right panel.",
            "Use <b>Select All</b> / <b>Clear All</b> for quick batch selection.",
        ], styles),
        sp(),
        h2("Visit filter", styles),
        body("Click a visit code in the left <b>Visits</b> list to filter samples to that visit. "
             "Click <b>All Visits</b> to reset.", styles),
        sp(),
        h2("Adding a sample", styles),
        bullet_list([
            "Select exactly <b>one</b> participant checkbox.",
            "Click <b>＋ Add Sample</b>.",
            "Choose Sample Type, Visit, Date Collected, and optional discrepancy notes.",
            "Click <b>Save</b>.",
        ], styles),
        sp(),
        h2("Adding aliquots to a sample", styles),
        bullet_list([
            "Select a sample row in the right panel.",
            "Click <b>＋ Add Aliquots</b>.",
            "Specify quantity and volume (µL) per aliquot.",
            "Click <b>Save</b>.",
        ], styles),
        sp(),
        h2("Aliquot status colours", styles),
        table(
            ["Colour", "Status", "Meaning"],
            [
                ["Green",  "Available", "Ready for use or shipment"],
                ["Orange", "Blocked",   "Reserved for a researcher"],
                ["Blue",   "Shipped",   "Included in a completed shipment"],
            ],
            col_widths=[2.5*cm, 3.5*cm, 10.6*cm],
            styles=styles,
        ),
        PageBreak(),
    ]

    # ── 8. Storage Tab ────────────────────────────────────────────────────────
    story += [
        h1("8. Storage Tab", styles), sp(),
        body("The Storage tab provides a visual map of every freezer, shelf, rack, "
             "drawer, and box. Click a box node in the left tree to see its 10×10 "
             "position grid on the right.", styles),
        sp(),
        h2("Storage hierarchy", styles),
        table(
            ["Level", "Examples", "Notes"],
            [
                ["Freezer / Tank", "NARI/COHRPICA/18-19/01 REGULAR", "Upright or cylindrical"],
                ["Compartment",    "I, II, III, IV (Shelf)",          "Upright freezers only"],
                ["Rack",           "A, B, C, D, E, F",               "Upright freezers only"],
                ["Drawer",         "01, 02, 03, 04, 05",             "Upright freezers only"],
                ["Box",            "Container name from Excel col O", "Holds 10×10 = 100 positions"],
                ["Position",       "A1 – J10",                       "Individual tube slot"],
            ],
            col_widths=[3.5*cm, 5.5*cm, 7.6*cm],
            styles=styles,
        ),
        sp(),
        h2("Box grid colours", styles),
        table(
            ["Colour", "Meaning"],
            [
                ["White",  "Empty — no aliquot placed"],
                ["Blue",   "Occupied — aliquot present"],
                ["Orange", "Blocked — aliquot reserved"],
                ["Grey",   "Shipped — aliquot sent; position locked"],
                ["Green",  "Selected — currently clicked cell"],
            ],
            col_widths=[3*cm, 13.6*cm],
            styles=styles,
        ),
        sp(),
        h2("Placing an aliquot", styles),
        bullet_list([
            "Select a box in the hierarchy tree.",
            "Click an empty (white) cell in the grid.",
            "Click <b>📍 Place Aliquot</b>.",
            "Search for the aliquot by ID and confirm.",
        ], styles),
        sp(),
        h2("Moving an aliquot", styles),
        bullet_list([
            "Click the occupied cell.",
            "Click <b>↔ Move</b> or drag the cell to a new empty position.",
        ], styles),
        tip("Shipped (grey) cells are locked — Move and Remove are disabled.", styles),
        PageBreak(),
    ]

    # ── 9. Search Tab ─────────────────────────────────────────────────────────
    story += [
        h1("9. Search Tab", styles), sp(),
        body("The Search tab lets you find aliquots using any combination of participant, "
             "sample, and storage criteria. Use <b>Ctrl+F</b> to open it instantly.", styles),
        sp(),
        h2("Filter fields (left panel)", styles),
        table(
            ["Filter", "Match type"],
            [
                ["PID",           "Partial text match"],
                ["Population",    "Partial text match"],
                ["Age",           "Exact integer"],
                ["Site",          "Partial text match"],
                ["Visit Time",    "Partial text match (e.g. M0, SCR)"],
                ["Visit Code",    "Partial text match (e.g. 1.0)"],
                ["Cohort",        "Partial text match"],
                ["Disease",       "Partial text match"],
                ["Sample Type",   "Partial text match"],
            ],
            col_widths=[4*cm, 12.6*cm],
            styles=styles,
        ),
        sp(),
        body("Use the <b>AND / OR</b> toggle to combine filters. Results are paginated at 100 per page.", styles),
        sp(),
        h2("Actions on results", styles),
        table(
            ["Button", "Description", "Who can use"],
            [
                ["Show in box",       "Switch to Storage tab and highlight the aliquot's position", "All"],
                ["Block selected…",   "Reserve aliquots for a researcher until a date",             "Manager / PI"],
                ["Unblock selected…", "Release a block with a mandatory reason",                    "All roles"],
                ["Ship selected…",    "Add aliquots to a new or existing shipment",                 "Manager / PI"],
                ["Export to Excel",   "Download current search results as .xlsx",                  "All"],
            ],
            col_widths=[3.5*cm, 8.5*cm, 4.6*cm],
            styles=styles,
        ),
        tip("Double-click any row to jump directly to the aliquot's position in the Storage tab.", styles),
        PageBreak(),
    ]

    # ── 10. Shipments Tab ────────────────────────────────────────────────────
    story += [
        h1("10. Shipments Tab", styles), sp(),
        body("The Shipments tab records aliquots sent to external researchers. "
             "Once shipped, an aliquot's box cell turns grey and the aliquot "
             "cannot be moved or removed.", styles),
        sp(),
        h2("Creating a shipment", styles),
        bullet_list([
            "Go to the <b>Search</b> tab and search for the aliquots to ship.",
            "Select the rows (hold Ctrl or Shift for multiple).",
            "Click <b>Ship selected…</b>.",
            "Fill in researcher name, institution, and shipment date.",
            "Click <b>Ship</b> — a unique shipment reference (SHIP-YYYYMMDD-NNN) is generated.",
        ], styles),
        sp(),
        h2("Viewing shipment history", styles),
        body("Open the <b>Shipments</b> tab to see all shipments. "
             "Click a shipment row to see the list of aliquots it contained.", styles),
        PageBreak(),
    ]

    # ── 11. Catalogue Tab ────────────────────────────────────────────────────
    story += [
        h1("11. Catalogue Tab", styles), sp(),
        body("The Catalogue tab generates a pivot table showing how many aliquots "
             "of each sample type each participant has.", styles),
        sp(),
        h2("Generating the catalogue", styles),
        bullet_list([
            "Select a <b>Study</b> (or leave at 'All studies').",
            "Optionally check <b>Available aliquots only</b> to exclude shipped/blocked.",
            "Click <b>Generate Catalogue</b>.",
        ], styles),
        sp(),
        h2("Narrowing results", styles),
        body("Use the <b>Narrow results</b> filters (PID, Gender, Disease, Cohort, Site, "
             "Sample Type) to slice the pivot table without regenerating it.", styles),
        sp(),
        h2("Exporting", styles),
        body("Click <b>Export to Excel…</b> to save the current pivot view to an .xlsx file.", styles),
        PageBreak(),
    ]

    # ── 12. Admin Tab ─────────────────────────────────────────────────────────
    story += [
        h1("12. Admin Tab", styles), sp(),
        body("The Admin tab is restricted to PI and Manager roles. It has three sub-tabs.", styles),
        sp(),

        h2("Users", styles),
        bullet_list([
            "<b>Add user</b> — click ＋ Add User, enter username, role, email, and temporary password.",
            "<b>Edit user</b> — select a row and click ✎ Edit to change name, email, or role.",
            "<b>Reset password</b> — select a user and click 🔑 Reset Password.",
            "<b>Deactivate</b> — select a user and click 🗑 Deactivate (does not delete records).",
        ], styles),
        warn("A user cannot change their own role. Role changes must be made by another PI or Manager.", styles),
        sp(),

        h2("Audit Trail", styles),
        body("Every significant action is logged. The audit trail is immutable — entries cannot be edited or deleted.", styles),
        bullet_list([
            "Filter by <b>Action</b> type (CREATE, UPDATE, DELETE, LOGIN, SHIP, BLOCK, UNBLOCK…).",
            "Filter by <b>Entity type</b> and <b>date range</b>.",
            "Click <b>Search</b> to refresh results (100 per page).",
            "Click column headers to sort.",
        ], styles),
        sp(),

        h2("Backup", styles),
        body("The current backup timestamp is shown at the top of the Admin tab and in the status bar at the bottom of the window.", styles),
        bullet_list([
            "Click <b>💾 Backup Now</b> (in the Admin tab header) or press <b>Ctrl+B</b> from anywhere.",
            "A timestamped copy is saved to <b>data/backups/cbms_YYYYMMDD_HHMMSS.db</b>.",
        ], styles),
        tip("Take a backup before every Excel import and before any major data change.", styles),
        PageBreak(),
    ]

    # ── 13. Excel Import Reference ───────────────────────────────────────────
    story += [
        h1("13. Excel Import Reference", styles), sp(),
        body("The Excel file must contain exactly 21 columns in this order. "
             "The header row is validated (case-insensitive, minor typos accepted).", styles),
        sp(),
        table(
            ["Col", "Header", "Required", "Notes"],
            [
                ["A", "PID",               "Yes", "Participant ID string"],
                ["B", "Age",               "No",  "Integer"],
                ["C", "Gender",            "No",  "Male / Female / Transgender"],
                ["D", "Population",        "No",  "FSW, MSM, PWID, General Adult, Child only, Pair-Child, Pair-Mother"],
                ["E", "Disease",           "No",  "None, Diabetes, TB, Risk of CVD, Infected without co-morbidity, Unknown-Screen failure, NA"],
                ["F", "Visit Code",        "No",  "Decimal (e.g. 1.0)"],
                ["G", "Visit Time",        "No",  "SCR, M0 – M36"],
                ["H", "Date Collected",    "No",  "Any parseable date format"],
                ["I", "Site Name",         "No",  "GHTM, ICMR-NARI (or NARI), NIMHANS, NIRT, YRG-Care"],
                ["J", "Visit Name",        "No",  "Screening, Enrollment, Follow-up"],
                ["K", "Sample Type",       "No",  "Serum, ED Plasma, HEP Plasma, EDTA PBMC"],
                ["L", "Cohort Name",       "No",  "HIV UNINFECTED, HIV INFECTED-ADULT, HIV INFECTED-PEDIATRIC, EARLY HIV INFECTED"],
                ["M", "Aliquot ID",        "No",  "Auto-generated if blank"],
                ["N", "Freezer / Tank",    "Cond","Required if any storage column is filled"],
                ["O", "Container",         "Cond","Box name"],
                ["P", "Slot Position",     "Cond","1–100 sequential position in box"],
                ["Q", "Shelf",             "Cond","I / II / III / IV (upright); '.' for cylindrical"],
                ["R", "Rack",              "Cond","A-01 format (upright); 1–13 (cylindrical)"],
                ["S", "Position",          "N/A", "Auto-computed from Slot Position; use '.'"],
                ["T", "Discrepancy Remark","No",  "Free text or '.'"],
                ["U", "Discrepancy For",   "No",  "Free text or '.'"],
            ],
            col_widths=[0.8*cm, 3.2*cm, 1.8*cm, 10.8*cm],
            styles=styles,
        ),
        sp(),
        warn("If any storage column (N–S) is non-empty, all of N, O, P, Q, R must be filled. "
             "Partial storage paths are a validation error.", styles),
        PageBreak(),
    ]

    # ── 14. Backup & Recovery ─────────────────────────────────────────────────
    story += [
        h1("14. Backup & Recovery", styles), sp(),
        h2("Taking a backup", styles),
        bullet_list([
            "Press <b>Ctrl+B</b> from anywhere in the app, or",
            "Open <b>Admin</b> tab and click <b>💾 Backup Now</b>.",
            "The backup is saved to <b>data/backups/</b>.",
            "The status bar (bottom-right) and Admin tab header show the last backup time.",
        ], styles),
        sp(),
        h2("Restoring from backup", styles),
        bullet_list([
            "Close CBMS.",
            "Navigate to <b>data/backups/</b> and find the desired <b>.db</b> file.",
            "Copy it to <b>data/cbms.db</b> (overwriting the current database).",
            "Relaunch CBMS.",
        ], styles),
        warn("Restoring a backup permanently replaces the current database. "
             "Take a backup of the current state first if in doubt.", styles),
        sp(),
        h2("Backup file location", styles),
        code("data/\n  cbms.db              ← live database\n  backups/\n    cbms_20260514_143022.db\n    cbms_20260513_090011.db\n    ...", styles),
        PageBreak(),
    ]

    # ── 15. Keyboard Shortcuts ───────────────────────────────────────────────
    story += [
        h1("15. Keyboard Shortcuts", styles), sp(),
        table(
            ["Shortcut", "Action"],
            [
                ["Ctrl+1",       "Dashboard"],
                ["Ctrl+2",       "Studies"],
                ["Ctrl+3",       "Participants"],
                ["Ctrl+4",       "Samples"],
                ["Ctrl+5",       "Storage"],
                ["Ctrl+F",       "Search"],
                ["Ctrl+6",       "Shipments"],
                ["Ctrl+7",       "Catalogue"],
                ["Ctrl+8",       "Admin"],
                ["Ctrl+N",       "New participant (from any tab)"],
                ["Ctrl+Shift+N", "New study"],
                ["Ctrl+B",       "Backup now"],
            ],
            col_widths=[4.5*cm, 12.1*cm],
            styles=styles,
        ),
        PageBreak(),
    ]

    # ── 16. Troubleshooting ───────────────────────────────────────────────────
    story += [
        h1("16. Troubleshooting", styles), sp(),
        table(
            ["Problem", "Solution"],
            [
                ["App won't open on macOS (unsigned warning)",
                 "Right-click CBMS.app → Open → click Open. Or run:\n"
                 "xattr -d com.apple.quarantine /Applications/CBMS.app"],
                ["Excel import fails — header mismatch",
                 "Check that your file has exactly 21 columns in the correct order. "
                 "Minor spelling variants (e.g. 'Descripancy') are accepted."],
                ["Excel import fails — validation errors",
                 "The error list shows the row number and field. Fix those rows "
                 "in Excel and retry."],
                ["Search by cohort returns no results",
                 "Ensure the Cohort filter text matches the stored value "
                 "(e.g. 'HIV UNINFECTED'). The filter is a partial case-insensitive match."],
                ["Box grid shows no aliquots after import",
                 "Check that the Slot Position column (P) contains a number 1–100 "
                 "and that all storage columns (N–R) are filled."],
                ["'No storage location' when double-clicking Search result",
                 "The aliquot was imported without storage coordinates or was "
                 "removed from its position."],
                ["Forgot admin password",
                 "Close the app, delete data/cbms.db, and relaunch — "
                 "the default admin/Admin@1234 will be restored. "
                 "Warning: this also deletes all data. Restore from backup instead if possible."],
            ],
            col_widths=[5.5*cm, 11.1*cm],
            styles=styles,
        ),
    ]

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
    print(f"[CBMS] Manual written to: {output_path}")


if __name__ == "__main__":
    build_manual("CBMS_User_Manual.pdf")
