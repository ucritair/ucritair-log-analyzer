# AQI Standards Sources (PM-only packs)

These packs use PM2.5/PM10 breakpoints only. When a standard normally combines
other pollutants (e.g., ozone), we compute only the PM sub-index.

## Standards + primary sources

- US EPA AQI (legacy, pre-2024 PM2.5 update)  
  AirNow Technical Assistance Document (EPA-454/B-18-007, Sep 2018)  
  https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf

- US EPA AQI (2024 PM2.5 update)  
  Federal Register final rule (revisions to AQI for PM2.5)  
  https://www.federalregister.gov/documents/2024/02/07/2024-01910/revisions-to-the-air-quality-index-aqi-for-particulate-matter

- EU EEA Air Quality Index (EAQI)  
  EEA methodology and threshold table  
  https://www.eea.europa.eu/en/analysis/indicators/air-quality-index

- WHO Air Quality Guidelines 2021  
  WHO publication page (PDF linked on page)  
  https://www.who.int/publications/i/item/9789240034228

- UK Defra Daily Air Quality Index (DAQI)  
  UK Air guidance page with PM2.5/PM10 bands  
  https://uk-air.defra.gov.uk/air-pollution/daqi?view=more-info

- India CPCB National Air Quality Index (NAQI)  
  CPCB official NAQI page  
  https://cpcb.nic.in/National-Air-Quality-Index/

- China MEE AQI (HJ 633-2012)  
  Ministry of Ecology and Environment standards portal  
  https://www.mee.gov.cn/

## Notes

- These packs intentionally use PM2.5/PM10 only.  
- Standards with discrete bands (EU EEA, WHO, UK DAQI) are implemented as
  banded indices (one value per band).  
- EPA AQI packs apply PM2.5/PM10 concentration truncation before computing
  sub-indices.
