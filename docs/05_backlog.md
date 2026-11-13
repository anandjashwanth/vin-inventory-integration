# 5. Product backlog

Prioritised with MoSCoW (Must, Should, Could, Won't for now). The same stories are tracked in Jira: [add Jira board link or screenshots].

## Epic 1: VIN decode at stock intake
| ID | User story | Priority | Acceptance criteria |
|---|---|---|---|
| 1.1 | As a stock controller, I want to enter a VIN and get the vehicle details filled in, so I do not type them by hand | Must | Make, model, year and fuel are filled for a clean decode |
| 1.2 | As a stock controller, I want a clear message when a VIN is invalid, so I can correct it straight away | Must | Length, character and check-digit errors are shown with the reason |
| 1.3 | As a stock controller, I want to load many vehicles at once, so intake of a delivery is fast | Should | A batch of 50 VINs is processed in one request |

## Epic 2: Data quality
| ID | User story | Priority | Acceptance criteria |
|---|---|---|---|
| 2.1 | As a sales manager, I want incomplete records held for review, so they do not go live with gaps | Must | Records missing any required field go to the exceptions list |
| 2.2 | As a sales manager, I want a summary of decode quality, so I know how much manual work remains | Should | Summary shows clean rate, error codes and missing fields by region |

## Epic 3: UK coverage
| ID | User story | Priority | Acceptance criteria |
|---|---|---|---|
| 3.1 | As a UK stock controller, I want European vehicles decoded fully, so I do not type their details by hand | Should (v2) | A UK data source fills required fields for vehicles the US source cannot decode |

## Epic 4: Customer value
| ID | User story | Priority | Acceptance criteria |
|---|---|---|---|
| 4.1 | As a sales manager, I want to know about open recalls at intake, so we fix them before sale | Could (v3) | Open recalls listed for each decoded vehicle |
| 4.2 | As a sales executive, I want a draft listing description, so advertising is faster | Could (v3) | AI drafts a description from decoded fields only; a person approves it before it is published |
