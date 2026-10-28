# CampusCore / LabCommons Fairness Rules

## 1. Monthly hourly quotas by user tier

| User tier | Monthly quota |
|---|---:|
| Admin | 80 hours |
| Lab_Manager | 120 hours |
| Faculty | 100 hours |
| PostDoc | 70 hours |
| Student_Grad | 40 hours |
| Student_UG | 24 hours |
| Incubator_Founder | 32 hours |

Quota applies to booked resource hours, not calendar time between bookings. A booking in `Approved` or `In_Custody` reserves quota; on transition to `Returned_Clean`, actual used hours are posted. A cancelled or rejected request consumes no hours. A manager may document an exception, but cannot silently bypass safety prerequisites. `used_quota_hours` is the current monthly snapshot and should be reconciled with completed custody records.

## 2. Dynamic waitlist priority

For waitlist arbitration, compute:

`Priority = (Academic_Weight * 0.4) + ((Monthly_Quota - Used_Hours) * 0.35) - (Strikes * 15) + (Days_Since_Last_Booking * 0.25)`

- `Academic_Weight` is an institution-approved urgency value from 0 to 100 (e.g. thesis milestone, grant deliverable, scheduled sample window).
- `Monthly_Quota` and `Used_Hours` are the user's quota and consumed hours at the time of arbitration.
- `Strikes` is the count of active penalty strikes at that time.
- `Days_Since_Last_Booking` is the number of full days since the user's last completed booking; use 30 for a user with no prior booking.
- Clamp the result to 0–100 after applying the formula. Store the calculated score and an explainable reason in `waitlist.csv`. If scores tie, prefer the earlier request timestamp, then the user with fewer strikes. Never use protected personal characteristics.

## 3. Anti-hoarding and equipment-group limits

- A user may consume no more than **4 peak-time hours per rolling week per equipment group**. Peak time is 10:00–16:00 local time on institutional working days.
- A user may hold at most one active booking per resource and at most two active bookings across all resources.
- Power users at or above 90% of their monthly quota are deprioritised for discretionary waitlist slots unless the request is tied to a documented critical academic deadline.
- A no-show or unresolved damage incident triggers a review flag, not an automatic fine. A Lab_Manager or Admin must record any proposed penalty and its rationale in the audit trail.
- For supervised assets, the assigned manager or delegated expert must be present throughout the session. Expired, revoked, or pending-review certificates do not satisfy eligibility.
- Approved bookings may not overlap on the same resource. Waitlisted requests may overlap by definition but cannot be promoted until a conflict is cleared.
