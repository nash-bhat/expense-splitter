"""Pure money logic: equal splits, net balances and settlement. No I/O."""

from collections.abc import Iterable


def split_equally(amount_paise: int, member_ids: list[int]) -> dict[int, int]:
    """Split an amount into equal integer shares that sum exactly to the amount.

    Leftover paise go one each to the lowest member ids, so results are deterministic.
    """
    if not member_ids:
        raise ValueError("cannot split among zero members")
    base, remainder = divmod(amount_paise, len(member_ids))
    return {mid: base + (1 if i < remainder else 0) for i, mid in enumerate(sorted(member_ids))}


def net_balances(
    member_ids: Iterable[int],
    payments: Iterable[tuple[int, int]],
    shares: Iterable[tuple[int, int]],
) -> dict[int, int]:
    """Net balance per member: what they paid minus what they owe.

    `payments` and `shares` are (member_id, paise) pairs. Balances always sum to zero.
    """
    balances = {mid: 0 for mid in member_ids}
    for mid, paise in payments:
        balances[mid] += paise
    for mid, paise in shares:
        balances[mid] -= paise
    return balances


def settle(balances: dict[int, int]) -> list[tuple[int, int, int]]:
    """Return (debtor_id, creditor_id, paise) transfers that zero every balance.

    Greedily pairs the largest debtor with the largest creditor. This needs at most
    n - 1 transfers for n non-zero members; finding the true minimum is NP-hard.
    """
    creditors = sorted(([b, m] for m, b in balances.items() if b > 0), key=lambda x: (-x[0], x[1]))
    debtors = sorted(([-b, m] for m, b in balances.items() if b < 0), key=lambda x: (-x[0], x[1]))
    transfers: list[tuple[int, int, int]] = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        amount = min(debtors[i][0], creditors[j][0])
        transfers.append((debtors[i][1], creditors[j][1], amount))
        debtors[i][0] -= amount
        creditors[j][0] -= amount
        if debtors[i][0] == 0:
            i += 1
        if creditors[j][0] == 0:
            j += 1
    return transfers


def format_rupees(paise: int) -> str:
    """Format paise as rupees, e.g. 12345 -> '₹123.45', 5000 -> '₹50'."""
    rupees, rem = divmod(paise, 100)
    return f"₹{rupees}" if rem == 0 else f"₹{rupees}.{rem:02d}"
