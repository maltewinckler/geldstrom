"""FinTS Enumeration Types.

These enums define the valid codes used in FinTS protocol messages.
Each enum corresponds to a specific code field in the FinTS specification.
"""
from __future__ import annotations

from enum import Enum


class SecurityMethod(str, Enum):
    """Sicherheitsverfahren (Security Method).

    Source: FinTS 3.0 Formals, Sicherheitsverfahren
    """
    DDV = "DDV"   # DDV (Chip card)
    RAH = "RAH"   # RAH (RSA/AES Hybrid)
    RDH = "RDH"   # RDH (RSA/DES Hybrid)
    PIN = "PIN"   # PIN/TAN


class IdentifiedRole(str, Enum):
    """Rolle des Identifizierten (Identified Role).

    Source: FinTS 3.0 Formals
    """
    MS = "1"  # Message Sender
    MR = "2"  # Message Receiver


class DateTimeType(str, Enum):
    """Datum/Uhrzeit-Typ (Date/Time Type).

    Source: FinTS 3.0 Formals
    """
    STS = "1"  # Sicherheitszeitstempel (Security Timestamp)
    CRT = "6"  # Certificate Revocation Time


class SecurityRole(str, Enum):
    """Rolle des Sicherheitslieferanten (Security Role).

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """
    ISS = "1"  # Erfasser, Erstsignatur (Issuer, First Signature)
    CON = "3"  # Unterstützer, Zweitsignatur (Cosigner, Second Signature)
    WIT = "4"  # Zeuge/Übermittler (Witness/Transmitter)


class SecurityApplicationArea(str, Enum):
    """Bereich der Sicherheitsapplikation (Security Application Area).

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """
    SHM = "1"  # Signaturkopf und HBCI-Nutzdaten
    SHT = "2"  # Von Signaturkopf bis Signaturabschluss


class CompressionFunction(str, Enum):
    """Komprimierungsfunktion (Compression Function).

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """
    NULL = "0"    # Keine Kompression
    LZW = "1"     # Lempel, Ziv, Welch
    COM = "2"     # Optimized LZW
    LZSS = "3"    # Lempel, Ziv
    LZHuf = "4"   # LZ + Huffman Coding
    ZIP = "5"     # PKZIP
    GZIP = "6"    # deflate (gzip)
    BZIP2 = "7"   # bzip2
    ZZZ = "999"   # Gegenseitig vereinbart (Mutually agreed)


class KeyType(str, Enum):
    """Schlüsselart (Key Type).

    Source: FinTS 3.0 Formals
    """
    D = "D"  # Schlüssel zur Erzeugung digitaler Signaturen
    S = "S"  # Signierschlüssel (Signing Key)
    V = "V"  # Chiffrierschlüssel (Cipher Key)


class UsageEncryption(str, Enum):
    """Verwendungsmodus der Verschlüsselung (Encryption Usage).

    Source: FinTS 3.0 Formals
    """
    OSY = "2"  # Owner Symmetric


class OperationMode(str, Enum):
    """Operationsmodus (Operation Mode).

    Source: FinTS 3.0 Formals
    """
    CBC = "2"               # Cipher Block Chaining
    ISO_9796_1 = "16"       # ISO 9796-1 (bei RDH)
    ISO_9796_2_RANDOM = "17"  # ISO 9796-2 mit Zufallszahl
    PKCS1V15 = "18"         # RSASSA-PKCS#1 V1.5
    PSS = "19"              # RSASSA-PSS
    ZZZ = "999"             # Gegenseitig vereinbart (DDV: Retail-MAC)


class EncryptionAlgorithmCoded(str, Enum):
    """Verschlüsselungsalgorithmus kodiert (Encryption Algorithm).

    Source: FinTS 3.0 Formals
    """
    TWOKEY3DES = "13"  # 2-Key-Triple-DES
    AES256 = "14"      # AES-256


class AlgorithmParameterName(str, Enum):
    """Algorithmusparameter, Name (Algorithm Parameter Name).

    Source: FinTS 3.0 Formals
    """
    KYE = "5"  # Symmetrischer Schlüssel, verschlüsselt mit symmetrischem Schlüssel
    KYP = "6"  # Symmetrischer Schlüssel, verschlüsselt mit öffentlichem Schlüssel


class AlgorithmParameterIVName(str, Enum):
    """Algorithmusparameter IV, Name (Algorithm Parameter IV Name).

    Source: FinTS 3.0 Formals
    """
    IVC = "1"  # Initialization value, clear text


class CreditDebit(str, Enum):
    """Soll-Haben-Kennzeichen (Credit/Debit Indicator).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """
    CREDIT = "C"  # Haben (Credit)
    DEBIT = "D"   # Soll (Debit)


class SynchronizationMode(str, Enum):
    """Synchronisierungsmodus (Synchronization Mode).

    Source: FinTS 3.0 Formals
    """
    NEW_SYSTEM_ID = "0"   # Neue Kundensystem-ID zurückmelden
    LAST_MESSAGE = "1"    # Letzte verarbeitete Nachrichtennummer
    SIGNATURE_ID = "2"    # Signatur-ID zurückmelden


class SystemIDStatus(str, Enum):
    """Kundensystem-Status (System ID Status).

    Source: FinTS 3.0 Formals
    """
    ID_UNNECESSARY = "0"  # Kundensystem-ID wird nicht benötigt
    ID_NECESSARY = "1"    # Kundensystem-ID wird benötigt


class UPDUsage(str, Enum):
    """UPD-Verwendung (UPD Usage).

    Source: FinTS 3.0 Formals
    """
    UPD_CONCLUSIVE = "0"     # Nicht aufgeführte GV sind gesperrt
    UPD_INCONCLUSIVE = "1"   # Keine Aussage über nicht aufgeführte GV


class Language(str, Enum):
    """Dialogsprache (Dialog Language).

    Source: FinTS 3.0 Formals
    """
    DEFAULT = "0"  # Standard
    DE = "1"       # Deutsch
    EN = "2"       # Englisch
    FR = "3"       # Französisch


class ServiceType(int, Enum):
    """Kommunikationsdienst (Service Type).

    Source: FinTS 3.0 Formals
    """
    T_ONLINE = 1   # T-Online
    TCP_IP = 2     # TCP/IP (SLIP/PPP)
    HTTPS = 3      # HTTPS


class TANMediaType(str, Enum):
    """TAN-Medium-Art (TAN Media Type).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ALL = "0"       # Alle
    ACTIVE = "1"    # Aktiv
    AVAILABLE = "2" # Verfügbar


class TANMediaClass(str, Enum):
    """TAN-Medium-Klasse (TAN Media Class).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ALL = "A"       # Alle Medien
    LIST = "L"      # Liste
    GENERATOR = "G" # TAN-Generator
    MOBILE = "M"    # Mobiltelefon mit mobileTAN
    SECODER = "S"   # Secoder
    BILATERAL = "B" # Bilateral vereinbart


class TANMediumStatus(str, Enum):
    """TAN-Medium-Status.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ACTIVE = "1"              # Aktiv
    AVAILABLE = "2"           # Verfügbar
    ACTIVE_SUCCESSOR = "3"    # Aktiv Folgekarte
    AVAILABLE_SUCCESSOR = "4" # Verfügbar Folgekarte


class TANTimeDialogAssociation(str, Enum):
    """TAN Zeit- und Dialogbezug (TAN Time/Dialog Association).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    NOT_ALLOWED = "1"     # TAN nicht zeitversetzt/dialogübergreifend erlaubt
    ALLOWED = "2"         # TAN zeitversetzt/dialogübergreifend erlaubt
    BOTH = "3"            # Beide Verfahren unterstützt
    NOT_APPLICABLE = "4"  # Nicht zutreffend


class AllowedFormat(str, Enum):
    """Erlaubtes Format im Zwei-Schritt-Verfahren (Allowed Format).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    NUMERIC = "1"       # Numerisch
    ALPHANUMERIC = "2"  # Alphanumerisch


class StatementFormat(str, Enum):
    """Kontoauszugsformat (Statement Format).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """
    MT_940 = "1"   # S.W.I.F.T. MT940
    ISO_8583 = "2"  # ISO 8583
    PDF = "3"      # Printable format (e.g., PDF)


class Confirmation(str, Enum):
    """Quittierung (Confirmation).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """
    NOT_REQUIRED = "0"        # Nicht notwendig
    CONFIRMED = "1"           # Quittiert
    AWAITING_CONFIRMATION = "2"  # Quittierung offen


__all__ = [
    # Security
    "SecurityMethod",
    "IdentifiedRole",
    "DateTimeType",
    "SecurityRole",
    "SecurityApplicationArea",
    "CompressionFunction",
    "KeyType",
    # Encryption
    "UsageEncryption",
    "OperationMode",
    "EncryptionAlgorithmCoded",
    "AlgorithmParameterName",
    "AlgorithmParameterIVName",
    # Balance/Amount
    "CreditDebit",
    # System
    "SynchronizationMode",
    "SystemIDStatus",
    "UPDUsage",
    "Language",
    "ServiceType",
    # TAN
    "TANMediaType",
    "TANMediaClass",
    "TANMediumStatus",
    "TANTimeDialogAssociation",
    "AllowedFormat",
    # Statement
    "StatementFormat",
    "Confirmation",
]

