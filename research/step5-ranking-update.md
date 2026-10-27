# Step 5: Ranking update and decisions

Two observations from the Step 4 staging table were incorporated into the application's evidence catalogue:

- R001 → B13 / P13 / E018: study-specific graphene oxide and sulfamethoxazole. The abstract's up-to value is an upper bound, with insufficient information for an exact operating point.
- R002 → B14 / P14 / E019: study-specific nZVI and sulfamethoxazole. The 83–91% range is kept as a range, not a single measured result or guaranteed removal.

Both records are specific to the described study profiles, require the user to accept study profiles, and remain conditional because illumination requirements and recovery details are not established in the reviewed abstract. Unknown ratings span their full ranges. They never receive a TiO₂ ML prediction, and their reported outcomes do not become decision scores.

Ranking target matching now rejects qualified results, including upper bounds, maximums and reported ranges, as proof of an exact removal target. A matching target must be supported by an unqualified removal-percent endpoint with all five operating inputs and the laboratory-solution assumption matching. This is still an evidence-policy match, not independent validation.

The other 16 staged rows remain on hold. Composite and setup requirements, unsupported arsenic/chromium species, nanoclay dimensions and source discrepancies are not silently assigned or generalized. The saved model and training data were not changed.

The catalogue now covers 13 of 45 family–pollutant pairs across three supported pollutants. With preset assumptions and the default priorities, UV SMX yields M02, M03, M05, M06 and M08 in the first interval tier; no unique winner is justified. Dark SMX leaves M05, M06 and M08 conditional; the abstracts for M05/M06 do not establish a light requirement. The lead preset still selects M13 under its documented source-matched setup.

Automated tests cover the new profile boundaries, unknown setup and recovery, exact target restrictions, source range preservation, custom weights and API behavior. Historical saved report and notebook outputs reflect their earlier catalogue snapshot and should not be treated as current live results.
