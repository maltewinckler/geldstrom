"""FinTS Enumeration Types.

These enums define the valid codes used in FinTS protocol messages.
Each enum corresponds to a specific code field in the FinTS specification.

All enums inherit from FinTSEnum which ensures __str__ returns the value,
matching the behavior of legacy RepresentableEnum. This is required for
compatibility with legacy FinTS field parsing which relies on str(enum)
returning the raw protocol value.
"""
from __future__ import annotations

from enum import Enum


class FinTSEnum(str, Enum):
    """Base class for FinTS string enums that returns value from __str__.

    This ensures compatibility with legacy field parsing which expects
    str(enum) to return the protocol value, not the enum name.

    Example:
        >>> str(SynchronizationMode.NEW_SYSTEM_ID)
        '0'  # Returns value, not 'SynchronizationMode.NEW_SYSTEM_ID'
    """

    def __str__(self) -> str:
        """Return the enum value as string."""
        return str(self.value)


class FinTSIntEnum(int, Enum):
    """Base class for FinTS integer enums that returns value from __str__.

    Example:
        >>> str(ServiceType.HTTPS)
        '3'  # Returns value, not 'ServiceType.HTTPS'
    """

    def __str__(self) -> str:
        """Return the enum value as string."""
        return str(self.value)


class SecurityMethod(FinTSEnum):
    """Sicherheitsverfahren (Security Method).

    Source: FinTS 3.0 Formals, Sicherheitsverfahren
    """
    DDV = "DDV"   # DDV (Chip card)
    RAH = "RAH"   # RAH (RSA/AES Hybrid)
    RDH = "RDH"   # RDH (RSA/DES Hybrid)
    PIN = "PIN"   # PIN/TAN


class IdentifiedRole(FinTSEnum):
    """Rolle des Identifizierten (Identified Role).

    Source: FinTS 3.0 Formals
    """
    MS = "1"  # Message Sender
    MR = "2"  # Message Receiver


class DateTimeType(FinTSEnum):
    """Datum/Uhrzeit-Typ (Date/Time Type).

    Source: FinTS 3.0 Formals
    """
    STS = "1"  # Sicherheitszeitstempel (Security Timestamp)
    CRT = "6"  # Certificate Revocation Time


class SecurityRole(FinTSEnum):
    """Rolle des Sicherheitslieferanten (Security Role).

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """
    ISS = "1"  # Erfasser, Erstsignatur (Issuer, First Signature)
    CON = "3"  # Unterstützer, Zweitsignatur (Cosigner, Second Signature)
    WIT = "4"  # Zeuge/Übermittler (Witness/Transmitter)


class SecurityApplicationArea(FinTSEnum):
    """Bereich der Sicherheitsapplikation (Security Application Area).

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """
    SHM = "1"  # Signaturkopf und HBCI-Nutzdaten
    SHT = "2"  # Von Signaturkopf bis Signaturabschluss


class CompressionFunction(FinTSEnum):
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


class KeyType(FinTSEnum):
    """Schlüsselart (Key Type).

    Source: FinTS 3.0 Formals
    """
    D = "D"  # Schlüssel zur Erzeugung digitaler Signaturen
    S = "S"  # Signierschlüssel (Signing Key)
    V = "V"  # Chiffrierschlüssel (Cipher Key)


class UsageEncryption(FinTSEnum):
    """Verwendungsmodus der Verschlüsselung (Encryption Usage).

    Source: FinTS 3.0 Formals
    """
    OSY = "2"  # Owner Symmetric


class OperationMode(FinTSEnum):
    """Operationsmodus (Operation Mode).

    Source: FinTS 3.0 Formals
    """
    CBC = "2"               # Cipher Block Chaining
    ISO_9796_1 = "16"       # ISO 9796-1 (bei RDH)
    ISO_9796_2_RANDOM = "17"  # ISO 9796-2 mit Zufallszahl
    PKCS1V15 = "18"         # RSASSA-PKCS#1 V1.5
    PSS = "19"              # RSASSA-PSS
    ZZZ = "999"             # Gegenseitig vereinbart (DDV: Retail-MAC)


class EncryptionAlgorithmCoded(FinTSEnum):
    """Verschlüsselungsalgorithmus kodiert (Encryption Algorithm).

    Source: FinTS 3.0 Formals
    """
    TWOKEY3DES = "13"  # 2-Key-Triple-DES
    AES256 = "14"      # AES-256


class AlgorithmParameterName(FinTSEnum):
    """Algorithmusparameter, Name (Algorithm Parameter Name).

    Source: FinTS 3.0 Formals
    """
    KYE = "5"  # Symmetrischer Schlüssel, verschlüsselt mit symmetrischem Schlüssel
    KYP = "6"  # Symmetrischer Schlüssel, verschlüsselt mit öffentlichem Schlüssel


class AlgorithmParameterIVName(FinTSEnum):
    """Algorithmusparameter IV, Name (Algorithm Parameter IV Name).

    Source: FinTS 3.0 Formals
    """
    IVC = "1"  # Initialization value, clear text


class CreditDebit(FinTSEnum):
    """Soll-Haben-Kennzeichen (Credit/Debit Indicator).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """
    CREDIT = "C"  # Haben (Credit)
    DEBIT = "D"   # Soll (Debit)


class SynchronizationMode(FinTSEnum):
    """Synchronisierungsmodus (Synchronization Mode).

    Source: FinTS 3.0 Formals
    """
    NEW_SYSTEM_ID = "0"   # Neue Kundensystem-ID zurückmelden
    LAST_MESSAGE = "1"    # Letzte verarbeitete Nachrichtennummer
    SIGNATURE_ID = "2"    # Signatur-ID zurückmelden


class SystemIDStatus(FinTSEnum):
    """Kundensystem-Status (System ID Status).

    Source: FinTS 3.0 Formals
    """
    ID_UNNECESSARY = "0"  # Kundensystem-ID wird nicht benötigt
    ID_NECESSARY = "1"    # Kundensystem-ID wird benötigt


class UPDUsage(FinTSEnum):
    """UPD-Verwendung (UPD Usage).

    Source: FinTS 3.0 Formals
    """
    UPD_CONCLUSIVE = "0"     # Nicht aufgeführte GV sind gesperrt
    UPD_INCONCLUSIVE = "1"   # Keine Aussage über nicht aufgeführte GV


class Language(FinTSEnum):
    """Dialogsprache (Dialog Language).

    Source: FinTS 3.0 Formals
    """
    DEFAULT = "0"  # Standard
    DE = "1"       # Deutsch
    EN = "2"       # Englisch
    FR = "3"       # Französisch


class ServiceType(FinTSIntEnum):
    """Kommunikationsdienst (Service Type).

    Source: FinTS 3.0 Formals
    """
    T_ONLINE = 1   # T-Online
    TCP_IP = 2     # TCP/IP (SLIP/PPP)
    HTTPS = 3      # HTTPS


class TANMediaType(FinTSEnum):
    """TAN-Medium-Art (TAN Media Type).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ALL = "0"       # Alle
    ACTIVE = "1"    # Aktiv
    AVAILABLE = "2" # Verfügbar


class TANMediaClass(FinTSEnum):
    """TAN-Medium-Klasse (TAN Media Class).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ALL = "A"       # Alle Medien
    LIST = "L"      # Liste
    GENERATOR = "G" # TAN-Generator
    MOBILE = "M"    # Mobiltelefon mit mobileTAN
    SECODER = "S"   # Secoder
    BILATERAL = "B" # Bilateral vereinbart


class TANMediumStatus(FinTSEnum):
    """TAN-Medium-Status.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ACTIVE = "1"              # Aktiv
    AVAILABLE = "2"           # Verfügbar
    ACTIVE_SUCCESSOR = "3"    # Aktiv Folgekarte
    AVAILABLE_SUCCESSOR = "4" # Verfügbar Folgekarte


class TANTimeDialogAssociation(FinTSEnum):
    """TAN Zeit- und Dialogbezug (TAN Time/Dialog Association).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    NOT_ALLOWED = "1"     # TAN nicht zeitversetzt/dialogübergreifend erlaubt
    ALLOWED = "2"         # TAN zeitversetzt/dialogübergreifend erlaubt
    BOTH = "3"            # Beide Verfahren unterstützt
    NOT_APPLICABLE = "4"  # Nicht zutreffend


class AllowedFormat(FinTSEnum):
    """Erlaubtes Format im Zwei-Schritt-Verfahren (Allowed Format).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    NUMERIC = "1"       # Numerisch
    ALPHANUMERIC = "2"  # Alphanumerisch


class TANUsageOption(FinTSEnum):
    """TAN-Einsatzoption (TAN Usage Option).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    ALL_ACTIVE = "0"          # Kunde kann alle "aktiven" Medien parallel nutzen
    EXACTLY_ONE = "1"         # Kunde kann genau ein Medium zu einer Zeit nutzen
    MOBILE_AND_GENERATOR = "2"  # Kunde kann Mobiltelefon und TAN-Generator parallel nutzen


class TANListNumberRequired(FinTSEnum):
    """TAN-Listennummer erforderlich (TAN List Number Required).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    MUST_NOT = "0"  # TAN-Listennummer darf nicht angegeben werden
    CAN = "1"       # TAN-Listennummer kann angegeben werden
    MUST = "2"      # TAN-Listennummer muss angegeben werden


class InitializationMode(FinTSEnum):
    """Initialisierungsmodus (Initialization Mode).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    CLEARTEXT_PIN = "00"        # Klartext-PIN ohne TAN
    ENCRYPTED_PIN = "01"        # Verschlüsselte PIN und target/cleartext TAN
    RESERVED_02 = "02"          # Reserviert


class DescriptionRequired(FinTSEnum):
    """Bezeichnung des TAN-Medium erforderlich (Description Required).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    MUST_NOT = "0"  # Bezeichnung des TAN-Mediums darf nicht angegeben werden
    MAY = "1"       # Bezeichnung des TAN-Mediums kann angegeben werden
    MUST = "2"      # Bezeichnung des TAN-Mediums muss angegeben werden


class SMSChargeAccountRequired(FinTSEnum):
    """SMS-Abbuchungskonto erforderlich (SMS Charge Account Required).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    MUST_NOT = "0"  # SMS-Abbuchungskonto darf nicht angegeben werden
    MAY = "1"       # SMS-Abbuchungskonto kann angegeben werden
    MUST = "2"      # SMS-Abbuchungskonto muss angegeben werden


class PrincipalAccountRequired(FinTSEnum):
    """Auftraggeberkonto erforderlich (Principal Account Required).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    MUST_NOT = "0"  # Auftraggeberkonto darf nicht angegeben werden
    MUST = "2"      # Auftraggeberkonto muss angegeben werden


class TaskHashAlgorithm(FinTSEnum):
    """Auftrags-Hashwertverfahren (Task Hash Algorithm).

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """
    NONE = "0"       # Auftrags-Hashwert nicht unterstützt
    RIPEMD_160 = "1" # RIPEMD-160
    SHA_1 = "2"      # SHA-1


class Confirmation(FinTSEnum):
    """Quittierung (Confirmation).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """
    NOT_REQUIRED = "0"        # Nicht notwendig
    CONFIRMED = "1"           # Quittiert
    AWAITING_CONFIRMATION = "2"  # Quittierung offen


# Versioned aliases for backwards compatibility
# These map legacy versioned enums to their current equivalents
Language2 = Language  # Language version 2 is same as Language
TANMediaType2 = TANMediaType  # TANMediaType version 2
TANMediaClass3 = TANMediaClass  # TANMediaClass version 3 (subset)
TANMediaClass4 = TANMediaClass  # TANMediaClass version 4


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
    "TANUsageOption",
    "TANListNumberRequired",
    "InitializationMode",
    "DescriptionRequired",
    "SMSChargeAccountRequired",
    "PrincipalAccountRequired",
    "TaskHashAlgorithm",
    # Versioned aliases
    "Language2",
    "TANMediaType2",
    "TANMediaClass3",
    "TANMediaClass4",
    "Confirmation",
]

