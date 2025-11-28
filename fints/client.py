import datetime
import logging
from collections.abc import Iterable
from decimal import Decimal
from enum import Enum

from sepaxml import SepaTransfer

from . import version
from .constants import SYSTEM_ID_UNASSIGNED
from .connection import FinTSHTTPSConnection
from .dialog import FinTSDialog
from .infrastructure.fints import (
    NeedRetryResponse as _NeedRetryResponse,
    RESPONSE_STATUS_MAPPING,
    ResponseStatus,
    TransactionResponse,
)
from .infrastructure.fints.services import StatementsService, TransactionsService
from .exceptions import *
from .formals import (
    BankIdentifier,
    TANMediaClass4, TANMediaType2,
    StatementFormat
)
from .infrastructure.legacy import (
    DialogSessionManager,
    NeedTANResponse,
    PinTanWorkflow,
    TouchdownPaginator,
)
from .infrastructure.fints import FinTSOperations
from .message import FinTSInstituteMessage
from .models import SEPAAccount
from .parser import FinTS3Serializer
from .segments.accounts import HISPA1, HKSPA1
from .segments.bank import HIBPA3, HIUPA4, HKKOM4
from .segments.debit import (
    HKDBS1, HKDBS2, HKDMB1, HKDMC1, HKDME1, HKDME2,
    HKDSC1, HKDSE1, HKDSE2, DebitResponseBase,
)
from .segments.depot import HKWPD5, HKWPD6
from .segments.dialog import HIRMG2, HIRMS2
from .segments.journal import HKPRO3, HKPRO4
from .segments.saldo import HKSAL5, HKSAL6, HKSAL7
from .segments.statement import DKKKU2
from .segments.transfer import HKCCM1, HKCCS1, HKIPZ1, HKIPM1
from .types import SegmentSequence
from .utils import (
    MT535_Miniparser, Password,
    compress_datablob, decompress_datablob,
)

NeedRetryResponse = _NeedRetryResponse  # backward compatibility re-export

logger = logging.getLogger(__name__)
DATA_BLOB_MAGIC = b'python-fints_DATABLOB'

# workaround for ING not offering PSD2 conform two step authentication
# ING only accepts one step authentication and only allows reading operations

class FinTSClientMode(Enum):
    OFFLINE = 'offline'
    INTERACTIVE = 'interactive'


class FinTS3Client:
    def __init__(self,
                 bank_identifier, user_id, customer_id=None,
                 from_data: bytes=None, system_id=None,
                 product_id=None, product_version=version[:5],
                 mode=FinTSClientMode.INTERACTIVE):
        self.accounts = []
        if isinstance(bank_identifier, BankIdentifier):
            self.bank_identifier = bank_identifier
        elif isinstance(bank_identifier, str):
            self.bank_identifier = BankIdentifier(BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank_identifier)
        else:
            raise TypeError("bank_identifier must be BankIdentifier or str (BLZ)")
        self.system_id = system_id or SYSTEM_ID_UNASSIGNED
        if not product_id:
            raise TypeError("The product_id keyword argument is mandatory starting with python-fints version 4. See "
                            "https://python-fints.readthedocs.io/en/latest/upgrading_3_4.html for more information.")

        self.user_id = user_id
        self.customer_id = customer_id or user_id
        self.bpd_version = 0
        self.bpa = None
        self.bpd = SegmentSequence()
        self.upd_version = 0
        self.upa = None
        self.upd = SegmentSequence()
        self.product_name = product_id
        self.product_version = product_version
        self.response_callbacks = []
        self.mode = mode
        self.init_tan_response = None
        self._dialog_manager = DialogSessionManager(self)
        self._transactions_service_impl = None
        self._statements_service_impl = None
        self._touchdown_paginator = None

        if from_data:
            self.set_data(bytes(from_data))

    # ------------------------------------------------------------------
    # Compatibility helpers exposing the legacy _standing_dialog attribute
    # ------------------------------------------------------------------

    @property
    def _standing_dialog(self):  # pragma: no cover - thin compatibility shim
        return self._dialog_manager.standing_dialog

    @_standing_dialog.setter
    def _standing_dialog(self, value):  # pragma: no cover - thin compatibility shim
        self._dialog_manager.standing_dialog = value

    def _new_dialog(self, lazy_init=False):
        raise NotImplemented()

    def _ensure_system_id(self):
        self._dialog_manager.ensure_system_id()

    def _process_response(self, dialog, segment, response):
        pass

    def process_response_message(self, dialog, message: FinTSInstituteMessage, internal_send=True):
        bpa = message.find_segment_first(HIBPA3)
        if bpa:
            self.bpa = bpa
            self.bpd_version = bpa.bpd_version
            self.bpd = SegmentSequence(
                message.find_segments(
                    callback=lambda m: len(m.header.type) == 6
                    and m.header.type[1] == 'I'
                    and m.header.type[5] == 'S'
                )
            )

        upa = message.find_segment_first(HIUPA4)
        if upa:
            self.upa = upa
            self.upd_version = upa.upd_version
            self.upd = SegmentSequence(
                message.find_segments('HIUPD')
            )

        for seg in message.find_segments(HIRMG2):
            for response in seg.responses:
                if not internal_send:
                    self._log_response(None, response)

                    self._call_callbacks(None, response)

                self._process_response(dialog, None, response)

        for seg in message.find_segments(HIRMS2):
            for response in seg.responses:
                segment = None  # FIXME: Provide segment

                if not internal_send:
                    self._log_response(segment, response)

                    self._call_callbacks(segment, response)

                self._process_response(dialog, segment, response)

    def _send_with_possible_retry(self, dialog, command_seg, resume_func):
        response = dialog._send(command_seg)
        return resume_func(command_seg, response)

    def __enter__(self):
        self._dialog_manager.enter()

    def __exit__(self, exc_type, exc_value, traceback):
        self._dialog_manager.exit(exc_type, exc_value, traceback)

    def _get_dialog(self, lazy_init=False):
        return self._dialog_manager.get_dialog(lazy_init=lazy_init)

    def _touchdown_helper(self):
        if self._touchdown_paginator is None:
            self._touchdown_paginator = TouchdownPaginator(self)
        return self._touchdown_paginator

    def _transactions_service(self):
        if self._transactions_service_impl is None:
            self._transactions_service_impl = TransactionsService(self)
        return self._transactions_service_impl

    def _statements_service(self):
        if self._statements_service_impl is None:
            self._statements_service_impl = StatementsService(self)
        return self._statements_service_impl

    def _set_data_v1(self, data):
        self.system_id = data.get('system_id', self.system_id)

        if all(x in data for x in ('bpd_bin', 'bpa_bin', 'bpd_version')):
            if data['bpd_version'] >= self.bpd_version and data['bpa_bin']:
                self.bpd = SegmentSequence(data['bpd_bin'])
                self.bpa = SegmentSequence(data['bpa_bin']).segments[0]
                self.bpd_version = data['bpd_version']

        if all(x in data for x in ('upd_bin', 'upa_bin', 'upd_version')):
            if data['upd_version'] >= self.upd_version and data['upa_bin']:
                self.upd = SegmentSequence(data['upd_bin'])
                self.upa = SegmentSequence(data['upa_bin']).segments[0]
                self.upd_version = data['upd_version']

    def _deconstruct_v1(self, including_private=False):
        data = {
            "system_id": self.system_id,
            "bpd_bin": self.bpd.render_bytes(),
            "bpa_bin": FinTS3Serializer().serialize_message(self.bpa) if self.bpa else None,
            "bpd_version": self.bpd_version,
        }

        if including_private:
            data.update({
                "upd_bin": self.upd.render_bytes(),
                "upa_bin": FinTS3Serializer().serialize_message(self.upa) if self.upa else None,
                "upd_version": self.upd_version,
            })

        return data

    def deconstruct(self, including_private: bool=False) -> bytes:
        """Return state of this FinTSClient instance as an opaque datablob. You should not
        use this object after calling this method.

        Information about the connection is implicitly retrieved from the bank and
        cached in the FinTSClient. This includes: system identifier, bank parameter
        data, user parameter data. It's not strictly required to retain this information
        across sessions, but beneficial. If possible, an API user SHOULD use this method
        to serialize the client instance before destroying it, and provide the serialized
        data next time an instance is constructed.

        Parameter `including_private` should be set to True, if the storage is sufficiently
        secure (with regards to confidentiality) to include private data, specifically,
        account numbers and names. Most often this is the case.

        Note: No connection information is stored in the datablob, neither is the PIN.
        """
        data = self._deconstruct_v1(including_private=including_private)
        return compress_datablob(DATA_BLOB_MAGIC, 1, data)

    def set_data(self, blob: bytes):
        """Restore a datablob created with deconstruct().

        You should only call this method once, and only immediately after constructing
        the object and before calling any other method or functionality (e.g. __enter__()).
        For convenience, you can pass the `from_data` parameter to __init__()."""
        decompress_datablob(DATA_BLOB_MAGIC, blob, self)

    def _log_response(self, segment, response):
        if response.code[0] in ('0', '1'):
            log_target = logger.info
        elif response.code[0] in ('3',):
            log_target = logger.warning
        else:
            log_target = logger.error

        log_target("Dialog response: {} - {}{}".format(
            response.code,
            response.text,
            " ({!r})".format(response.parameters) if response.parameters else ""),
            extra={
                'fints_response_code': response.code,
                'fints_response_text': response.text,
                'fints_response_parameters': response.parameters,
            }
        )

    def get_information(self):
        """
        Return information about the connected bank.

        Note: Can only be filled after the first communication with the bank.
        If in doubt, use a construction like::

            f = FinTS3Client(...)
            with f:
                info = f.get_information()

        Returns a nested dictionary::

            bank:
                name: Bank Name
                supported_operations: dict(FinTSOperations -> boolean)
                supported_formats: dict(FinTSOperation -> ['urn:iso:std:iso:20022:tech:xsd:pain.001.003.03', ...])
                supported_sepa_formats: ['urn:iso:std:iso:20022:tech:xsd:pain.001.003.03', ...]
            accounts:
                - iban: IBAN
                  account_number: Account Number
                  subaccount_number: Sub-Account Number
                  bank_identifier: fints.formals.BankIdentifier(...)
                  customer_id: Customer ID
                  type: Account type
                  currency: Currency
                  owner_name: ['Owner Name 1', 'Owner Name 2 (optional)']
                  product_name: Account product name
                  supported_operations: dict(FinTSOperations -> boolean)
                - ...

        """
        retval = {
            'bank': {},
            'accounts': [],
            'auth': {},
        }
        if self.bpa:
            retval['bank']['name'] = self.bpa.bank_name
        if self.bpd.segments:
            retval['bank']['supported_operations'] = {
                op: any(self.bpd.find_segment_first(cmd[0]+'I'+cmd[2:]+'S') for cmd in op.value)
                for op in FinTSOperations
            }
            retval['bank']['supported_formats'] = {}
            for op in FinTSOperations:
                for segment in (self.bpd.find_segment_first(cmd[0] + 'I' + cmd[2:] + 'S') for cmd in op.value):
                    if not hasattr(segment, 'parameter'):
                        continue
                    formats = getattr(segment.parameter, 'supported_sepa_formats', [])
                    retval['bank']['supported_formats'][op] = list(
                        set(retval['bank']['supported_formats'].get(op, [])).union(set(formats))
                    )
            hispas = self.bpd.find_segment_first('HISPAS')
            if hispas:
                retval['bank']['supported_sepa_formats'] = list(hispas.parameter.supported_sepa_formats)
            else:
                retval['bank']['supported_sepa_formats'] = []
        if self.upd.segments:
            for upd in self.upd.find_segments('HIUPD'):
                acc = {}
                acc['iban'] = upd.iban
                acc['account_number'] = upd.account_information.account_number
                acc['subaccount_number'] = upd.account_information.subaccount_number
                acc['bank_identifier'] = upd.account_information.bank_identifier
                acc['customer_id'] = upd.customer_id
                acc['type'] = upd.account_type
                acc['currency'] = upd.account_currency
                acc['extension'] = upd.extension
                acc['owner_name'] = []
                if upd.name_account_owner_1:
                    acc['owner_name'].append(upd.name_account_owner_1)
                if upd.name_account_owner_2:
                    acc['owner_name'].append(upd.name_account_owner_2)
                acc['product_name'] = upd.account_product_name
                acc['supported_operations'] = {
                    op: any(allowed_transaction.transaction in op.value for allowed_transaction in upd.allowed_transactions)
                    for op in FinTSOperations
                }
                retval['accounts'].append(acc)
        return retval


    def _get_sepa_accounts(self, command_seg, response):
        self.accounts = []
        for seg in response.find_segments(HISPA1, throw=True):
            self.accounts.extend(seg.accounts)

        return [a for a in [acc.as_sepa_account() for acc in self.accounts] if a]

    def get_sepa_accounts(self):
        """
        Returns a list of SEPA accounts

        :return: List of SEPAAccount objects.
        """

        seg = HKSPA1()
        with self._get_dialog() as dialog:
            return self._send_with_possible_retry(dialog, seg, self._get_sepa_accounts)

    def _fetch_with_touchdowns(self, dialog, segment_factory, response_processor, *args, **kwargs):
        """Execute a sequence of fetch commands on dialog with touchdown pagination."""
        return self._touchdown_helper().fetch(
            dialog,
            segment_factory,
            response_processor,
            *args,
            **kwargs,
        )

    def _find_highest_supported_command(self, *segment_classes, **kwargs):
        """Search the BPD for the highest supported version of a segment."""
        return_parameter_segment = kwargs.get("return_parameter_segment", False)

        parameter_segment_name = "{}I{}S".format(segment_classes[0].TYPE[0], segment_classes[0].TYPE[2:])
        version_map = dict((clazz.VERSION, clazz) for clazz in segment_classes)
        max_version = self.bpd.find_segment_highest_version(parameter_segment_name, version_map.keys())
        if not max_version:
            raise FinTSUnsupportedOperation('No supported {} version found. I support {}, bank supports {}.'.format(
                parameter_segment_name,
                tuple(version_map.keys()),
                tuple(v.header.version for v in self.bpd.find_segments(parameter_segment_name))
            ))

        if return_parameter_segment:
            return max_version, version_map.get(max_version.header.version)
        else:
            return version_map.get(max_version.header.version)

    def get_transactions(
        self,
        account: SEPAAccount,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
        include_pending: bool = False,
    ):
        return self._transactions_service().fetch_mt940(
            account,
            start_date,
            end_date,
            include_pending=include_pending,
        )

    def get_transactions_xml(self, account: SEPAAccount, start_date: datetime.date = None,
                             end_date: datetime.date = None) -> list:
        return self._transactions_service().fetch_camt(
            account,
            start_date,
            end_date,
        )

    def _supported_camt_message_types(self, parameter_segment=None):
        segment = parameter_segment or self.bpd.find_segment_first('HICAZS')
        if not segment:
            return ()

        identifiers: list[str] = []
        self._collect_camt_identifiers(segment, identifiers)

        ordered: list[str] = []
        seen: set[str] = set()
        for identifier in identifiers:
            if identifier not in seen:
                seen.add(identifier)
                ordered.append(identifier)
        return tuple(ordered)

    def _collect_camt_identifiers(self, node, bucket):
        if node is None:
            return
        if isinstance(node, str):
            if 'camt.' in node.lower():
                bucket.append(node)
            return
        if isinstance(node, (bytes, bytearray)):
            return
        if isinstance(node, Iterable):
            for item in node:
                self._collect_camt_identifiers(item, bucket)
            return

        fields = getattr(node, '_fields', {})
        for name in fields:
            self._collect_camt_identifiers(getattr(node, name), bucket)

        additional = getattr(node, '_additional_data', None)
        if additional:
            self._collect_camt_identifiers(additional, bucket)

    def get_credit_card_transactions(self, account: SEPAAccount, credit_card_number: str, start_date: datetime.date = None, end_date: datetime.date = None):
        # FIXME Reverse engineered, probably wrong
        with self._get_dialog() as dialog:
            dkkku = self._find_highest_supported_command(DKKKU2)

            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: dkkku(
                    account=dkkku._fields['account'].type.from_sepa_account(account) if account else None,
                    credit_card_number=credit_card_number,
                    date_start=start_date,
                    date_end=end_date,
                    touchdown_point=touchdown,
                ),
                lambda responses: responses,
                'DIKKU'
            )

        return responses

    def _get_balance(self, command_seg, response):
        for resp in response.response_segments(command_seg, 'HISAL'):
            return resp.balance_booked.as_mt940_Balance()

    def get_balance(self, account: SEPAAccount):
        """
        Fetches an accounts current balance.

        :param account: SEPA account to fetch the balance
        :return: A mt940.models.Balance object
        """

        with self._get_dialog() as dialog:
            hksal = self._find_highest_supported_command(HKSAL5, HKSAL6, HKSAL7)

            seg = hksal(
                account=hksal._fields['account'].type.from_sepa_account(account),
                all_accounts=False,
            )

            response = self._send_with_possible_retry(dialog, seg, self._get_balance)
            return response

    def get_holdings(self, account: SEPAAccount):
        """
        Retrieve holdings of an account.

        :param account: SEPAAccount to retrieve holdings for.
        :return: List of Holding objects
        """
        # init dialog
        with self._get_dialog() as dialog:
            hkwpd = self._find_highest_supported_command(HKWPD5, HKWPD6)

            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkwpd(
                    account=hkwpd._fields['account'].type.from_sepa_account(account),
                    touchdown_point=touchdown,
                ),
                lambda responses: responses,  # TODO
                'HIWPD'
            )

        if isinstance(responses, NeedTANResponse):
            return responses

        holdings = []
        for resp in responses:
            if type(resp.holdings) == bytes:
                holding_str = resp.holdings.decode()
            else:
                holding_str = resp.holdings

            mt535_lines = str.splitlines(holding_str)
            # The first line is empty - drop it.
            del mt535_lines[0]
            mt535 = MT535_Miniparser()
            holdings.extend(mt535.parse(mt535_lines))

        if not holdings:
            logger.debug('No HIWPD response segment found - maybe account has no holdings?')
        return holdings

    def get_scheduled_debits(self, account: SEPAAccount, multiple=False):
        with self._get_dialog() as dialog:
            if multiple:
                command_classes = (HKDMB1, )
                response_type = "HIDMB"
            else:
                command_classes = (HKDBS1, HKDBS2)
                response_type = "HKDBS"

            hkdbs = self._find_highest_supported_command(*command_classes)

            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkdbs(
                    account=hkdbs._fields['account'].type.from_sepa_account(account),
                    touchdown_point=touchdown,
                ),
                lambda responses: responses,
                response_type,
            )

        return responses

    def get_status_protocol(self):
        with self._get_dialog() as dialog:
            hkpro = self._find_highest_supported_command(HKPRO3, HKPRO4)

            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkpro(
                    touchdown_point=touchdown,
                ),
                lambda responses: responses,
                'HIPRO',
            )

        return responses

    def get_communication_endpoints(self):
        with self._get_dialog() as dialog:
            hkkom = self._find_highest_supported_command(HKKOM4)

            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkkom(
                    touchdown_point=touchdown,
                ),
                lambda responses: responses,
                'HIKOM'
            )

        return responses

    def get_statements(self, account: SEPAAccount):
        return self._statements_service().list_statements(account)

    def get_statement(self, account: SEPAAccount, number: int, year: int, format: StatementFormat = None):
        return self._statements_service().fetch_statement(
            account,
            number,
            year,
            format=format,
        )

    def _find_supported_sepa_version(self, candidate_versions):
        hispas = self.bpd.find_segment_first('HISPAS')
        if not hispas:
            logger.warning("Could not determine supported SEPA versions, is the dialogue open? Defaulting to first candidate: %s.", candidate_versions[0])
            return candidate_versions[0]

        bank_supported = list(hispas.parameter.supported_sepa_formats)

        for candidate in candidate_versions:
            if "urn:iso:std:iso:20022:tech:xsd:{}".format(candidate) in bank_supported:
                return candidate
            if "urn:iso:std:iso:20022:tech:xsd:{}.xsd".format(candidate) in bank_supported:
                return candidate

        logger.warning("No common supported SEPA version. Defaulting to first candidate and hoping for the best: %s.", candidate_versions[0])
        return candidate_versions[0]

    def simple_sepa_transfer(self, account: SEPAAccount, iban: str, bic: str,
                             recipient_name: str, amount: Decimal, account_name: str, reason: str, instant_payment=False,
                             endtoend_id='NOTPROVIDED'):
        """
        Simple SEPA transfer.

        :param account: SEPAAccount to start the transfer from.
        :param iban: Recipient's IBAN
        :param bic: Recipient's BIC
        :param recipient_name: Recipient name
        :param amount: Amount as a ``Decimal``
        :param account_name: Sender account name
        :param reason: Transfer reason
        :param instant_payment: Whether to use instant payment (defaults to ``False``)
        :param endtoend_id: End-to-end-Id (defaults to ``NOTPROVIDED``)
        :return: Returns either a NeedRetryResponse or TransactionResponse
        """
        config = {
            "name": account_name,
            "IBAN": account.iban,
            "BIC": account.bic,
            "batch": False,
            "currency": "EUR",
        }
        version = self._find_supported_sepa_version(['pain.001.001.03', 'pain.001.003.03'])
        sepa = SepaTransfer(config, version)
        payment = {
            "name": recipient_name,
            "IBAN": iban,
            "BIC": bic,
            "amount": round(Decimal(amount) * 100),  # in cents
            "execution_date": datetime.date(1999, 1, 1),
            "description": reason,
            "endtoend_id": endtoend_id,
        }
        sepa.add_payment(payment)
        xml = sepa.export().decode()
        return self.sepa_transfer(account, xml, pain_descriptor="urn:iso:std:iso:20022:tech:xsd:"+version, instant_payment=instant_payment)

    def sepa_transfer(self, account: SEPAAccount, pain_message: str, multiple=False,
                      control_sum=None, currency='EUR', book_as_single=False,
                      pain_descriptor='urn:iso:std:iso:20022:tech:xsd:pain.001.001.03', instant_payment=False):
        """
        Custom SEPA transfer.

        :param account: SEPAAccount to send the transfer from.
        :param pain_message: SEPA PAIN message containing the transfer details.
        :param multiple: Whether this message contains multiple transfers.
        :param control_sum: Sum of all transfers (required if there are multiple)
        :param currency: Transfer currency
        :param book_as_single: Kindly ask the bank to put multiple transactions as separate lines on the bank statement (defaults to ``False``)
        :param pain_descriptor: URN of the PAIN message schema used.
        :param instant_payment: Whether this is an instant transfer (defaults to ``False``)
        :return: Returns either a NeedRetryResponse or TransactionResponse
        """

        with self._get_dialog() as dialog:
            if multiple:
                command_class = HKIPM1 if instant_payment else HKCCM1
            else:
                command_class = HKIPZ1 if instant_payment else HKCCS1

            hiccxs, hkccx = self._find_highest_supported_command(
                command_class,
                return_parameter_segment=True
            )

            seg = hkccx(
                account=hkccx._fields['account'].type.from_sepa_account(account),
                sepa_descriptor=pain_descriptor,
                sepa_pain_message=pain_message.encode(),
            )

            # if instant_payment:
            #     seg.allow_convert_sepa_transfer = True

            if multiple:
                if hiccxs.parameter.sum_amount_required and control_sum is None:
                    raise ValueError("Control sum required.")
                if book_as_single and not hiccxs.parameter.single_booking_allowed:
                    raise FinTSUnsupportedOperation("Single booking not allowed by bank.")

                if control_sum:
                    seg.sum_amount.amount = control_sum
                    seg.sum_amount.currency = currency

                if book_as_single:
                    seg.request_single_booking = True

            return self._send_with_possible_retry(dialog, seg, self._continue_sepa_transfer)

    def _continue_sepa_transfer(self, command_seg, response):
        retval = TransactionResponse(response, HIRMS2)

        for seg in response.find_segments(HIRMS2):
            for resp in seg.responses:
                retval.set_status_if_higher(
                    RESPONSE_STATUS_MAPPING.get(resp.code[0], ResponseStatus.UNKNOWN)
                )
                retval.responses.append(resp)

        return retval

    def _continue_dialog_initialization(self, command_seg, response):
        return response

    def sepa_debit(self, account: SEPAAccount, pain_message: str, multiple=False, cor1=False,
                   control_sum=None, currency='EUR', book_as_single=False,
                   pain_descriptor='urn:iso:std:iso:20022:tech:xsd:pain.008.003.01'):
        """
        Custom SEPA debit.

        :param account: SEPAAccount to send the debit from.
        :param pain_message: SEPA PAIN message containing the debit details.
        :param multiple: Whether this message contains multiple debits.
        :param cor1: Whether to use COR1 debit (lead time reduced to 1 day)
        :param control_sum: Sum of all debits (required if there are multiple)
        :param currency: Debit currency
        :param book_as_single: Kindly ask the bank to put multiple transactions as separate lines on the bank statement (defaults to ``False``)
        :param pain_descriptor: URN of the PAIN message schema used. Defaults to ``urn:iso:std:iso:20022:tech:xsd:pain.008.003.01``.
        :return: Returns either a NeedRetryResponse or TransactionResponse (with data['task_id'] set, if available)
        """

        with self._get_dialog() as dialog:
            if multiple:
                if cor1:
                    command_candidates = (HKDMC1, )
                else:
                    command_candidates = (HKDME1, HKDME2)
            else:
                if cor1:
                    command_candidates = (HKDSC1, )
                else:
                    command_candidates = (HKDSE1, HKDSE2)

            hidxxs, hkdxx = self._find_highest_supported_command(
                *command_candidates,
                return_parameter_segment=True
            )

            seg = hkdxx(
                account=hkdxx._fields['account'].type.from_sepa_account(account),
                sepa_descriptor=pain_descriptor,
                sepa_pain_message=pain_message.encode(),
            )

            if multiple:
                if hidxxs.parameter.sum_amount_required and control_sum is None:
                    raise ValueError("Control sum required.")
                if book_as_single and not hidxxs.parameter.single_booking_allowed:
                    raise FinTSUnsupportedOperation("Single booking not allowed by bank.")

                if control_sum:
                    seg.sum_amount.amount = control_sum
                    seg.sum_amount.currency = currency

                if book_as_single:
                    seg.request_single_booking = True

            return self._send_with_possible_retry(dialog, seg, self._continue_sepa_debit)

    def _continue_sepa_debit(self, command_seg, response):
        retval = TransactionResponse(response, HIRMS2)

        for seg in response.find_segments(HIRMS2):
            for resp in seg.responses:
                retval.set_status_if_higher(
                    RESPONSE_STATUS_MAPPING.get(resp.code[0], ResponseStatus.UNKNOWN)
                )
                retval.responses.append(resp)

        for seg in response.find_segments(DebitResponseBase):
            if seg.task_id:
                retval.data['task_id'] = seg.task_id

        if not 'task_id' in retval.data:
            for seg in response.find_segments('HITAN'):
                if hasattr(seg, 'task_reference') and seg.task_reference:
                    retval.data['task_id'] = seg.task_reference

        return retval

    def add_response_callback(self, cb):
        # FIXME document
        self.response_callbacks.append(cb)

    def remove_response_callback(self, cb):
        # FIXME document
        self.response_callbacks.remove(cb)

    def set_product(self, product_name, product_version):
        """Set the product name and version that is transmitted as part of our identification

        According to 'FinTS Financial Transaction Services, Schnittstellenspezifikation, Formals',
        version 3.0, section C.3.1.3, you should fill this with useful information about the
        end-user product, *NOT* the FinTS library."""

        self.product_name = product_name
        self.product_version = product_version

    def _call_callbacks(self, *cb_data):
        for cb in self.response_callbacks:
            cb(*cb_data)

    def pause_dialog(self):
        """Pause a standing dialog and return the saved dialog state.

        Sometimes, for example in a web app, it's not possible to keep a context open
        during user input. In some cases, though, it's required to send a response
        within the same dialog that issued the original task (f.e. TAN with TANTimeDialogAssociation.NOT_ALLOWED).
        This method freezes the current standing dialog (started with FinTS3Client.__enter__()) and
        returns the frozen state.

        Commands MUST NOT be issued in the dialog after calling this method.

        MUST be used in conjunction with deconstruct()/set_data().

        Caller SHOULD ensure that the dialog is resumed (and properly ended) within a reasonable amount of time.

        :Example:

        ::

            client = FinTS3PinTanClient(..., from_data=None)
            with client:
                challenge = client.sepa_transfer(...)

                dialog_data = client.pause_dialog()

                # dialog is now frozen, no new commands may be issued
                # exiting the context does not end the dialog

            client_data = client.deconstruct()

            # Store dialog_data and client_data out-of-band somewhere
            # ... Some time passes ...
            # Later, possibly in a different process, restore the state

            client = FinTS3PinTanClient(..., from_data=client_data)
            with client.resume_dialog(dialog_data):
                client.send_tan(...)

                # Exiting the context here ends the dialog, unless frozen with pause_dialog() again.
        """
        return self._dialog_manager.pause()

    def resume_dialog(self, dialog_data):
        # FIXME document, test,    NOTE NO UNTRUSTED SOURCES
        return self._dialog_manager.resume(dialog_data)


class FinTS3PinTanClient(FinTS3Client):

    def __init__(self, bank_identifier, user_id, pin, server, customer_id=None, tan_medium=None, *args, **kwargs):
        self.pin = Password(pin) if pin is not None else pin
        self.connection = FinTSHTTPSConnection(server)
        self._tan_state_seed = {
            "allowed_security_functions": [],
            "selected_security_function": None,
            "selected_tan_medium": tan_medium,
            "init_tan_response": None,
        }
        self._tan_workflow = None
        super().__init__(
            bank_identifier=bank_identifier,
            user_id=user_id,
            customer_id=customer_id,
            *args,
            **kwargs,
        )

    def _tan_helper(self):
        if self._tan_workflow is None:
            self._tan_workflow = PinTanWorkflow(
                self,
                selected_security_function=self._tan_state_seed[
                    "selected_security_function"
                ],
                selected_tan_medium=self._tan_state_seed["selected_tan_medium"],
                allowed_security_functions=self._tan_state_seed[
                    "allowed_security_functions"
                ],
                init_tan_response=self._tan_state_seed["init_tan_response"],
            )
        return self._tan_workflow

    def _new_dialog(self, lazy_init=False):
        enc, auth = self._tan_helper().dialog_mechanisms()

        return FinTSDialog(
            self,
            lazy_init=lazy_init,
            enc_mechanism=enc,
            auth_mechanisms=auth,
        )

    def fetch_tan_mechanisms(self):
        return self._tan_helper().fetch_tan_mechanisms()

    def _set_data_v1(self, data):
        super()._set_data_v1(data)
        self._tan_helper().restore_state(data)

    def _deconstruct_v1(self, including_private=False):
        data = super()._deconstruct_v1(including_private=including_private)
        return self._tan_helper().dump_state(
            data,
            including_private=including_private,
        )

    def is_tan_media_required(self):
        return self._tan_helper().is_media_required()

    def _get_tan_segment(self, orig_seg, tan_process, tan_seg=None):
        return self._tan_helper().build_tan_segment(orig_seg, tan_process, tan_seg)

    def _need_twostep_tan_for_segment(self, seg):
        return self._tan_helper().need_twostep_tan(seg)

    def _send_with_possible_retry(self, dialog, command_seg, resume_func):
        return self._tan_helper().send_with_possible_retry(
            dialog,
            command_seg,
            resume_func,
        )

    def is_challenge_structured(self):
        return self._tan_helper().is_challenge_structured()

    def send_tan(self, challenge: NeedTANResponse, tan: str):
        """Send a TAN or drive the decoupled approval handshake."""

        return self._tan_helper().send_tan(challenge, tan)

    def _process_response(self, dialog, segment, response):
        self._tan_helper().handle_response(dialog, segment, response)

    def get_tan_mechanisms(self):
        """Return the available TAN mechanisms."""

        return self._tan_helper().get_tan_mechanisms()

    def get_current_tan_mechanism(self):
        return self._tan_helper().get_current_tan_mechanism()

    def set_tan_mechanism(self, security_function):
        self._tan_helper().set_tan_mechanism(security_function)

    def set_tan_medium(self, tan_medium):
        self._tan_helper().set_tan_medium(tan_medium)

    def get_tan_media(
        self,
        media_type=TANMediaType2.ALL,
        media_class=TANMediaClass4.ALL,
    ):
        """Get information about TAN lists/generators.

        Returns tuple of fints.formals.TANUsageOption and a list of
        fints.formals.TANMedia4 or fints.formals.TANMedia5 objects.
        """
        return self._tan_helper().get_tan_media(media_type, media_class)

    def get_information(self):
        retval = super().get_information()
        retval['auth'] = {
            'current_tan_mechanism': self.get_current_tan_mechanism(),
            'tan_mechanisms': self.get_tan_mechanisms(),
        }
        return retval

    # ------------------------------------------------------------------
    # Compatibility properties for TAN state
    # ------------------------------------------------------------------

    @property
    def selected_security_function(self):
        if self._tan_workflow is not None:
            return self._tan_workflow.selected_security_function
        return self._tan_state_seed["selected_security_function"]

    @selected_security_function.setter
    def selected_security_function(self, value):
        if self._tan_workflow is not None:
            self._tan_workflow.selected_security_function = value
        else:
            self._tan_state_seed["selected_security_function"] = value

    @property
    def selected_tan_medium(self):
        if self._tan_workflow is not None:
            return self._tan_workflow.selected_tan_medium
        return self._tan_state_seed["selected_tan_medium"]

    @selected_tan_medium.setter
    def selected_tan_medium(self, value):
        if self._tan_workflow is not None:
            self._tan_workflow.selected_tan_medium = value
        else:
            self._tan_state_seed["selected_tan_medium"] = value

    @property
    def allowed_security_functions(self):
        if self._tan_workflow is not None:
            return self._tan_workflow.allowed_security_functions
        return self._tan_state_seed["allowed_security_functions"]

    @allowed_security_functions.setter
    def allowed_security_functions(self, functions):
        if functions is None:
            functions = []
        if self._tan_workflow is not None:
            self._tan_workflow.allowed_security_functions = functions
        else:
            self._tan_state_seed["allowed_security_functions"] = functions

    @property
    def init_tan_response(self):
        if self._tan_workflow is not None:
            return self._tan_workflow.init_tan_response
        return self._tan_state_seed["init_tan_response"]

    @init_tan_response.setter
    def init_tan_response(self, value):
        if self._tan_workflow is not None:
            self._tan_workflow.init_tan_response = value
        else:
            self._tan_state_seed["init_tan_response"] = value
