"""MT940 parsing utilities for FinTS transaction data."""

import mt940


def mt940_to_array(data: str):
    """Parse MT940 data into transaction objects."""
    data = data.replace("@@", "\r\n")
    data = data.replace("-0000", "+0000")
    transactions = mt940.models.Transactions()
    return transactions.parse(data)


def decode_phototan_image(data: bytes) -> dict:
    """Decode photoTAN data into its mime type and image data.

    Format from: https://github.com/hbci4j/hbci4java/blob/master/src/main/java/org/kapott/hbci/manager/MatrixCode.java
    """
    # Mime type length is the first two bytes of data
    mime_type_length = int.from_bytes(data[:2], byteorder="big")

    # The mime type follows from byte three to (mime_type_length - 1)
    mime_type = data[2 : 2 + mime_type_length].decode("iso-8859-1")

    # The image length is coded in the next two bytes
    image_length_start = 2 + mime_type_length
    image_length = int.from_bytes(
        data[image_length_start : 2 + image_length_start], byteorder="big"
    )

    # The actual image data is everything that follows.
    image = data[2 + image_length_start : 2 + image_length_start + image_length]

    return {
        "mime_type": mime_type,
        "image": image,
    }


__all__ = ["decode_phototan_image", "mt940_to_array"]
