# BSI SMT v3 series root-cause analysis

BSI SMT v3 assigns every imported PDF to NCS, NCTS, or NOAPS from the filename. The importer refuses to guess when none of those series identifiers is present, except for the legacy `Daytona 500` NCS filename.

The recurring-offender engine analyzes each series independently across all imported races. It ranks:

- Vector
- Car number
- Camera serial
- Vector + car
- Camera + vector
- Camera + car
- Camera + position
- Vector + car + camera

For each candidate it calculates sample count, distinct races, low-RT2 race count, average RT2, failure rate, difference from the selected series average, event-adjusted RT2, and an explainable evidence score.

## Evidence score

The ranking score is:

`35 × underperformance + 30 × failure rate + 20 × repeatability + 15 × adverse event-adjusted performance`

All four components are normalized from zero to one. The calculation is displayed on screen. The score is an evidence ranking, not a probability and not proof of physical causation.

## Event adjustment

For every observation:

`event-adjusted RT2 = observation RT2 - average RT2 for that race`

The average event-adjusted score for an offender helps distinguish a recurring assignment/equipment pattern from a race that was difficult for everyone.
