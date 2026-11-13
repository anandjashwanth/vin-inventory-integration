# 1. Discovery: who this is for and what problem it solves

## User
**Stock controller at a franchised car dealership.** Adds every new and used vehicle to the dealer management system so it can be priced, advertised and sold.

## Current process (assumed)
1. Vehicle arrives on site.
2. Stock controller reads the VIN from the windscreen or documents.
3. Make, model, year, fuel, engine and body details are typed in by hand, often from the paperwork or the manufacturer's website.

## Pain points (assumed, to validate with users)
| Pain point | Effect on the business |
|---|---|
| Manual typing of 10 to 15 fields per vehicle | Slow stock intake; vehicles wait to be advertised |
| Typos in the VIN itself | Wrong vehicle details, failed lookups later (finance, warranty, recalls) |
| Missing or inconsistent specification | Poor website search results; customers cannot filter correctly |
| No warning when data is incomplete | Problems are found by customers or finance teams, not at intake |

## What success looks like
- Most vehicles are added by entering the VIN only, with details filled automatically.
- Bad VINs are caught at the point of entry, before they reach other systems.
- Incomplete records are flagged for review instead of going live silently.

## Assumptions to test
- [ ] How many vehicles a typical dealer adds per week
- [ ] Which fields matter most for advertising and pricing
- [ ] What share of a UK dealer's stock has European-market VINs

> Status: assumptions based on desk research. [Add notes here from any conversation with dealership staff.]
