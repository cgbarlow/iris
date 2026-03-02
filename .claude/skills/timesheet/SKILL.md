---
name: timesheet
description: "Interactive timesheet entry — collects work description, start/end times via prompts, calculates hours, appends to .campaign/timesheet.md"
user_invocable: true
---

# /timesheet

Update the project timesheet at `.campaign/timesheet.md`.

## Instructions

1. Read the current timesheet from `.campaign/timesheet.md`
2. Use `AskUserQuestion` to collect the following for each entry:
   - **Description**: What work was done
   - **Start time**: When work started (e.g. "9:00 AM", "14:30")
   - **End time**: When work ended (e.g. "11:30 AM", "17:00")
3. Calculate the hours as the difference between end time and start time, rounded to 2 decimal places
4. Append the new row to the markdown table in `.campaign/timesheet.md`
5. Display the updated timesheet to the user

## Weekly Summary Maintenance

Every time an entry is added, edited, or removed, recalculate the Weekly Summary table. Weeks are identified by their **Monday** start date (ISO week, Mon–Sun). The total hours line below the weekly summary must always equal the sum of all entry hours.

**Calculating the week-starting Monday for a date:**
- Monday → the date itself
- Tuesday → date − 1 day
- Wednesday → date − 2 days
- Thursday → date − 3 days
- Friday → date − 4 days
- Saturday → date − 5 days
- Sunday → date − 6 days

For example, Sunday 2026-03-01 belongs to the week starting Monday 2026-02-23 (subtract 6 days). Monday 2026-03-02 starts a new week. Always use this calculation — do NOT treat the entry date itself as the week start.

## Timesheet Template

If `.campaign/timesheet.md` does not exist, create it with this content:

```markdown
# Timesheet

## How to update

Run `/timesheet` in Claude Code to add entries, or use clock in/out:
- `/timesheet clock in` — starts a new entry at the current time
- `/timesheet clock out` — ends the open entry and prompts for a description
- `/timesheet` — manually add an entry (date, description, start/end times)

Timezone: (ask user)

---

## Weekly Summary

| Week Starting | Hours |
|---------------|-------|

**Total: 0.00 hours**

---

## Entries

| Date       | Description | Start Time | End Time | Hours |
|------------|-------------|------------|----------|-------|
```
