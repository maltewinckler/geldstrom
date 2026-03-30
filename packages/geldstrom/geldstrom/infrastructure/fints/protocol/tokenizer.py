"""FinTS Wire Format Tokenizer.

This module provides low-level tokenization of FinTS wire format data.
The tokenizer breaks raw bytes into tokens for parsing.

Token Types:
- CHAR: Character data (text)
- BINARY: Binary data (prefixed with @length@)
- PLUS: Field separator (+)
- COLON: DEG element separator (:)
- APOSTROPHE: Segment terminator (')
- EOF: End of data

Example:
    state = ParserState(b"HNHBK:1:3+280+12345'")
    while state.peek() != Token.EOF:
        token = state.peek()
        value = state.consume()
        print(f"{token}: {value}")
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from enum import Enum
from typing import Any

_TOKEN_RE = re.compile(
    rb"""
        ^(?:  (?: \? (?P<ECHAR>.) )
        | (?P<CHAR>[^?:+@']+)
        | (?P<TOK>[+:'])
        | (?: @ (?P<BINLEN>[0-9]+) @ )
    )""",
    re.X | re.S,
)


class Token(Enum):
    """Token types in FinTS wire format."""

    EOF = "eof"
    CHAR = "char"
    BINARY = "bin"
    PLUS = "+"
    COLON = ":"
    APOSTROPHE = "'"


class ParserState:
    """Stateful tokenizer for FinTS wire format.

    Provides peek/consume interface for parsing FinTS data.

    Example:
        state = ParserState(b"HNHBK:1:3+280'")
        state.peek()  # Token.CHAR
        state.consume()  # "HNHBK"
        state.consume(Token.COLON)  # b":"
    """

    def __init__(
        self,
        data: bytes,
        start: int = 0,
        end: int | None = None,
        encoding: str = "iso-8859-1",
    ):
        self._token: Token | None = None
        self._value: Any = None
        self._encoding = encoding
        self._tokenizer = iter(self._tokenize(data, start, end or len(data), encoding))

    def peek(self) -> Token:
        """Look at next token without consuming it."""
        if not self._token:
            self._token, self._value = next(self._tokenizer)
        return self._token

    def consume(self, token: Token | None = None) -> Any:
        """Consume and return the next token value.

        Args:
            token: Expected token type (optional). Raises if mismatch.

        Returns:
            The token's value
        """
        self.peek()
        if token and token != self._token:
            raise ValueError(f"Expected {token}, got {self._token}")
        self._token = None
        return self._value

    @staticmethod
    def _tokenize(
        data: bytes, start: int, end: int, encoding: str
    ) -> Iterator[tuple[Token, Any]]:
        """Tokenize FinTS wire data."""
        pos = start
        unclaimed: list[bytes] = []
        last_was: Token | None = None

        while pos < end:
            match = _TOKEN_RE.match(data[pos:end])
            if match:
                pos += match.end()
                d = match.groupdict()
                if d["ECHAR"] is not None:
                    unclaimed.append(d["ECHAR"])
                elif d["CHAR"] is not None:
                    unclaimed.append(d["CHAR"])
                else:
                    if unclaimed:
                        if last_was in (Token.BINARY, Token.CHAR):
                            raise ValueError("Consecutive char/binary tokens")
                        yield Token.CHAR, b"".join(unclaimed).decode(encoding)
                        unclaimed.clear()
                        last_was = Token.CHAR

                    if d["TOK"] is not None:
                        token = Token(d["TOK"].decode("us-ascii"))
                        yield token, d["TOK"]
                        last_was = token
                    elif d["BINLEN"] is not None:
                        blen = int(d["BINLEN"].decode("us-ascii"), 10)
                        if last_was in (Token.BINARY, Token.CHAR):
                            raise ValueError("Consecutive char/binary tokens")
                        yield Token.BINARY, data[pos : pos + blen]
                        pos += blen
                        last_was = Token.BINARY
                    else:
                        raise ValueError("Unknown token type")
            else:
                raise ValueError(f"Cannot tokenize at position {pos}")

        if unclaimed:
            if last_was in (Token.BINARY, Token.CHAR):
                raise ValueError("Trailing unclaimed data")
            yield Token.CHAR, b"".join(unclaimed).decode(encoding)

        yield Token.EOF, b""


__all__ = [
    "Token",
    "ParserState",
]
