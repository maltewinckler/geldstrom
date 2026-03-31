"""FinTS Protocol Segments - Pydantic models.

This module provides Pydantic-based implementations of FinTS segments,
replacing the legacy Container-based definitions in fints/segments/.

Segments are the main building blocks of FinTS messages. Each segment
has a header and type-specific data fields.

Organization:
- dialog: Dialog management (HNHBK, HNHBS, HIRMG, HIRMS, HKSYN, HISYN, HKEND)
- message: Message security (HNVSK, HNVSD, HNSHK, HNSHA)
- auth: Authentication (HKIDN, HKVVB, HKTAN, HITAN, HKTAB, HITAB)
- bank: Bank/User parameters (HIBPA, HIUPA, HIUPD, HIKOM)
- pintan: PIN/TAN parameters (HIPINS, HITANS)
- saldo: Balance segments (HKSAL, HISAL)
- accounts: Account segments (HKSPA, HISPA)
- transactions: Transaction segments (HKKAZ, HIKAZ, HKCAZ, HICAZ)
- params: Generic parameter segments
"""

from __future__ import annotations

from .accounts import (
    HISPA1,
    HKSPA1,
)
from .auth import (
    HITAB4,
    HITAB5,
    HITAB_VERSIONS,
    HITAN6,
    HITAN7,
    HITAN_VERSIONS,
    # Identification
    HKIDN2,
    HKIDN_VERSIONS,
    # TAN Media
    HKTAB4,
    HKTAB5,
    HKTAB_VERSIONS,
    HKTAN2,
    HKTAN6,
    HKTAN7,
    HKTAN_VERSIONS,
    # Processing
    HKVVB3,
    HKVVB_VERSIONS,
    # TAN Response
    HITANBase,
    # TAN Request
    HKTANBase,
)
from .bank import (
    # BPD
    HIBPA3,
    HIBPA_VERSIONS,
    HIKOM4,
    HIKOM_VERSIONS,
    # UPD
    HIUPA4,
    HIUPA_VERSIONS,
    HIUPD6,
    HIUPD_VERSIONS,
    # Communication
    HKKOM4,
    HKKOM_VERSIONS,
)
from .dialog import (
    # Responses
    HIRMG2,
    HIRMG_VERSIONS,
    HIRMS2,
    HIRMS_VERSIONS,
    HISYN4,
    HISYN_VERSIONS,
    # Dialog end
    HKEND1,
    HKEND_VERSIONS,
    # Synchronization
    HKSYN3,
    HKSYN_VERSIONS,
    # Message header/trailer
    HNHBK3,
    HNHBK_VERSIONS,
    HNHBS1,
    HNHBS_VERSIONS,
)
from .message import (
    HNSHA2,
    HNSHA_VERSIONS,
    # Signature
    HNSHK4,
    HNSHK_VERSIONS,
    HNVSD1,
    HNVSD_VERSIONS,
    # Encryption
    HNVSK3,
    HNVSK_VERSIONS,
)
from .params import (
    HIKAZS4,
    HIKAZS5,
    HIKAZS6,
    HIKAZS7,
    HIKAZS_VERSIONS,
    HISALS4,
    HISALS5,
    HISALS6,
    HISALS7,
    HISALS_VERSIONS,
    # Security Parameters
    HISHV3,
    HISHV_VERSIONS,
    HISPAS1,
    HISPAS2,
    HISPAS3,
    HISPAS_VERSIONS,
    # Balance Parameters
    BalanceParameter,
    # Base classes
    GenericParameter,
    GenericSegment,
    # SEPA Account Parameters
    GetSEPAAccountParameter,
)
from .params import (
    # Transaction Parameters
    TransactionParameter as ParamsTransactionParameter,
)
from .pintan import (
    # Segments
    HIPINS1,
    HIPINS_VERSIONS,
    HITANS1,
    HITANS2,
    HITANS3,
    HITANS4,
    HITANS5,
    HITANS6,
    HITANS7,
    HITANS_VERSIONS,
    ParameterPinTan,
    # Base
    ParameterSegmentBase,
    ParameterTwostepCommon,
    ParameterTwostepTAN1,
    ParameterTwostepTAN2,
    ParameterTwostepTAN3,
    ParameterTwostepTAN4,
    ParameterTwostepTAN5,
    ParameterTwostepTAN6,
    ParameterTwostepTAN7,
    # Supporting DEGs
    TransactionTANRequired,
    TwoStepParameters1,
    TwoStepParameters2,
    TwoStepParameters3,
    TwoStepParameters4,
    TwoStepParameters5,
    TwoStepParameters6,
    TwoStepParameters7,
    TwoStepParametersBase,  # Alias for backwards compatibility
    TwoStepParametersCommon,
)
from .saldo import (
    # Response segments
    HISAL5,
    HISAL6,
    HISAL7,
    HISAL_VERSIONS,
    # Request segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    # Version registry
    HKSAL_VERSIONS,
)
from .transactions import (
    # CAMT Response
    HICAZ1,
    HICAZ_VERSIONS,
    # MT940 Response
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    # CAMT Request
    HKCAZ1,
    HKCAZ_VERSIONS,
    # MT940 Request
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
)

__all__ = [
    # Dialog - Message header/trailer
    "HNHBK3",
    "HNHBS1",
    "HNHBK_VERSIONS",
    "HNHBS_VERSIONS",
    # Dialog - Responses
    "HIRMG2",
    "HIRMS2",
    "HIRMG_VERSIONS",
    "HIRMS_VERSIONS",
    # Dialog - Synchronization
    "HKSYN3",
    "HISYN4",
    "HKSYN_VERSIONS",
    "HISYN_VERSIONS",
    # Dialog - End
    "HKEND1",
    "HKEND_VERSIONS",
    # Message - Encryption
    "HNVSK3",
    "HNVSD1",
    "HNVSK_VERSIONS",
    "HNVSD_VERSIONS",
    # Message - Signature
    "HNSHK4",
    "HNSHA2",
    "HNSHK_VERSIONS",
    "HNSHA_VERSIONS",
    # Auth - Identification
    "HKIDN2",
    "HKIDN_VERSIONS",
    # Auth - Processing
    "HKVVB3",
    "HKVVB_VERSIONS",
    # Auth - TAN Request
    "HKTANBase",
    "HKTAN2",
    "HKTAN6",
    "HKTAN7",
    "HKTAN_VERSIONS",
    # Auth - TAN Response
    "HITANBase",
    "HITAN6",
    "HITAN7",
    "HITAN_VERSIONS",
    # Auth - TAN Media
    "HKTAB4",
    "HKTAB5",
    "HITAB4",
    "HITAB5",
    "HKTAB_VERSIONS",
    "HITAB_VERSIONS",
    # Bank - BPD
    "HIBPA3",
    "HIBPA_VERSIONS",
    # Bank - UPD
    "HIUPA4",
    "HIUPD6",
    "HIUPA_VERSIONS",
    "HIUPD_VERSIONS",
    # Bank - Communication
    "HKKOM4",
    "HIKOM4",
    "HKKOM_VERSIONS",
    "HIKOM_VERSIONS",
    # PIN/TAN - DEGs
    "TransactionTANRequired",
    "ParameterPinTan",
    "TwoStepParametersCommon",
    "TwoStepParametersBase",
    "TwoStepParameters1",
    "TwoStepParameters2",
    "TwoStepParameters3",
    "TwoStepParameters4",
    "TwoStepParameters5",
    "TwoStepParameters6",
    "TwoStepParameters7",
    "ParameterTwostepCommon",
    "ParameterTwostepTAN1",
    "ParameterTwostepTAN2",
    "ParameterTwostepTAN3",
    "ParameterTwostepTAN4",
    "ParameterTwostepTAN5",
    "ParameterTwostepTAN6",
    "ParameterTwostepTAN7",
    # PIN/TAN - Base
    "ParameterSegmentBase",
    # PIN/TAN - Segments
    "HIPINS1",
    "HITANS1",
    "HITANS2",
    "HITANS3",
    "HITANS4",
    "HITANS5",
    "HITANS6",
    "HITANS7",
    "HIPINS_VERSIONS",
    "HITANS_VERSIONS",
    # Balance request segments
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    # Balance response segments
    "HISAL5",
    "HISAL6",
    "HISAL7",
    # Balance version registries
    "HKSAL_VERSIONS",
    "HISAL_VERSIONS",
    # Account segments
    "HKSPA1",
    "HISPA1",
    # MT940 Transaction segments
    "HKKAZ5",
    "HKKAZ6",
    "HKKAZ7",
    "HKKAZ_VERSIONS",
    "HIKAZ5",
    "HIKAZ6",
    "HIKAZ7",
    "HIKAZ_VERSIONS",
    # CAMT Transaction segments
    "HKCAZ1",
    "HKCAZ_VERSIONS",
    "HICAZ1",
    "HICAZ_VERSIONS",
    # Parameter segments - Base
    "GenericParameter",
    "GenericSegment",
    # Parameter segments - SEPA Account
    "GetSEPAAccountParameter",
    "HISPAS1",
    "HISPAS2",
    "HISPAS3",
    "HISPAS_VERSIONS",
    # Parameter segments - Balance
    "BalanceParameter",
    "HISALS4",
    "HISALS5",
    "HISALS6",
    "HISALS7",
    "HISALS_VERSIONS",
    # Parameter segments - Transactions
    "ParamsTransactionParameter",
    "HIKAZS4",
    "HIKAZS5",
    "HIKAZS6",
    "HIKAZS7",
    "HIKAZS_VERSIONS",
    # Parameter segments - Security
    "HISHV3",
    "HISHV_VERSIONS",
]
