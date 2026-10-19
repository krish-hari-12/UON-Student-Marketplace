#!/usr/bin/env python3
"""
generate_diagrams.py
====================
Builds the four documentation figures for the final report:
  architecture.png  - layered (n-tier) system architecture
  er_diagram.png    - entity-relationship diagram of the database
  gantt.png         - project Gantt chart (baseline schedule)
  storyboard.png    - UI storyboard / wireframe of the user journey

Run from the docs/figs folder:  python generate_diagrams.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.dates as mdates
from datetime import date

NAVY, GREEN, GREY, LIGHT = "#14385f", "#009a44", "#6b7a8d", "#eef2f6"

# ======================================================================
# 1. Architecture diagram
# ======================================================================
def architecture():
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    layers = [
        ("Presentation layer", "HTML5 / CSS3 / JavaScript / Bootstrap 5 templates\n"
         "Student UI  ·  Admin UI  ·  responsive layouts  ·  forms", "#dce9f7"),
        ("Application layer", "Flask route blueprints: main · auth · listings · favourites\n"
         "messages · reports · admin      Security: sessions, RBAC, CSRF, validation", "#d7f0e2"),
        ("Data-access layer", "app/db.py query helpers (portable SQL)\n"
         "app/emailer.py notifications  ·  image upload service", "#fdf1d8"),
        ("Data-storage layer", "Relational database (SQLite default / MySQL optional)\n"
         "uploads/listings image storage", "#f7dcdd"),
    ]
    for i, (title, body, color) in enumerate(layers):
        y = 0.76 - i * 0.23
        box = FancyBboxPatch((0.08, y), 0.84, 0.16,
                             boxstyle="round,pad=0.01", fc=color, ec=NAVY, lw=1.4)
        ax.add_patch(box)
        ax.text(0.5, y + 0.105, title, ha="center", va="center",
                fontsize=12, fontweight="bold", color=NAVY)
        ax.text(0.5, y + 0.048, body, ha="center", va="center", fontsize=8.5, color="#333")
        if i < 3:
            ax.annotate("", xy=(0.5, y - 0.065), xytext=(0.5, y - 0.005),
                        arrowprops=dict(arrowstyle="-|>", lw=2, color=GREY))
    ax.text(0.5, 0.965, "UoN Student Marketplace - layered (n-tier) architecture",
            ha="center", fontsize=13, fontweight="bold", color=NAVY)
    ax.text(0.015, 0.84, "Browser\n(desktop /\ntablet / mobile)", fontsize=8, color=GREY, ha="left")
    ax.annotate("", xy=(0.075, 0.86), xytext=(0.001, 0.86),
                arrowprops=dict(arrowstyle="<|-|>", lw=1.6, color=GREY))
    plt.tight_layout()
    plt.savefig("architecture.png", dpi=150)
    plt.close()

# ======================================================================
# 2. ER diagram
# ======================================================================
ENTITIES = {
    "users": (["user_id PK", "email UQ", "password_hash", "first_name", "last_name",
               "phone", "role", "status", "created_at"], (0.02, 0.66)),
    "categories": (["category_id PK", "name UQ", "description", "is_archived"], (0.36, 0.86)),
    "listings": (["listing_id PK", "user_id FK", "category_id FK", "title", "description",
                  "price", "condition", "location", "status", "created_at", "updated_at"],
                 (0.68, 0.52)),
    "listing_images": (["image_id PK", "listing_id FK", "file_path", "is_primary",
                        "uploaded_at"], (0.36, 0.60)),
    "favourites": (["user_id PK FK", "listing_id PK FK", "created_at"], (0.36, 0.34)),
    "conversations": (["conversation_id PK", "listing_id FK", "buyer_id FK", "created_at"],
                      (0.02, 0.36)),
    "messages": (["message_id PK", "conversation_id FK", "sender_id FK", "body",
                  "sent_at", "is_read"], (0.02, 0.12)),
    "reports": (["report_id PK", "listing_id FK", "reporter_id FK", "reason", "details",
                 "status", "resolved_by FK", "resolved_at", "resolution_note", "created_at"],
                (0.36, 0.05)),
    "audit_log": (["audit_id PK", "admin_id FK", "action", "entity_type", "entity_id",
                   "details", "created_at"], (0.70, 0.12)),
    "email_log": (["email_id PK", "recipient", "subject", "body", "status", "sent_at"],
                  (0.70, 0.30)),
}
RELATIONS = [
    ("users", "listings", "1 .. *"), ("categories", "listings", "1 .. *"),
    ("listings", "listing_images", "1 .. *"), ("users", "favourites", "1 .. *"),
    ("listings", "favourites", "1 .. *"), ("users", "conversations", "1 .. *"),
    ("listings", "conversations", "1 .. *"), ("conversations", "messages", "1 .. *"),
    ("users", "messages", "1 .. *"), ("listings", "reports", "1 .. *"),
    ("users", "reports", "1 .. *"), ("users", "audit_log", "1 .. *"),
]

def er():
    fig, ax = plt.subplots(figsize=(13, 8.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    boxes = {}
    for name, (fields, (x, y)) in ENTITIES.items():
        w, h = 0.24, 0.028 * (len(fields) + 1)
        box = FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0.004",
                             fc="white", ec=NAVY, lw=1.3)
        ax.add_patch(box)
        ax.add_patch(plt.Rectangle((x, y - 0.028), w, 0.028, fc=NAVY, ec=NAVY))
        ax.text(x + w / 2, y - 0.0145, name, ha="center", va="center",
                fontsize=9, fontweight="bold", color="white", family="monospace")
        for i, f in enumerate(fields):
            ax.text(x + 0.012, y - 0.040 - i * 0.026, f, fontsize=7,
                    family="monospace", color="#222")
        boxes[name] = (x, y - h, w, h)
    for a, b, label in RELATIONS:
        xa, ya = boxes[a][0] + boxes[a][2] / 2, boxes[a][1] + boxes[a][3] / 2
        xb, yb = boxes[b][0] + boxes[b][2] / 2, boxes[b][1] + boxes[b][3] / 2
        ax.annotate("", xy=(xb, yb), xytext=(xa, ya),
                    arrowprops=dict(arrowstyle="-", lw=0.9, color=GREEN,
                                    connectionstyle="arc3,rad=0.08"))
    ax.set_title("UoN Student Marketplace - entity-relationship diagram",
                 fontsize=13, fontweight="bold", color=NAVY)
    plt.tight_layout()
    plt.savefig("er_diagram.png", dpi=150)
    plt.close()

# ======================================================================
# 3. Gantt chart (baseline schedule, 8 Sep - 13 Nov 2026)
# ======================================================================
TASKS = [
    ("1.1 Project Planning", (2026, 9, 7), (2026, 9, 11)),
    ("1.2 Requirements Analysis", (2026, 9, 8), (2026, 9, 22)),
    ("1.3 System Design", (2026, 9, 10), (2026, 9, 24)),
    ("1.6 Database Development", (2026, 9, 15), (2026, 10, 8)),
    ("1.4 Frontend Development", (2026, 9, 21), (2026, 10, 20)),
    ("1.5 Backend Development", (2026, 9, 21), (2026, 10, 20)),
    ("1.7 Administration & Moderation", (2026, 10, 8), (2026, 10, 24)),
    ("1.8 System Integration", (2026, 10, 15), (2026, 11, 2)),
    ("1.9 Testing & QA", (2026, 9, 22), (2026, 11, 9)),
    ("1.10 Documentation", (2026, 10, 20), (2026, 11, 10)),
    ("1.11 Finalisation & Delivery", (2026, 11, 3), (2026, 11, 13)),
    ("1.12 Project Monitoring & Control", (2026, 9, 7), (2026, 11, 13)),
]

def gantt():
    fig, ax = plt.subplots(figsize=(11, 5.6))
    for i, (name, s, e) in enumerate(TASKS):
        start = date(*s); end = date(*e)
        ax.barh(i, (end - start).days, left=mdates.date2num(start),
                height=0.55, color=NAVY if i % 2 == 0 else "#2a5a8f")
    ax.set_yticks(range(len(TASKS)))
    ax.set_yticklabels([t[0] for t in TASKS], fontsize=8.5)
    ax.invert_yaxis()
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    ax.grid(axis="x", color="#dddddd", lw=0.6)
    ax.axvline(mdates.date2num(date(2026, 9, 28)), color=GREEN, lw=2, linestyle="--")
    ax.text(mdates.date2num(date(2026, 9, 28)), len(TASKS) - 0.2,
            " status snapshot\n 28 Sep 2026", color=GREEN, fontsize=8, fontweight="bold")
    ax.set_title("UoN Student Marketplace - project Gantt chart (baseline, updated weekly)",
                 fontsize=12, fontweight="bold", color=NAVY)
    plt.tight_layout()
    plt.savefig("gantt.png", dpi=150)
    plt.close()

# ======================================================================
# 4. Storyboard (six wireframe panels)
# ======================================================================
def panel(ax, x, y, title, lines, highlight=None):
    w, h = 0.28, 0.42
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004",
                                fc="white", ec=NAVY, lw=1.4))
    ax.add_patch(plt.Rectangle((x, y + h - 0.035), w, 0.035, fc=NAVY))
    ax.text(x + w / 2, y + h - 0.0175, title, ha="center", va="center",
            fontsize=7.5, color="white", fontweight="bold")
    yy = y + h - 0.075
    for kind, text in lines:
        if kind == "btn":
            ax.add_patch(FancyBboxPatch((x + 0.02, yy - 0.022), 0.12, 0.026,
                         boxstyle="round,pad=0.002", fc=GREEN, ec="none"))
            ax.text(x + 0.08, yy - 0.009, text, ha="center", va="center",
                    fontsize=5.5, color="white", fontweight="bold")
        elif kind == "card":
            ax.add_patch(plt.Rectangle((x + 0.02, yy - 0.045), w - 0.04, 0.05,
                         fc=LIGHT, ec="#c8d2dc"))
            ax.text(x + 0.03, yy - 0.02, text, fontsize=5, color="#333")
        elif kind == "field":
            ax.add_patch(plt.Rectangle((x + 0.02, yy - 0.028), w - 0.04, 0.028,
                         fc="white", ec="#9aa7b3"))
            ax.text(x + 0.03, yy - 0.014, text, fontsize=5, color="#666")
        else:
            ax.text(x + 0.02, yy - 0.012, text, fontsize=6, color="#333",
                    fontweight="bold")
        yy -= {"h2": 0.045, "card": 0.06, "btn": 0.04, "field": 0.038}.get(kind, 0.03)

def storyboard():
    fig, ax = plt.subplots(figsize=(14, 7.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.set_title("UoN Student Marketplace - storyboard of the user journey",
                 fontsize=13, fontweight="bold", color=NAVY)
    panel(ax, 0.02, 0.52, "1. Home / Marketplace",
          [("h2", "Search bar + categories"),
           ("field", "Search listings..."),
           ("card", "[textbook] [desk] [laptop]"),
           ("card", "[bike] [fridge] [monitor]"),
           ("btn", "Browse all")])
    panel(ax, 0.37, 0.52, "2. Browse & filter results",
          [("h2", "Filters: category, price, condition"),
           ("card", "HP laptop - $620 - Like new"),
           ("card", "Study desk - $45 - Fair"),
           ("card", "STAT1070 textbook - $35"),
           ("btn", "Open listing")])
    panel(ax, 0.72, 0.52, "3. Listing detail",
          [("h2", "Photos, price, seller, condition"),
           ("card", "photo gallery + description"),
           ("btn", "Contact seller"),
           ("btn", "Save to favourites"),
           ("btn", "Report listing")])
    panel(ax, 0.02, 0.04, "4. Message thread",
          [("h2", "Buyer-seller chat (BR-05)"),
           ("card", "buyer: is it available?"),
           ("card", "seller: yes, Saturday ok?"),
           ("field", "Type a message..."),
           ("btn", "Send")])
    panel(ax, 0.37, 0.04, "5. Post an ad (form)",
          [("h2", "Title, price, category..."),
           ("field", "Title *"),
           ("field", "Price $ / Category *"),
           ("field", "Description * + photos"),
           ("btn", "Publish listing")])
    panel(ax, 0.72, 0.04, "6. Admin dashboard",
          [("h2", "Reports & moderation (BR-07)"),
           ("card", "open reports / users / ads"),
           ("btn", "Review report"),
           ("btn", "Remove listing"),
           ("btn", "Manage categories")])
    for x1, y1, x2, y2 in [(0.30, 0.73, 0.37, 0.73), (0.65, 0.73, 0.72, 0.73),
                           (0.86, 0.52, 0.86, 0.46), (0.72, 0.25, 0.65, 0.25),
                           (0.37, 0.25, 0.30, 0.25)]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1.8, color=GREEN))
    plt.tight_layout()
    plt.savefig("storyboard.png", dpi=150)
    plt.close()

if __name__ == "__main__":
    architecture(); er(); gantt(); storyboard()
    print("diagrams generated")
