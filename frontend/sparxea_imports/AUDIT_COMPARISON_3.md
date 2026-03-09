# Audit Comparison — Iteration 3 vs 2

**Date:** 2026-03-07

## Score

| Metric | Iter 2 | Iter 3 | Delta |
|--------|----------|----------|-------|
| Total issues | 464 | 313 | -151 (32.5%) |
| Diagrams with issues | 160 | 107 | 53 |
| Critical | 0 | 1 | -1 |
| High | 132 | 89 | 43 |
| Medium | 332 | 223 | 109 |
| Low | 0 | 0 | 0 |

## By Issue Type

| Type | Iter 2 | Iter 3 | Delta |
|------|----------|----------|-------|
| api_error | 0 | 1 | +1 |
| missing_packages | 1 | 0 | -1 |
| missing_waypoints | 146 | 101 | -45 |
| node_overlap | 160 | 106 | -54 |
| text_overflow | 157 | 105 | -52 |

## Fixed (4)

- **AIXM_v.5.1.1** [AIXM]: text_overflow — 6 text elements overflow: "XMLSchemaDatatypes"(+55px), "AIXM Data Types"(+15px), "ISO 19107  Geometry"(+43px), "ISO 19115 Metadata"(+41px), "AIXM Abstract Feature"(+57px)
- **AIXM_v.5.1.1** [AIXM]: node_overlap — 11 overlapping pairs:  x ;  x ;  x XMLSchemaDatatypes
- **AIXM_v.5.1.1** [AIXM]: missing_packages — API has 7 package nodes, DOM has 0
- **AIXM_v.5.1.1** [AIXM]: missing_waypoints — 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

## Regressions (1)

- **AIXM_v.5.1.1** [AIXM]: api_error — API error 401 for diagram 34c7d86b-4e36-4872-ac60-e4b513a094da

## Persistent Issues (312)

### node_overlap (106)
- GM_Point_Profile: 1 overlapping pairs:  x GM_Point
- GM_Curve Profile: 8 overlapping pairs:  x GM_Geodesic;  x GM_Circle;  x GM_Arc
- Aggregation: 3 overlapping pairs:  x GM_MultiSurface;  x GM_MultiCurve;  x GM_MultiPoint
- Basic Message: 3 overlapping pairs:  x AIXMFeature;  x BasicMessageMemberAIXM;  x AIXMBasicMessage
- 2 - Surveillance Equipment: 8 overlapping pairs:  x SecondarySurveillanceRadar;  x PrimarySurveillanceRadar;  x SurveillanceGroundStation
- 1 - Surveillance System: 4 overlapping pairs:  x RadarComponent;  x RadarEquipment;  x OrganisationAuthority
- 2 - Obstacle Assessment Associations: 3 overlapping pairs:  x SegmentLeg;  x HoldingAssessment;  x ObstacleAssessmentArea
- 1 - Obstacle Assessment Feature: 6 overlapping pairs:  x Surface;  x ObstacleAssessmentArea;  x AltitudeAdjustment
- 1 - Standard Levels: 6 overlapping pairs:  x AirspaceLayer;  x Airspace;  x StandardLevelSector
- 1 - Properties with Schedule: 4 overlapping pairs:  x SpecialDate;  x OrganisationAuthority;  x Timesheet
- _...and 96 more_

### text_overflow (105)
- GM_Curve Profile: 2 text elements overflow: "GM_GeodesicString"(+33px), "GM_CurveSegment"(+17px)
- Aggregation: 1 text elements overflow: "GM_MultiSurface"(+15px)
- Basic Message: 4 text elements overflow: "+ identifier: CodeUUIDType"(+46px), "«collectionMemberChoice»"(+32px), "BasicMessageMemberAIXM"(+84px), "AIXMBasicMessage"(+32px)
- 2 - Surveillance Equipment: 32 text elements overflow: "+ type: CodeRadioFrequencyAreaType"(+43px), "+ angleScallop: ValAngleType"(+5px), "+ signalType: CodeRadioSignalType"(+36px), "EquipmentChoice"(+7px), "SecondarySurveillanceRadar"(+42px)
- 1 - Surveillance System: 28 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: TextDesignatorType"(+27px)
- 2 - Obstacle Assessment Associations: 22 text elements overflow: "+ finalApproachPath: CodeMinimaFinalAppr"(+59px), "+ requiredNavigationPerformance: CodeRNP"(+9px), "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px)
- 1 - Obstacle Assessment Feature: 20 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px)
- 1 - Standard Levels: 11 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px)
- 1 - Properties with Schedule: 8 text elements overflow: "+ type: CodeSpecialDateType"(+34px), "+ dateDay: DateMonthDayType"(+34px), "+ dateYear: DateYearType"(+15px), "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px)
- 1 - Radio Frequency Limitation: 22 text elements overflow: "+ precisionApproachRadarType: CodePARTyp"(+45px), "SecondarySurveillanceRadar"(+42px), "+ transponder: CodeTransponderType"(+48px), "+ autonomous: CodeYesNoType"(+4px), "+ type: CodeSpecialNavigationStationType"(+58px)
- _...and 95 more_

### missing_waypoints (101)
- GM_Curve Profile: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- Basic Message: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- 2 - Surveillance Equipment: 14/15 edges (93%) have no waypoints — straight-line routing instead of orthogonal
- 1 - Surveillance System: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal
- 2 - Obstacle Assessment Associations: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- 1 - Obstacle Assessment Feature: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- 1 - Standard Levels: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- 1 - Properties with Schedule: 3/4 edges (75%) have no waypoints
- 1 - Radio Frequency Limitation: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- 1 - Light Element: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- _...and 91 more_

