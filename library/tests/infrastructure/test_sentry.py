from library.infrastructure.sentry import normalize_error_message


def test_normalize_error_message_collapses_uuids_indices_and_quoted_text() -> None:
    first = normalize_error_message(
        "Failed to send 1 objects in a batch of 35, index=11, "
        "uuid='019ef82b-1234-4abc-89de-0123456789ab', text='Moving a candidate forward'"
    )
    second = normalize_error_message(
        "Failed to send 3 objects in a batch of 50, index=4, "
        "uuid='abcd0000-9999-4def-81ab-fedcba987654', text='An entirely different fact'"
    )

    assert first == second


def test_normalize_error_message_keeps_distinct_errors_distinct() -> None:
    expired = normalize_error_message(
        "Firestore rejected the transaction as invalid: 400 The referenced transaction has expired "
        "or is no longer valid."
    )
    not_found = normalize_error_message("Firestore rejected the transaction as invalid: 404 Document not found.")

    assert expired != not_found


def test_normalize_error_message_strips_hex_and_bare_numbers() -> None:
    assert normalize_error_message("connection refused at 0xDEADBEEF after 12 attempts") == normalize_error_message(
        "connection refused at 0x00000000 after 3 attempts"
    )
