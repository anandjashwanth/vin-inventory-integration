# 6. Roadmap

| Version | Goal | Scope | Success measure |
|---|---|---|---|
| **v1 (built)** | Prove the integration and catch bad data early | Local VIN checks, batch decode, field mapping, validation, exceptions file, quality summary | Share of VINs loaded clean without manual entry |
| **v2 (next)** | Close the coverage gaps | Add a UK source for European-market vehicles, for example the DVLA Vehicle Enquiry Service (looks up by registration number; needs a free API key), and a specification source for transmission, drive type and trim | Clean rate for European-market VINs; share of listings with transmission filled |
| **v3 (later)** | Add value for customers and sales teams | Recall check through NHTSA's recalls API; AI-drafted listing description from decoded fields with human approval | Recalls caught before sale; time to advertise a vehicle |

## Decision behind v2
The v1 run on 200 vehicles loaded 95% clean, but two gaps matter more than new features:
- **Listing detail:** transmission was missing for 87% of vehicles and drive type for 57%. Customers filter on both.
- **UK market:** a European-market VIN failed in testing, and the US-market test data cannot show how widespread this is for a UK dealer.

Fixing these improves every vehicle a dealer lists, so they come before recalls or AI features.

## What would change at production scale
- Host NHTSA's downloadable vPIC database instead of calling the live API, removing the dependency on a free service with no uptime guarantee.
- Monitor error-code rates over time and alert when they rise.
- Store the raw API response alongside the mapped record, so every field can be traced back to its source.
