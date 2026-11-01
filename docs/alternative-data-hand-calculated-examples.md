# Alternative-data hand-calculated examples

These synthetic examples are normative AD-2 arithmetic oracles. Amounts use
USD, all records were observed before the decision time, and the feature window
contains three calendar months. Values below are aggregate fictional evidence,
not consumer records or underwriting guidance.

## Cash-flow oracle

Eligible posted events are:

- Month 1: inflows 2,000 and 500; outflow 1,200; ending balance 1,300.
- Month 2: inflow 2,000; outflow 1,500; internal transfer 300; ending balance
  1,500.
- Month 3: inflow 2,200; outflow 1,600; fee 25; outflow 100 followed by an
  explicit full reversal of 100; ending balance 1,975.

The internal transfer contributes to neither inflow nor outflow. The reversed
outflow has net contribution zero. Fees are reported separately and are not
silently merged into spending.

Expected values:

- inflow total = `2,500 + 2,000 + 2,200 = 6,700`;
- outflow total = `1,200 + 1,500 + 1,600 = 4,300`;
- net cash flow = `6,700 - 4,300 - 25 = 2,375`;
- mean monthly inflow = `6,700 / 3 = 2,233.3333333333335`;
- population standard deviation of monthly inflow
  `[2500, 2000, 2200]` = `205.48046676563254`;
- coefficient of variation = `205.48046676563254 /
  2233.3333333333335 = 0.09200617914879068`;
- eligible reversal count = `1`; reversed amount = `100`;
- balance availability = `3 / 3 = 1.0`; and
- negative-balance observation rate = `0 / 3 = 0.0`.

If Month 2 were explicitly a provider reporting gap, three-month coverage would
remain the population denominator, behavioral monthly statistics would be
unavailable under a three-period minimum, and no zero inflow/outflow month would
be invented.

## Rent oracle

The supplied schedule contains three monthly obligations of 1,000 with a
five-day grace rule:

- Month 1: full payment 1,000 on due date.
- Month 2: partial payment 600 on day 3 and remaining 400 on day 8.
- Month 3: explicit provider nonparticipation; no payment behavior is observed.

Only the first two obligations have observable payment evidence. Month 3
remains in coverage evidence with `ad_provider_nonparticipation` and does not
enter an unpaid or late numerator.

Expected values:

- scheduled obligation count = `3` and scheduled amount = `3,000`;
- behavior-observable obligation count = `2`;
- provider coverage rate = `2 / 3 = 0.6666666666666666`;
- fully paid observable count = `2 / 2 = 1.0`;
- paid in full within grace count = `1 / 2 = 0.5`;
- partial-payment-observed count = `1 / 2 = 0.5`;
- observable paid amount = `(1,000 + 1,000) / 2,000 = 1.0`; and
- Month 3 timeliness state = `unavailable`, not late or unpaid.

The Month 2 completion date is day 8, so it is outside grace even though a
partial amount arrived within grace. Timeliness uses the date cumulative linked
payments first meet the adjusted obligation amount.

## Utility oracle

Three electricity bills are explicitly supplied:

- Month 1: bill 100; full payment 100 by due date.
- Month 2: bill 120; partial payment 60 by due date and remaining 60 after due
  date.
- Month 3: estimated bill 80, linked adjustment `-20`, adjusted obligation 60,
  and full payment 60 by due date.

Expected values:

- original billed amount = `100 + 120 + 80 = 300`;
- net adjusted obligation = `100 + 120 + (80 - 20) = 260`;
- total linked payment = `100 + 120 + 60 = 280`;
- fully paid count = `3 / 3 = 1.0`;
- fully paid by due date count = `2 / 3 = 0.6666666666666666`;
- partial-payment-observed count = `1 / 3 = 0.3333333333333333`;
- estimated-bill prevalence = `1 / 3 = 0.3333333333333333`; and
- adjustment prevalence = `1 / 3 = 0.3333333333333333`.

Payment totals may exceed the net adjusted obligation because the Month 2
payment was complete and Month 3 was adjusted. The profile reports both totals;
it does not reinterpret the difference as income, credit, or overpayment. An
explicit service interruption would be contextual evidence only and would not
change these payment-behavior numerators.

## Required fixture assertions

Machine fixtures reproduce every input event, expected numerator, denominator,
value, availability state, and reason code above. Tests must also mutate each
oracle to cover a post-decision observation, a missing schedule/due date, a
broken reversal/obligation link, a currency mismatch, and an unavailable
period. No mutation may serialize entity, record, obligation, account, address,
meter, or permission identifiers into report artifacts or diagnostics.
