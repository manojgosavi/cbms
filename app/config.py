"""
CBMS — Central Biorepository Management Software
Global configuration and constants.
"""

from pathlib import Path
from enum import Enum
import sys

# ── Paths ──────────────────────────────────────────────────────────────────
# For development: __file__ points to config.py in app/
# For PyInstaller bundle: __file__ points to config.pyc in the bundle
BASE_DIR = Path(__file__).resolve().parent.parent          # project root or app directory

# For bundled apps, ensure data folder is in a writable location
# Try to create data in BASE_DIR first, fall back to user home if not writable
def _get_data_dir() -> Path:
    preferred = BASE_DIR / "data"
    # Check if BASE_DIR is writable
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        # Test if we can actually write to it
        test_file = preferred / ".write_test"
        test_file.touch()
        test_file.unlink()
        return preferred
    except (OSError, PermissionError):
        # Fall back to user home directory
        home_data = Path.home() / ".cbms" / "data"
        home_data.mkdir(parents=True, exist_ok=True)
        return home_data

DATA_DIR = _get_data_dir()
DB_PATH  = DATA_DIR / "cbms.db"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR    = DATA_DIR / "logs"

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# ── Application meta ───────────────────────────────────────────────────────
APP_NAME    = "CBMS"
APP_VERSION = "0.1.0"
APP_TITLE   = "Central Biorepository Management Software"

# ── Sample ID format ───────────────────────────────────────────────────────
# Pattern: <PROJECT_SHORT>-<YY>-<SERIAL>   e.g. COH-26-1
SAMPLE_ID_SEPARATOR = "-"

# ── Dropdown Enums (for validation and UI dropdowns) ─────────────────────
class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    TRANSGENDER = "Transgender"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class Population(str, Enum):
    FSW = "FSW"
    MSM = "MSM"
    PWID = "PWID"
    GENERAL_ADULT = "General Adult"
    CHILD_ONLY = "Child only"
    PAIR_CHILD = "Pair-Child"
    PAIR_MOTHER = "Pair-Mother"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class Disease(str, Enum):
    DIABETES = "Diabetes"
    INFECTED_NO_COMORBIDITY = "Infected without co-morbidity"
    NONE = "None"
    NA = "NA"
    TB = "TB"
    RISK_CVD = "Risk of CVD"
    UNKNOWN_SCREEN_FAILURE = "Unknown-Screen failure"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class Site(str, Enum):
    GHTM = "GHTM"
    ICMAR_NARI = "ICMR-NARI"
    NIMHANS = "NIMHANS"
    NIRT = "NIRT"
    YRG_CARE = "YRG-Care"
    ICMR_NIRT = "ICMR-NIRT"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class VisitName(str, Enum):
    SCREENING = "Screening"
    ENROLLMENT = "Enrollment"
    FOLLOW_UP = "Follow-up"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class SampleType(str, Enum):
    SERUM = "Serum"
    ED_PLASMA = "ED Plasma"
    HEP_PLASMA = "HEP Plasma"
    PBMC = "EDTA PBMC"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None


class CohortName(str, Enum):
    HIV_UNINFECTED = "HIV UNINFECTED"
    HIV_INFECTED_ADULT = "HIV INFECTED-ADULT"
    HIV_INFECTED_PEDIATRIC = "HIV INFECTED-PEDIATRIC"
    EARLY_HIV_INFECTED = "EARLY HIV INFECTED"

    @classmethod
    def _missing_(cls, value):
        normalized = str(value).lower().strip()
        for member in cls:
            if member.value.lower().strip() == normalized:
                return member
        return None




# ── RBAC roles ────────────────────────────────────────────────────────────
class Role:
    PI      = "PI"
    MANAGER = "MANAGER"
    LAB_TECH = "LAB_TECH"

    ALL = [PI, MANAGER, LAB_TECH]

    # Permissions map  role → frozenset of allowed actions
    PERMISSIONS: dict[str, frozenset] = {
        PI: frozenset([
            "study.create", "study.edit", "study.delete",
            "participant.create", "participant.edit", "participant.delete",
            "sample.create", "sample.edit", "sample.delete",
            "storage.create", "storage.edit", "storage.delete",
            "shipment.create", "shipment.edit",
            "admin.users", "admin.audit", "admin.backup",
            "report.view", "report.export",
        ]),
        MANAGER: frozenset([
            "study.create", "study.edit",
            "participant.create", "participant.edit", "participant.delete",
            "sample.create", "sample.edit", "sample.delete",
            "storage.create", "storage.edit", "storage.delete",
            "shipment.create", "shipment.edit",
            "admin.users", "admin.audit", "admin.backup",
            "report.view", "report.export",
        ]),
        LAB_TECH: frozenset([
            "participant.create", "participant.edit",
            "sample.create", "sample.edit",
            "storage.edit",
            "report.view", "report.export",
        ]),
    }

    @classmethod
    def can(cls, role: str, action: str) -> bool:
        return action in cls.PERMISSIONS.get(role, frozenset())


# ── UI constants ───────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH  = 1280
WINDOW_MIN_HEIGHT = 800

# Box grid sizes supported
BOX_GRID_SIZES = [
    (9, 9),
    (10, 10),
    (8, 12),
    (6, 6),
]

# ── Audit actions ──────────────────────────────────────────────────────────
class AuditAction:
    CREATE  = "CREATE"
    UPDATE  = "UPDATE"
    DELETE  = "DELETE"
    LOGIN   = "LOGIN"
    LOGOUT  = "LOGOUT"
    EXPORT  = "EXPORT"
    SHIP    = "SHIP"
    BLOCK   = "BLOCK"
    UNBLOCK = "UNBLOCK"
    MOVE    = "MOVE"
