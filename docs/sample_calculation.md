# Hand-Calculated Journal Example

All figures below are fictional; prices are VND per share and each quantity is 100 shares. Fees are zero so the weighted-average calculation is easy to verify.

| ID | Date | Ticker | Side | Price | Qty | What happens |
|---|---|---|---|---:|---:|---|
| S01 | 2026-01-05 | FPT | BUY | 100 | 100 | Open position |
| S02 | 2026-01-05 | FPT | BUY | 110 | 100 | Add to position |
| S03 | 2026-01-06 | FPT | SELL | 120 | 100 | Partial close, win |
| S04 | 2026-01-07 | FPT | BUY | 90 | 100 | Add after partial sell |
| S05 | 2026-01-08 | FPT | SELL | 90 | 100 | Partial close, loss |
| S06 | 2026-01-09 | FPT | BUY | 100 | 100 | Add to position |
| S07 | 2026-01-12 | FPT | SELL | 110 | 100 | Partial close, win |
| S08 | 2026-01-13 | FPT | SELL | 95 | 100 | Close the remaining FPT shares, loss |
| S09 | 2026-01-14 | MWG | BUY | 50 | 100 | Open position |
| S10 | 2026-01-15 | MWG | BUY | 60 | 100 | Add to position |

## Calculations

1. After S01 and S02, FPT average cost = `(100 × 100 + 110 × 100) / 200 = 105`.
2. S03 realized P&L = `(120 - 105) × 100 = +1,500`; 100 shares remain at cost 105.
3. After S04, average cost = `(105 × 100 + 90 × 100) / 200 = 97.5`.
4. S05 realized P&L = `(90 - 97.5) × 100 = -750`; 100 shares remain at cost 97.5.
5. After S06, average cost = `(97.5 × 100 + 100 × 100) / 200 = 98.75`.
6. S07 realized P&L = `(110 - 98.75) × 100 = +1,125`; 100 shares remain at cost 98.75.
7. S08 realized P&L = `(95 - 98.75) × 100 = -375`; FPT position is zero.
8. MWG ending quantity = 200; average cost = `(50 + 60) / 2 = 55`.

## Expected outputs

| Metric | Expected |
|---|---:|
| FPT ending quantity | 0 shares |
| MWG ending quantity / average cost | 200 shares / 55 VND |
| Realized P&L | +1,500 VND |
| Winning / losing sell events | 2 / 2 |
| Closed sell events / win rate | 4 / 50% |
| Average win / average loss | 1,312.50 / 562.50 VND |
| Profit factor | `2,625 / 1,125 = 2.3333` |
| Expectancy per sell event | `50% × 1,312.50 − 50% × 562.50 = 375 VND` |
| Maximum drawdown of cumulative realized P&L | 750 VND (50% of the 1,500 VND peak) |

Sell-event statistics group each sell as one observation. A partial sell can differ from treating the investor's entire thesis as one completed trade, so the dashboard also reports completed-position-cycle statistics separately.

## Completed-position-cycle statistics

The dashboard also follows the specification's completed-trade definition: one cycle starts with the first BUY after a zero position and ends only when the ticker's position returns to zero. Adding to a position and partial sells stay inside the same cycle. Open positions are excluded from completed-cycle win rate and expectancy.

In this sample, S01–S08 form one completed FPT cycle. Its realized P&L is `+1,500 VND`, so the completed-cycle win rate is `1 / 1 = 100%`, average win and expectancy are `1,500 VND`, and profit factor is infinite because there are no losing completed cycles. Risk amounts recorded by the four sell events are 1,000, 750, 875, and 875 VND; cycle R-multiple is `1,500 / 3,500 = 0.43R` (rounded). MWG remains open after S10 and is excluded. The separate sell-event view still reports 4 sell events, a 50% win rate, profit factor `2.3333`, and expectancy `375 VND` per sell event. These two views answer different questions and are labeled separately in the dashboard.
