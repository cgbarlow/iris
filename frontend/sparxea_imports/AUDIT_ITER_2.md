# EA Visual Audit — Iteration 2

**Date:** 2026-03-07
**Iteration:** 2 of 3
**Diagrams audited:** 163
**Diagrams with issues:** 160
**Total issues:** 464
**By severity:** critical=0, high=132, medium=332, low=0

## Summary by Issue Type

| Issue Type | Count | Severity |
|-----------|-------|----------|
| node_overlap | 160 | medium |
| text_overflow | 157 | medium |
| missing_waypoints | 146 | high |
| missing_packages | 1 | medium |

---

## AIXM

### GM_Point_Profile (id: `df71bd2f-ce9c-40db-9cca-c70c96034d9f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 1 overlapping pairs:  x GM_Point

**Correct:** Node count: 1, Edge count: 0, No content clipping, 20 links/cross-references detected, All nodes have bgColor

### GM_Curve Profile (id: `bd38fe07-c4f6-4abe-9438-f2c47992f52a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "GM_GeodesicString"(+33px), "GM_CurveSegment"(+17px)
- [medium] **node_overlap**: 8 overlapping pairs:  x GM_Geodesic;  x GM_Circle;  x GM_Arc
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 4 (1 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### Aggregation (id: `94d97fab-0bc1-4319-b767-7f12cd811c2b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "GM_MultiSurface"(+15px)
- [medium] **node_overlap**: 3 overlapping pairs:  x GM_MultiSurface;  x GM_MultiCurve;  x GM_MultiPoint

**Correct:** Node count: 3, Edge count: 0, No content clipping, 22 links/cross-references detected, All nodes have bgColor

### Basic Message (id: `480e5201-a435-4ae4-9c8c-5149ae0a3373`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ identifier: CodeUUIDType"(+46px), "«collectionMemberChoice»"(+32px), "BasicMessageMemberAIXM"(+84px), "AIXMBasicMessage"(+32px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AIXMFeature;  x BasicMessageMemberAIXM;  x AIXMBasicMessage
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 4 (2 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### 2 - Surveillance Equipment (id: `cf2ca016-c891-4c89-b3fb-2ddd52035a82`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "+ type: CodeRadioFrequencyAreaType"(+43px), "+ angleScallop: ValAngleType"(+5px), "+ signalType: CodeRadioSignalType"(+36px), "EquipmentChoice"(+7px), "SecondarySurveillanceRadar"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x SecondarySurveillanceRadar;  x PrimarySurveillanceRadar;  x SurveillanceGroundStation
- [high] **missing_waypoints**: 14/15 edges (93%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 15, No content clipping, Edge labels found: 30 (9 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### 1 - Surveillance System (id: `cf5c38df-71f1-4913-ab2c-a4df91bd9602`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: TextDesignatorType"(+27px)
- [medium] **node_overlap**: 4 overlapping pairs:  x RadarComponent;  x RadarEquipment;  x OrganisationAuthority
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 10, No content clipping, Edge labels found: 27 (10 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 2 - Obstacle Assessment Associations (id: `c2e5af5f-a422-4110-aa47-85dbcdeac4d4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ finalApproachPath: CodeMinimaFinalAppr"(+59px), "+ requiredNavigationPerformance: CodeRNP"(+9px), "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SegmentLeg;  x HoldingAssessment;  x ObstacleAssessmentArea
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 18 (6 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Obstacle Assessment Feature (id: `ddab2b47-b69e-4e0e-a8e0-8e621109d56b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 20 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px)
- [medium] **node_overlap**: 6 overlapping pairs:  x Surface;  x ObstacleAssessmentArea;  x AltitudeAdjustment
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 1 - Standard Levels (id: `5328386a-2a46-43f6-aad6-3c386999d9bb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px)
- [medium] **node_overlap**: 6 overlapping pairs:  x AirspaceLayer;  x Airspace;  x StandardLevelSector
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Properties with Schedule (id: `41cc7157-cc20-4c86-a2b1-245a729d758f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ type: CodeSpecialDateType"(+34px), "+ dateDay: DateMonthDayType"(+34px), "+ dateYear: DateYearType"(+15px), "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px)
- [medium] **node_overlap**: 4 overlapping pairs:  x SpecialDate;  x OrganisationAuthority;  x Timesheet
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 9 (4 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 1 - Radio Frequency Limitation (id: `96cf8a48-b109-401e-823f-fb7863373b53`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ precisionApproachRadarType: CodePARTyp"(+45px), "SecondarySurveillanceRadar"(+42px), "+ transponder: CodeTransponderType"(+48px), "+ autonomous: CodeYesNoType"(+4px), "+ type: CodeSpecialNavigationStationType"(+58px)
- [medium] **node_overlap**: 8 overlapping pairs:  x SecondarySurveillanceRadar;  x SpecialNavigationStation;  x NavaidEquipment
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 8, No content clipping, Edge labels found: 24 (3 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 1 - Light Element (id: `213f65c9-9d9e-4da5-a629-8f434c552e98`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "PropertiesWithSchedule"(+47px), "+ status: CodeStatusOperationsType"(+56px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 4 overlapping pairs:  x PropertiesWithSchedule;  x LightElementStatus;  x ElevatedPoint
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 2 - Flight Characteristics (id: `1da1e7aa-d778-45d9-82d1-1893f52b9b93`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ rule: CodeFlightRuleType"(+13px), "+ status: CodeFlightStatusType"(+38px), "+ military: CodeMilitaryStatusType"(+63px), "+ origin: CodeFlightOriginType"(+38px), "+ purpose: CodeFlightPurposeType"(+50px)
- [medium] **node_overlap**: 1 overlapping pairs:  x FlightCharacteristic

**Correct:** Node count: 1, Edge count: 0, No content clipping, 23 links/cross-references detected, All nodes have bgColor

### 1 - Aircraft Characteristics (id: `810c03e0-7fcc-4b2f-b28f-816299f795f9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px)
- [medium] **node_overlap**: 1 overlapping pairs:  x AircraftCharacteristic

**Correct:** Node count: 1, Edge count: 0, No content clipping, 23 links/cross-references detected, All nodes have bgColor

### 1 - Address (id: `ceae8271-caa4-4085-b695-02771badf8c8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "TelephoneContact"(+9px), "+ voice: TextPhoneType"(+18px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ContactInformation;  x TelephoneContact;  x OnlineContact
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 6, No content clipping, Edge labels found: 9 (3 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### 7 - Search and Rescue Services (id: `fc082fdc-2897-4982-b583-6bcf53081441`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px), "+ upperLowerSeparation: ValFLType"(+13px), "SearchRescueService"(+27px), "+ type: CodeServiceSARType"(+36px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RoutePortion;  x Airspace;  x SearchRescueService
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### 6 - Air Traffic Management (id: `aae4a9b1-464a-4323-b3d9-abc94e3de0df`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "+ designatorPrefix: CodeAerialRefuelling"(+82px), "+ designatorSuffix: TextDesignatorType"(+7px), "+ designatorDirection: CodeCardinalDirec"(+69px), "+ receiverChannel: CodeTACANChannelType"(+13px), "+ reverseDirectionTurn: CodeDirectionTur"(+51px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AerialRefuelling;  x Airspace;  x AirTrafficManagementService
- [medium] **missing_waypoints**: 4/5 edges (80%) have no waypoints

**Correct:** Node count: 4, Edge count: 5, No content clipping, Edge labels found: 12 (5 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 5 - Air Traffic Control Services (id: `4b4bb5ef-07bf-451d-931f-85380fcb52e6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ turnDirection: CodeDirectionTurnType"(+6px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 6 overlapping pairs:  x AerialRefuelling;  x Airspace;  x AirTrafficControlService
- [high] **missing_waypoints**: 11/12 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 12, No content clipping, Edge labels found: 27 (10 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 4 - Information Service (id: `5cdd1b11-c100-4e0a-af95-2629f8a9c806`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ turnDirection: CodeDirectionTurnType"(+6px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 5 overlapping pairs:  x AirportHeliport;  x Airspace;  x AerialRefuelling
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 10, No content clipping, Edge labels found: 27 (10 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 3 - Airport Ground Services (id: `e866c49b-0d4f-4b88-aade-6cfe6474200a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ type: CodeOxygenType"(+31px), "+ type: CodeNitrogenType"(+39px), "+ category: CodeOilType"(+38px), "+ category: CodeFuelType"(+38px), "+ jetwayAvailability: CodeYesNoType"(+23px)
- [medium] **node_overlap**: 12 overlapping pairs:  x Oxygen;  x Nitrogen;  x Oil
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 11, No content clipping, Edge labels found: 18 (6 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### 2 - Communication Channel (id: `c3e4be88-4bb3-444d-9ea3-f3ca9197f735`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 20 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeRadioFrequencyAreaType"(+43px), "+ angleScallop: ValAngleType"(+5px), "+ signalType: CodeRadioSignalType"(+36px), "EquipmentChoice"(+7px)
- [medium] **node_overlap**: 7 overlapping pairs:  x RadioCommunicationOperationalStatus;  x PropertiesWithSchedule;  x ElevatedPoint
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 27 (8 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 1 - Service Overview (id: `feb04d91-351a-43d4-8b86-d38be684ce71`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "AirportClearanceService"(+36px), "+ snowPlan: TextInstructionType"(+54px), "AirportSuppliesService"(+60px), "+ category: CodeFireFightingType"(+23px), "+ standard: CodeAviationStandardsType"(+54px)
- [medium] **node_overlap**: 11 overlapping pairs:  x PassengerService;  x AirTrafficManagementService;  x GroundTrafficControlService
- [high] **missing_waypoints**: 20/22 edges (91%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 19, Edge count: 22, No content clipping, Edge labels found: 24 (10 edges have label data), 40 links/cross-references detected, All nodes have bgColor

### 1 - RulesProcedures (id: `5d71d75c-8400-43ce-9a57-7b8e79b9475e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px), "+ upperLowerSeparation: ValFLType"(+13px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px)
- [medium] **node_overlap**: 3 overlapping pairs:  x Airspace;  x AirportHeliport;  x RulesProcedures
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### 3 - Flight restriction - routings (id: `ad9fcf28-384d-4de6-b32b-409e75241e69`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px), "+ contingencyRoute: CodeYesNoType"(+15px), "StandardInstrumentArrival"(+4px), "+ designator: TextSIDSTARDesignatorType"(+53px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DirectFlightSegment;  x SignificantPoint;  x RoutePortion
- [medium] **missing_waypoints**: 12/18 edges (67%) have no waypoints

**Correct:** Node count: 11, Edge count: 18, No content clipping, Edge labels found: 51 (12 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### 2 - Flight restrictions - conditions (id: `d4f72f35-1b41-46ad-bc33-bc32eda16f26`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 36 text elements overflow: "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px), "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px), "+ contingencyRoute: CodeYesNoType"(+15px)
- [medium] **node_overlap**: 10 overlapping pairs:  x DirectFlightClass;  x DirectFlight;  x SignificantPoint
- [medium] **missing_waypoints**: 24/33 edges (73%) have no waypoints

**Correct:** Node count: 20, Edge count: 33, No content clipping, Edge labels found: 87 (23 edges have label data), 42 links/cross-references detected, All nodes have bgColor

### 1 - Flight Restrictions (id: `3a188194-35a1-43c6-9102-f2c3f137a8c7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "+ speedReference: CodeSpeedReferenceType"(+44px), "+ speedCriteria: CodeComparisonType"(+13px)
- [medium] **node_overlap**: 9 overlapping pairs:  x FlightRoutingElement;  x FlightRestrictionRoute;  x FlightRestrictionLevel
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 30 (10 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 6 - Route Portion DME (id: `a3a2472c-e8e9-4044-9604-febc602c4c2c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ channel: CodeDMEChannelType"(+16px), "+ ghostFrequency: ValFrequencyType"(+48px), "+ displace: ValDistanceType"(+4px), "+ criticalDME: CodeYesNoType"(+40px), "+ satisfactory: CodeYesNoType"(+46px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RoutePortion;  x DME;  x RouteDME
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 5 - Route Portion Change Over Points (id: `2710be90-2315-4d69-95c2-7e1284f4f8b6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "ChangeOverPoint"(+5px), "+ distance: ValDistanceType"(+48px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SignificantPoint;  x RoutePortion;  x ChangeOverPoint
- [medium] **missing_waypoints**: 2/5 edges (40%) have no waypoints

**Correct:** Node count: 3, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 4 - Route Availability (id: `b7b952f6-3a49-4453-b88d-295eda73bec9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ unitOfMeasurement: CodeDistanceVertica"(+83px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ designatorPrefix: CodeAerialRefuelling"(+82px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AirspaceLayer;  x RouteSegment;  x PropertiesWithSchedule
- [high] **missing_waypoints**: 5/6 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 12 (5 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 3 - Route Portion (id: `17a2945b-b4ea-4ace-af6a-050b3a2bd639`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px), "+ designatorSuffix: CodeRouteDesignatorS"(+9px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RouteSegment;  x DesignatedPoint;  x Navaid
- [medium] **missing_waypoints**: 4/7 edges (57%) have no waypoints

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 21 (5 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 2 - Route Segment (id: `6df97799-4aec-4018-ab9a-bca6fd1f5d5a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ reportingATC: CodeATCReportingType"(+44px), "+ radarGuidance: CodeYesNoType"(+7px), "+ roleMilitaryTraining: CodeMilitaryRout"(+81px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px)
- [medium] **node_overlap**: 5 overlapping pairs:  x EnRouteSegmentPoint;  x Curve;  x ObstacleAssessmentArea
- [high] **missing_waypoints**: 6/7 edges (86%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 18 (6 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Routes (id: `cc47c954-5554-4276-af54-36d33d393043`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px), "+ designatorSuffix: CodeRouteDesignatorS"(+9px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RouteSegment;  x OrganisationAuthority;  x Route
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 9 (4 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### XMLSchemaDatatypes (id: `e034163f-2c11-4892-9dc2-4c96684ddb5a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "normalizedString"(+3px), "anySimpleType"(+3px), "anyAtomicType"(+4px), "+ fractionDigits: null"(+32px), "nonNegativeInteger"(+39px)
- [medium] **node_overlap**: 18 overlapping pairs:  x string;  x token;  x ENTITIES

**Correct:** Node count: 47, Edge count: 46, No content clipping, 66 links/cross-references detected, All nodes have bgColor

### Temp (id: `32e8cd37-17c4-4faa-a1ca-6e4e1ad6c406`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "CodeBuoyDesignatorBaseType"(+97px), "CodeBuoyDesignatorType"(+27px), "+ nilReason: NilReasonEnumeration"(+48px), "AlphanumericType"(+17px), "CodeICAOCountryBaseType"(+88px)
- [medium] **node_overlap**: 10 overlapping pairs:  x CodeBuoyDesignatorBaseType;  x CodeBuoyDesignatorType;  x string
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 12, No content clipping, 34 links/cross-references detected, All nodes have bgColor

### GM_Surface Profile (id: `4c4ee827-b1a7-4722-9b70-62637589a345`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "GM_SurfacePatch"(+5px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ;  x ;  x GM_Polygon
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 5, No content clipping, Edge labels found: 4 (1 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### 3 - Segment Leg (id: `f94c196c-a909-401c-91e6-3bedfb742e9f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 33 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ indicationDirection: CodeDirectionRefe"(+59px), "+ cardinalDirection: CodeCardinalDirecti"(+40px), "+ minimumReceptionAltitude: ValDistanceV"(+71px), "+ minimumReceptionAltitude: ValDistanceV"(+71px)
- [medium] **node_overlap**: 7 overlapping pairs:  x DepartureLeg;  x ApproachLeg;  x AircraftCharacteristic
- [high] **missing_waypoints**: 13/15 edges (87%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 15, No content clipping, Edge labels found: 33 (11 edges have label data), 35 links/cross-references detected, All nodes have bgColor

### 2 - Restricted Navigation (id: `b96a49c6-78ac-46fc-a4f0-35cbaa1ed051`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px)
- [medium] **node_overlap**: 5 overlapping pairs:  x Procedure;  x CircleSector;  x Surface
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### 1 - Overview (id: `80264cf3-6ab9-4b4a-aa3b-f2174c98b1c7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 26 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ requiredNavigationPerformance: CodeRNP"(+53px), "+ minimumObstacleClearanceAltitude: ValD"(+80px), "+ courseReversalInstruction: TextInstruc"(+3px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DepartureLeg;  x StandardInstrumentDeparture;  x ProcedureTransitionLeg
- [high] **missing_waypoints**: 16/17 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 14, Edge count: 17, No content clipping, Edge labels found: 33 (11 edges have label data), 36 links/cross-references detected, All nodes have bgColor

### 1- Minimum and Emergency Safe Altitude (id: `e6cd22e6-30b2-4be1-8af1-2b6b36a0412e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ altitudeAdjustmentType: CodeAltitudeAd"(+71px), "+ altitudeAdjustment: ValDistanceVertica"(+28px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AltitudeAdjustment;  x Surface;  x SafeAltitudeAreaSector
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 11, No content clipping, Edge labels found: 30 (9 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 5 - Navigation System Checkpoint (id: `e86909f3-547b-4959-b023-405086858c8a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: CodeNavaidDesignatorType"(+22px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NavaidEquipment;  x VOR;  x CheckpointVOR
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 15 (5 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 4 - Special Navigation System (id: `777383c3-5e9b-459b-9086-b88feaebc2ea`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "PropertiesWithSchedule"(+47px), "SpecialNavigationStationStatus"(+34px), "+ operationalStatus: CodeStatusNavaidTyp"(+60px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px)
- [medium] **node_overlap**: 7 overlapping pairs:  x SpecialNavigationStationStatus;  x ElevatedPoint;  x AuthorityForSpecialNavigationSystem
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 18 (7 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 3 - Navaid Limitation (id: `843ebd28-2391-487d-ac70-c829a0e0461f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ type: CodeSpecialNavigationStationType"(+58px), "+ emission: CodeRadioEmissionType"(+14px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x SpecialNavigationStation;  x NavaidEquipment
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 18 (3 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 2 - Navaid Equipment (id: `cf6312d4-79d1-4e92-937d-effe0f2d6279`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 38 text elements overflow: "+ trueBearingAccuracy: ValAngleType"(+39px), "+ magneticBearing: ValBearingType"(+26px), "+ angleProportionalLeft: ValAngleType"(+51px), "+ angleProportionalRight: ValAngleType"(+58px), "+ angleCoverLeft: ValAngleType"(+8px)
- [medium] **node_overlap**: 8 overlapping pairs:  x NDB;  x MarkerBeacon;  x TACAN
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 11, No content clipping, 34 links/cross-references detected, All nodes have bgColor

### 1 - ProcedureUsage (id: `a85786ff-9d6a-4430-a504-578441bfbdd9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "PropertiesWithSchedule"(+47px), "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ status: CodeProcedureAvailabilityType"(+66px)
- [medium] **node_overlap**: 3 overlapping pairs:  x PropertiesWithSchedule;  x Procedure;  x ProcedureAvailability
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 3 (1 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 6 - Segment Leg DME (id: `419a4c36-faf2-49ff-8bad-9131838f8d9a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ endConditionDesignator: CodeSegmentTer"(+59px), "+ courseDirection: CodeDirectionReferenc"(+16px), "+ upperLimitAltitude: ValDistanceVertica"(+16px), "+ upperLimitReference: CodeVerticalRefer"(+34px), "+ lowerLimitAltitude: ValDistanceVertica"(+16px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SegmentLeg;  x DME;  x ProcedureDME
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 5 - LandingTakeOffArea (id: `509a71ae-46d5-430e-9b65-9e672d2dac11`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ approachMarkingCondition: CodeMarkingC"(+50px), "+ precisionApproachGuidance: CodeApproac"(+57px), "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px)
- [medium] **node_overlap**: 6 overlapping pairs:  x TouchDownLiftOff;  x RunwayDirection;  x StandardInstrumentDeparture
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 4 - SegmentLegSpecialization (id: `f7c2308d-2280-490d-a84b-34d50684036a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 34 text elements overflow: "TerminalSegmentPoint"(+16px), "+ role: CodeProcedureFixRoleType"(+52px), "+ leadRadial: ValBearingType"(+27px), "+ leadDME: ValDistanceType"(+15px), "+ indicatorFACF: CodeYesNoType"(+40px)
- [medium] **node_overlap**: 10 overlapping pairs:  x IntermediateLeg;  x InitialLeg;  x ArrivalFeederLeg
- [high] **missing_waypoints**: 17/18 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 15, Edge count: 18, No content clipping, Edge labels found: 30 (10 edges have label data), 37 links/cross-references detected, All nodes have bgColor

### 2 - NavigationArea (id: `f27cf6ff-1ff3-4f3c-8b80-e50c3a9a30d5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ turnDirection: CodeDirectionTurnType"(+29px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x SectorDesign;  x Obstruction
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 21 (7 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 1 - SID (id: `b74799df-7a15-4eb9-ae82-90d38b184324`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px)
- [medium] **node_overlap**: 7 overlapping pairs:  x StandardInstrumentDeparture;  x DepartureLeg;  x ProcedureTransitionLeg
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 14, No content clipping, Edge labels found: 33 (11 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 1 - STAR (id: `0b1cb01b-0b2d-4067-9a63-b228b5bbeb0e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ safeAreaType: CodeSafeAltitudeType"(+50px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "LandingTakeoffAreaCollection"(+95px)
- [medium] **node_overlap**: 7 overlapping pairs:  x LandingTakeoffAreaCollection;  x ArrivalLeg;  x ProcedureTransitionLeg
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 10, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 1 - Minima (id: `89b4860e-51da-48d8-907d-849f175e4f92`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "EquipmentUnavailableAdjustmentColumn"(+83px), "+ guidanceEquipment: CodeApproachType"(+14px), "+ landingSystemLights: CodeYesNoType"(+8px), "+ visibilityAdjustment: ValDistanceVerti"(+77px), "+ approachLightingInoperative: CodeYesNo"(+58px)
- [medium] **node_overlap**: 5 overlapping pairs:  x EquipmentUnavailableAdjustmentColumn;  x EquipmentUnavailableAdjustment;  x LandingTakeoffAreaCollection
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Circling (id: `cbc67934-2fc4-465f-8a79-e85a98266f0b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 24 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ courseReversalInstruction: TextInstruc"(+3px), "+ additionalEquipment: CodeApproachEquip"(+66px), "LandingTakeoffAreaCollection"(+95px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Minima;  x CircleSector;  x PropertiesWithSchedule
- [high] **missing_waypoints**: 13/16 edges (81%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 16, No content clipping, Edge labels found: 45 (15 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 1 - Final Segment Leg Conditions (id: `3e725ab4-22df-4d4f-a2e6-2da9cc3f3129`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ isRemote: CodeYesNoType"(+23px), "+ isPrimary: CodeYesNoType"(+30px), "LandingTakeoffAreaCollection"(+95px), "+ altitudeCode: CodeMinimumAltitudeType"(+25px), "+ altitudeReference: CodeVerticalReferen"(+69px)
- [medium] **node_overlap**: 5 overlapping pairs:  x AircraftCharacteristic;  x ObstacleAssessmentArea;  x FASDataBlock
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 1 - Terminal Arrival Area (id: `5aa42e15-aea0-4dc8-9e8c-0ebe7ca1a6f5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ altitudeAdjustmentType: CodeAltitudeAd"(+71px), "+ altitudeAdjustment: ValDistanceVertica"(+28px), "+ requiredClearance: ValDistanceType"(+25px), "+ minimumAltitude: ValDistanceVerticalTy"(+63px), "+ surfacePenetration: CodeYesNoType"(+19px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x InstrumentApproachProcedure;  x Surface
- [high] **missing_waypoints**: 9/11 edges (82%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 11, No content clipping, Edge labels found: 30 (9 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 2 - Approach Procedure Tables (id: `433aa33b-4701-461a-86b5-74196c0a65f8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ measurementPoint: CodeProcedureDistanc"(+54px), "+ altitudeReference: CodeVerticalReferen"(+60px), "+ startingMeasurementPoint: CodeProcedur"(+71px), "+ endingMeasurementPoint: CodeProcedureD"(+58px), "+ startingMeasurementPoint: CodeProcedur"(+71px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ApproachAltitudeTable;  x ApproachDistanceTable;  x ApproachTimingTable
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Approach Procedure Overview (id: `e44b05ca-d309-4957-b6bb-33e0e391b852`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ seqNumberARINC: NoSequenceType"(+29px), "+ endConditionDesignator: CodeSegmentTer"(+59px), "+ courseDirection: CodeDirectionReferenc"(+16px), "+ upperLimitAltitude: ValDistanceVertica"(+16px), "+ upperLimitReference: CodeVerticalRefer"(+34px)
- [medium] **node_overlap**: 7 overlapping pairs:  x MissedApproachGroup;  x CirclingArea;  x LandingTakeoffAreaCollection
- [high] **missing_waypoints**: 15/15 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 15, No content clipping, Edge labels found: 42 (14 edges have label data), 36 links/cross-references detected, All nodes have bgColor

### 2 - Unit (id: `b1a42c1f-ad07-464c-b2be-ba4c84ae2c90`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ type: CodeUnitDependencyType"(+39px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "PropertiesWithSchedule"(+47px)
- [medium] **node_overlap**: 6 overlapping pairs:  x PropertiesWithSchedule;  x UnitAvailability;  x ElevatedPoint
- [high] **missing_waypoints**: 10/12 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 12, No content clipping, Edge labels found: 27 (11 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 1 - Organisation/Authority (id: `4976bcde-b092-4bce-833c-0fc2e01d4abc`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "OrganisationAuthorityAssociation"(+69px), "+ type: CodeOrganisationHierarchyType"(+56px)
- [medium] **node_overlap**: 3 overlapping pairs:  x ContactInformation;  x OrganisationAuthorityAssociation;  x OrganisationAuthority
- [medium] **missing_waypoints**: 1/2 edges (50%) have no waypoints

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 3 (2 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### 3 - Obstacle Areas (id: `e403b3dd-4704-4678-9efa-b3e99a7ba33f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ type: CodeVerticalStructureType"(+21px), "+ markingICAOStandard: CodeYesNoType"(+40px), "+ lightingICAOStandard: CodeYesNoType"(+46px), "+ synchronisedLighting: CodeYesNoType"(+46px), "+ horizontalAccuracy: ValDistanceType"(+60px)
- [medium] **node_overlap**: 5 overlapping pairs:  x Surface;  x RunwayDirection;  x AirportHeliport
- [high] **missing_waypoints**: 8/9 edges (89%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 9, No content clipping, Edge labels found: 24 (9 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 2 - Vertical Structure Associations (id: `70795ac1-51b7-4e66-9a11-5d6c6b326170`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ type: CodePassengerServiceType"(+46px), "+ emergencyLighting: CodeYesNoType"(+34px), "+ intensityLevel: CodeLightIntensityType"(+71px), "+ designator: CodeNavaidDesignatorType"(+22px), "+ emissionClass: CodeRadioEmissionType"(+22px)
- [medium] **node_overlap**: 7 overlapping pairs:  x GroundLightSystem;  x NavaidEquipment;  x SpecialNavigationStation
- [high] **missing_waypoints**: 11/13 edges (85%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 13, No content clipping, Edge labels found: 33 (13 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 1 - Vertical Structures (id: `1e6f5b0d-00e7-4cb9-8746-8f5d978119c4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ intensityLevel: CodeLightIntensityType"(+71px), "+ intensity: ValLightIntensityType"(+34px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 8 overlapping pairs:  x ElevatedPoint;  x ElevatedCurve;  x ElevatedSurface
- [high] **missing_waypoints**: 12/13 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 13, No content clipping, Edge labels found: 30 (10 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 1 - Notes (id: `57fd06c1-4c02-4adf-8ce6-61e819c49397`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ identifier: CodeUUIDType"(+46px), "+ note: TextNoteType"(+19px), "+ propertyName: TextPropertyNameType"(+45px), "+ purpose: CodeNotePurposeType"(+8px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AIXMObject;  x AIXMFeature;  x LinguisticNote
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 1 - GroundLight (id: `e80c7dde-6397-484b-8da7-d36b5637eb9d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ type: CodeVerticalStructureType"(+21px)
- [medium] **node_overlap**: 4 overlapping pairs:  x ElevatedPoint;  x VerticalStructure;  x AirportHeliport
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 2 - Designated Point (id: `fed4bc27-bc27-4e8d-b067-373f7b77bcea`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ indicationDirection: CodeDirectionRefe"(+59px), "+ cardinalDirection: CodeCardinalDirecti"(+40px), "+ minimumReceptionAltitude: ValDistanceV"(+71px), "+ priorFixTolerance: ValDistanceSignedTy"(+66px)
- [medium] **node_overlap**: 6 overlapping pairs:  x PointReference;  x DistanceIndication;  x TouchDownLiftOff
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 10, No content clipping, Edge labels found: 30 (10 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 1 - Significant Points (id: `c29ad16a-8a26-4884-9fbe-59f4966c1eff`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ designator: CodeDesignatedPointDesigna"(+66px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px)
- [medium] **node_overlap**: 5 overlapping pairs:  x TouchDownLiftOff;  x AirportHeliport;  x RunwayCentrelinePoint
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 13, No content clipping, Edge labels found: 39 (7 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 2 - Point Reference (id: `768a6db5-ade7-4f84-a1d1-d75d45400900`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ signalPerformance: CodeSignalPerforman"(+61px), "+ courseQuality: CodeCourseQualityILSTyp"(+10px), "+ integrityLevel: CodeIntegrityLevelILST"(+23px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ horizontalAccuracy: ValDistanceType"(+60px)
- [medium] **node_overlap**: 7 overlapping pairs:  x Navaid;  x SignificantPoint;  x DistanceIndication
- [medium] **missing_waypoints**: 12/15 edges (80%) have no waypoints

**Correct:** Node count: 10, Edge count: 15, No content clipping, Edge labels found: 42 (11 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 1 - Segment Points (id: `e76efaa1-85f4-4dd2-8814-9be712de8938`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "TerminalSegmentPoint"(+16px), "+ role: CodeProcedureFixRoleType"(+52px), "+ leadRadial: ValBearingType"(+27px), "+ leadDME: ValDistanceType"(+15px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SignificantPoint;  x Surface;  x TerminalSegmentPoint
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 9 (3 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Navaids (id: `115fec58-4909-46c2-90e9-bc3563effd7e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ approachMarkingCondition: CodeMarkingC"(+50px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NavaidEquipmentMonitoring;  x PropertiesWithSchedule;  x NavaidOperationalStatus
- [high] **missing_waypoints**: 17/18 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 18, No content clipping, Edge labels found: 45 (16 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 1 - Guidance Service (id: `b21f425c-ac6b-4b4d-ad78-db6a20e2f223`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ signalPerformance: CodeSignalPerforman"(+61px), "+ courseQuality: CodeCourseQualityILSTyp"(+10px), "+ integrityLevel: CodeIntegrityLevelILST"(+23px), "+ generalTerrainMonitor: CodeYesNoType"(+54px), "+ broadcastIdentifier: TextDesignatorTyp"(+72px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Navaid;  x RadarSystem;  x SpecialNavigationSystem
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 2 - Unplanned Holding (id: `2a89a164-fd98-4a06-8728-ee9ed50f4a3f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px), "+ assessedAltitude: ValDistanceVerticalT"(+39px), "+ slopeLowerAltitude: ValDistanceVertica"(+52px), "+ surfaceZone: CodeObstructionIdSurfaceZ"(+64px), "+ turnDirection: CodeDirectionTurnType"(+6px)
- [medium] **node_overlap**: 6 overlapping pairs:  x ObstacleAssessmentArea;  x HoldingPattern;  x PointReference
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Holding Pattern (id: `681c24dc-f37f-4034-8558-3725f2a7f503`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "HoldingPatternDuration"(+52px), "+ duration: ValDurationType"(+48px), "HoldingPatternDistance"(+60px), "+ length: ValDistanceType"(+44px), "HoldingPatternLength"(+33px)
- [medium] **node_overlap**: 5 overlapping pairs:  x HoldingPatternDistance;  x HoldingPatternLength;  x SegmentPoint
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 18 (6 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### 1 - Geometry (id: `dbdb4f51-ec62-49dd-be48-bb6c69d03c01`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ elevation: ValDistanceVerticalType"(+30px)
- [medium] **node_overlap**: 9 overlapping pairs:  x GM_Point;  x GM_Surface;  x GM_Curve
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 6, No content clipping, 30 links/cross-references detected, All nodes have bgColor

### 4 - Airspace Activation (id: `775e9609-89b3-4b92-87e9-17fe0b3f7820`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ unitOfMeasurement: CodeDistanceVertica"(+83px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AircraftCharacteristic;  x StandardLevelColumn;  x AirspaceLayer
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 18 (7 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 3 - Airspace Classification (id: `2a8d0255-0501-45a3-b7c9-f5cc217c5cd5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "PropertiesWithSchedule"(+47px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ classification: CodeAirspaceClassifica"(+87px)
- [medium] **node_overlap**: 4 overlapping pairs:  x PropertiesWithSchedule;  x AirspaceLayer;  x AirspaceLayerClass
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 2 - Airspace Associations (id: `0e2afc84-82de-44e2-ab43-a7f97015154c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 13 text elements overflow: "+ category: CodeRuleProcedureType"(+45px), "+ title: CodeRuleProcedureTitleType"(+58px), "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px), "AuthorityForAirspace"(+41px)
- [medium] **node_overlap**: 6 overlapping pairs:  x OrganisationAuthority;  x AuthorityForAirspace;  x SignificantPoint
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 21 (8 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Airspace Feature (id: `efc00ca3-ef34-4f35-b5a7-7239af962d94`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ name: TextNameType"(+3px), "+ type: CodeGeoBorderType"(+34px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ dependency: CodeAirspaceDependencyType"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Curve;  x GeoBorder;  x SignificantPoint
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 15 (5 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 3 - Taxi Holding Position (id: `4360acf2-672b-4287-aebb-df3cc578eecb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "TaxiHoldingPositionLightSystem"(+63px), "+ type: CodeLightHoldingPositionType"(+55px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ElevatedPoint;  x Runway;  x GuidanceLine
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 2 - Guidance Line (id: `e5dc0ff8-3871-4dbe-b5cd-b84a280eb735`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "GuidanceLineLightSystem"(+82px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RunwayCentrelinePoint;  x Taxiway;  x TouchDownLiftOff
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 1 - Taxiway (id: `a1d731da-4a79-40b1-a73f-456e5f6be2a9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ position: CodeTaxiwaySectionType"(+50px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 5 overlapping pairs:  x SurfaceCharacteristics;  x TaxiwayElement;  x TaxiwayMarking
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 12, No content clipping, Edge labels found: 36 (12 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 1 - Surface Contamination (id: `05cedd87-4736-4849-b112-94eba4dcae79`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 50 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "AircraftStandContamination"(+95px), "+ abandoned: CodeYesNoType"(+28px), "ApronContamination"(+43px), "+ designator: CodeAirportHeliportDesigna"(+4px)
- [medium] **node_overlap**: 12 overlapping pairs:  x AircraftStand;  x AircraftStandContamination;  x Apron
- [high] **missing_waypoints**: 25/25 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 17, Edge count: 25, No content clipping, Edge labels found: 54 (18 edges have label data), 39 links/cross-references detected, All nodes have bgColor

### 1 - Seaplanes (id: `01975d03-f2fc-45ff-a97a-ce5b78f97a79`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: CodeBuoyDesignatorType"(+51px)
- [medium] **node_overlap**: 7 overlapping pairs:  x ElevatedPoint;  x MarkingBuoy;  x FloatingDockSite
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 6 - Runway Blast Pad (id: `a7b47ca0-e862-4cd3-8776-790729b72826`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ approachMarkingCondition: CodeMarkingC"(+50px)
- [medium] **node_overlap**: 4 overlapping pairs:  x ElevatedSurface;  x RunwayDirection;  x SurfaceCharacteristics
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 5 - Runway Visual Range (id: `a4b95142-1ba4-4bfc-aaf1-5cdcde30ea20`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ approachMarkingCondition: CodeMarkingC"(+50px), "+ precisionApproachGuidance: CodeApproac"(+57px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RunwayDirection;  x ElevatedPoint;  x RunwayVisualRange
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 4 - Runway Protection (id: `1b7aaa28-168d-44d7-87af-df63679ff217`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ markingLocation: CodeProtectAreaSectio"(+62px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 5 overlapping pairs:  x RunwayDirection;  x TouchDownLiftOffSafeArea;  x RunwayProtectArea
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 12 (4 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 3 - Runway Operational Point (id: `aae6ddd9-3991-4e02-8994-548b5f0d755a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "NavaidEquipmentDistance"(+27px), "+ distance: ValDistanceType"(+6px), "+ distanceAccuracy: ValDistanceType"(+56px), "+ designator: CodeNavaidDesignatorType"(+22px), "+ emissionClass: CodeRadioEmissionType"(+22px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Apron;  x Taxiway;  x GuidanceLine
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 12, No content clipping, Edge labels found: 33 (11 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 2 - Runway Direction (id: `07ece560-5096-46f0-a661-2c7be7506ed2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 43 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ elevation: ValDistanceVerticalType"(+30px)
- [medium] **node_overlap**: 9 overlapping pairs:  x ElevatedCurve;  x ArrestingGearExtent;  x ArrestingGear
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 14, No content clipping, Edge labels found: 36 (12 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 1 - Runway (id: `a8335687-e25a-4f37-abec-22355b8c0c16`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ markingLocation: CodeRunwaySectionType"(+48px)
- [medium] **node_overlap**: 5 overlapping pairs:  x SurfaceCharacteristics;  x RunwayElement;  x RunwayDirection
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 13, No content clipping, Edge labels found: 39 (13 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 1 - Surface Marking (id: `1cd09b15-6998-442c-800b-b43c8a2afea6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 51 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "AirportHeliportProtectionArea"(+48px), "+ width: ValDistanceType"(+9px), "+ length: ValDistanceType"(+15px)
- [medium] **node_overlap**: 13 overlapping pairs:  x AirportHeliportProtectionArea;  x TaxiHoldingPosition;  x GuidanceLine
- [high] **missing_waypoints**: 40/41 edges (98%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 24, Edge count: 41, No content clipping, Edge labels found: 96 (32 edges have label data), 46 links/cross-references detected, All nodes have bgColor

### 3 - Pilot Controlled Lighting (id: `7ebe1efb-588e-4815-b40f-48b09a5d7065`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ intensityLevel: CodeLightIntensityType"(+72px), "+ activation: CodeSystemActivationType"(+60px), "+ classICAO: CodeApproachLightingICAOTyp"(+49px), "+ sequencedFlashing: CodeYesNoType"(+6px), "+ alignmentIndicator: CodeYesNoType"(+12px)
- [medium] **node_overlap**: 4 overlapping pairs:  x LightActivation;  x ApproachLightingSystem;  x GroundLightSystem
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### 2 - Surface Lighting Elements (id: `bd4d2d69-59b6-45db-98a7-17f4be71963e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ type: CodeGuidanceLineType"(+12px), "+ usageDirection: CodeDirectionType"(+56px), "GuidanceLineLightSystem"(+82px), "+ type: CodeRunwayProtectionAreaType"(+47px), "+ status: CodeStatusOperationsType"(+35px)
- [medium] **node_overlap**: 10 overlapping pairs:  x RunwayDirection;  x TouchDownLiftOff;  x Taxiway
- [high] **missing_waypoints**: 20/21 edges (95%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 16, Edge count: 21, No content clipping, Edge labels found: 39 (13 edges have label data), 38 links/cross-references detected, All nodes have bgColor

### 1 - Surface Lighting (id: `047a3a0e-2e3b-479e-8877-25a0db33f9c5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "PropertiesWithSchedule"(+47px), "+ operationalStatus: CodeStatusOperation"(+68px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x PropertiesWithSchedule;  x GroundLightingAvailability;  x ElevatedPoint
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 9 (3 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### 2 - TLOF Protection Area (id: `d07ca7bb-9393-4689-85c5-f7ae5a38374a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ composition: CodeSurfaceCompositionTyp"(+23px), "+ preparation: CodeSurfacePreparationTyp"(+23px), "+ surfaceCondition: CodeSurfaceCondition"(+42px), "+ pavementTypePCN: CodePCNPavementType"(+5px), "+ pavementSubgradePCN: CodePCNSubgradeTy"(+30px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SurfaceCharacteristics;  x TouchDownLiftOff;  x RunwayProtectArea
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 18 (6 edges have label data), 29 links/cross-references detected, All nodes have bgColor

### 1 - TLOF (id: `cb177c45-588f-4a74-88fd-9cc470f0f27c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 36 text elements overflow: "TouchDownLiftOffLightSystem"(+67px), "+ position: CodeTLOFSectionType"(+43px), "+ markingLocation: CodeTLOFSectionType"(+46px), "ManoeuvringAreaAvailability"(+15px), "+ operationalStatus: CodeStatusAirportTy"(+69px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SurfaceCharacteristics;  x ElevatedSurface;  x ElevatedPoint
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 13, No content clipping, Edge labels found: 39 (13 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 4 - Passenger Loading Bridge (id: `c4b4dfcf-56a6-472d-a7a2-95c9af91ae3b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ visualDockingSystem: CodeVisualDocking"(+64px)
- [medium] **node_overlap**: 3 overlapping pairs:  x ElevatedSurface;  x AircraftStand;  x PassengerLoadingBridge
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 3 - Roads (id: `ad8ad8d9-6bd9-43c1-aad0-4580854080f8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ composition: CodeSurfaceCompositionTyp"(+23px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AircraftStand;  x AirportHeliport;  x Road
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### 2 - Aircraft Stands (id: `fda0f6f4-7899-4dc1-9ff7-a8dabbee1623`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ composition: CodeSurfaceCompositionTyp"(+23px), "+ preparation: CodeSurfacePreparationTyp"(+23px), "+ surfaceCondition: CodeSurfaceCondition"(+42px), "+ pavementTypePCN: CodePCNPavementType"(+5px), "+ pavementSubgradePCN: CodePCNSubgradeTy"(+30px)
- [medium] **node_overlap**: 5 overlapping pairs:  x StandMarking;  x SurfaceCharacteristics;  x ApronElement
- [medium] **missing_waypoints**: 4/7 edges (57%) have no waypoints

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 28 links/cross-references detected, All nodes have bgColor

### 1 - Apron (id: `860e067a-f691-4fac-a490-e67e405ce1ac`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ markingLocation: CodeApronSectionType"(+51px), "+ position: CodeApronSectionType"(+48px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ElevatedSurface;  x AirportSuppliesService;  x ApronElement
- [high] **missing_waypoints**: 10/12 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 12, No content clipping, Edge labels found: 36 (12 edges have label data), 31 links/cross-references detected, All nodes have bgColor

### 5 - Apron Area Availability (id: `8cb8753c-1f97-4a86-a5a8-b99c995a4b71`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "PropertiesWithSchedule"(+47px), "+ type: CodeUsageLimitationType"(+40px), "+ priorPermission: ValDurationType"(+59px), "ApronAreaUsage"(+15px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AircraftStand;  x UsageCondition;  x ApronAreaUsage
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 11, No content clipping, Edge labels found: 27 (9 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### 4 - Manoeuvering Area Availability (id: `a4f1c551-e8ed-42a1-9169-e56d3a0cb517`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ helicopterClass: CodeHelicopterPerform"(+70px), "PropertiesWithSchedule"(+47px), "+ type: CodeUsageLimitationType"(+40px), "+ priorPermission: ValDurationType"(+59px), "+ operation: CodeOperationManoeuvringAre"(+55px)
- [medium] **node_overlap**: 7 overlapping pairs:  x TouchDownLiftOff;  x TaxiwayElement;  x SeaplaneLandingArea
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 27 (9 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 3 - AirportHeliport Availability (id: `4436e3de-2d06-4c36-85ad-11c9a565aab0`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ status: CodeFlightStatusType"(+25px), "+ military: CodeMilitaryStatusType"(+50px), "+ origin: CodeFlightOriginType"(+25px), "+ purpose: CodeFlightPurposeType"(+37px), "+ navigationSpecification: CodeNavigatio"(+18px)
- [medium] **node_overlap**: 6 overlapping pairs:  x Meteorology;  x ContactInformation;  x AirportHeliportUsage
- [high] **missing_waypoints**: 11/12 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 12, No content clipping, Edge labels found: 24 (9 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### 2 - AirportHeliport Association (id: `da3c4e95-0fac-4b03-b1fc-def383bef41d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 39 text elements overflow: "+ abandoned: CodeYesNoType"(+28px), "+ designator: TextDesignatorType"(+27px), "+ nominalLength: ValDistanceType"(+27px), "+ lengthAccuracy: ValDistanceType"(+33px), "+ nominalWidth: ValDistanceType"(+21px)
- [medium] **node_overlap**: 11 overlapping pairs:  x Taxiway;  x RulesProcedures;  x WorkArea
- [high] **missing_waypoints**: 18/21 edges (86%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 15, Edge count: 21, No content clipping, Edge labels found: 60 (20 edges have label data), 37 links/cross-references detected, All nodes have bgColor

### 1 - AirportHeliport (id: `c9860143-cbf4-4c76-ad6d-64ec4369e0cf`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 27 text elements overflow: "+ designator: TextDesignatorType"(+54px), "+ instruction: TextInstructionType"(+67px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 9 overlapping pairs:  x OrganisationAuthority;  x AirportHeliportResponsibilityOrganisation;  x PropertiesWithSchedule
- [high] **missing_waypoints**: 15/16 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 16, No content clipping, Edge labels found: 39 (14 edges have label data), 34 links/cross-references detected, All nodes have bgColor

### 2 - Aerial Refuelling Availability (id: `994ea915-4cd9-4df2-b61e-3c7eea57cfc2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "PropertiesWithSchedule"(+47px), "+ cardinalDirection: CodeCardinalDirecti"(+75px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AirspaceLayer;  x PropertiesWithSchedule;  x RouteAvailability
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 6 (3 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### 1 - Aerial Refuelling (id: `2a78bedd-4e4a-4a48-a5bb-af378ed21c9c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 23 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ reportingATC: CodeATCReportingType"(+44px), "+ radarGuidance: CodeYesNoType"(+7px)
- [medium] **node_overlap**: 9 overlapping pairs:  x AirspaceLayer;  x AerialRefuellingPoint;  x Surface
- [medium] **missing_waypoints**: 10/13 edges (77%) have no waypoints

**Correct:** Node count: 11, Edge count: 13, No content clipping, Edge labels found: 30 (12 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### Basic Types (id: `ae374f6c-7982-4d03-9b71-964f75236a74`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ nilReason: NilReasonEnumeration"(+48px), "Character2Type"(+7px), "AlphanumericType"(+17px), "anySimpleType"(+3px)
- [medium] **node_overlap**: 11 overlapping pairs:  x XHTMLType;  x unsignedInt;  x decimal
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 5, No content clipping, 31 links/cross-references detected, All nodes have bgColor

### Main (id: `aa02cec1-8bdc-4aaf-8440-c0645bef3987`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ sequenceNumber: NoSequenceType"(+31px), "AIXMFeaturePropertyGroup"(+33px), "+ featureLifetime: TimePrimitive"(+59px), "+ interpretation: TimeSliceInterpretatio"(+81px), "+ identifier: CodeUUIDType"(+46px)
- [medium] **node_overlap**: 8 overlapping pairs:  x ;  x AIXMMessage;  x MD_Metadata
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, 28 links/cross-references detected, All nodes have bgColor

### AIXM_v.5.1.1 (id: `34c7d86b-4e36-4872-ac60-e4b513a094da`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "XMLSchemaDatatypes"(+55px), "AIXM Data Types"(+15px), "ISO 19107  Geometry"(+43px), "ISO 19115 Metadata"(+41px), "AIXM Abstract Feature"(+57px)
- [medium] **node_overlap**: 11 overlapping pairs:  x ;  x ;  x XMLSchemaDatatypes
- [medium] **missing_packages**: API has 7 package nodes, DOM has 0
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 6, No content clipping, 28 links/cross-references detected, All nodes have bgColor


---

## FIXM

### NasRoute (id: `bcf7b1a7-3fe8-451d-983b-3aa909f2401c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 34 text elements overflow: "UnknownRouteElement"(+62px), "StarsFlightRules"(+13px), "+ estimatedElapsedTime: Duration"(+12px), "+ predictedWaypoint: SignificantPoint"(+43px), "+ estimatedElapsedEntryTime: Duration"(+32px)
- [medium] **node_overlap**: 15 overlapping pairs:  x UnknownRouteElement;  x StarsFlightRules;  x InhibitAdaptedDepRoutesIndicator
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 19, Edge count: 18, No content clipping, Edge labels found: 17 (17 edges have label data), 38 links/cross-references detected, All nodes have bgColor

### NasFlightData (id: `6fd53527-900e-4eec-9ab0-c3cde1acbfd9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "DiversionRecoveryIndicator"(+88px), "+ DIVERSION_RECOVERY:"(+19px), "NasFlightStatus"(+10px), "+ stddsSpotOut: Time"(+3px), "+ stddsWheelsOff: Time"(+16px)
- [medium] **node_overlap**: 18 overlapping pairs:  x DiversionRecoveryIndicator;  x RnavIndicator;  x NasFlightStatus
- [high] **missing_waypoints**: 26/26 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 25, Edge count: 26, No content clipping, Edge labels found: 26 (26 edges have label data), 44 links/cross-references detected, All nodes have bgColor

### NasAltitude (id: `99ba4e39-72ae-41eb-a545-1c97713c0e52`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "InvalidIndicator"(+8px), "ReportedAltitude"(+19px), "+ above: FlightLevelOrAltitude"(+32px), "+ below: FlightLevelOrAltitude"(+32px), "+ point: SignificantPoint"(+10px)
- [medium] **node_overlap**: 15 overlapping pairs:  x InvalidIndicator;  x TargetAltitude;  x AltitudeSuffix
- [high] **missing_waypoints**: 10/10 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 14, Edge count: 10, No content clipping, Edge labels found: 10 (10 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### NasAircraft (id: `51cf8dcc-d851-47f0-b970-19ce715d894e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "TfmsAircraftCategory"(+38px), "+ SINGLE_PISTON_PROP:"(+13px), "+ MULTI_PISTON_PROP:"(+7px), "+ SINGLE_TURBO_PROP:"(+7px), "+ MILITARY_FIGHTER_JET:"(+26px)
- [medium] **node_overlap**: 13 overlapping pairs:  x RnavIndicator;  x EngineType;  x TfmsAircraftCategory
- [high] **missing_waypoints**: 10/10 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 10, No content clipping, Edge labels found: 10 (10 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### NasTrajectoryOptions (id: `5b2b09da-ed53-42bd-90fb-a514e059d9cd`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 39 text elements overflow: "AssignedIndicator"(+25px), "+ ASSIGNED: string"(+7px), "+ amendmentRejectReason: CharacterString"(+29px), "RouteAmendmentStatus"(+71px), "CollaborativeTrajectoryOptionsProgram"(+107px)
- [medium] **node_overlap**: 23 overlapping pairs:  x AssignedIndicator;  x CtopRouteAmendment;  x CollaborativeTrajectoryOptionsProgram
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 24, Edge count: 18, No content clipping, Edge labels found: 18 (18 edges have label data), 44 links/cross-references detected, All nodes have bgColor

### NasTmiData (id: `c68ec35a-1a20-4397-9cc8-888c2c1c9186`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "AmendmentType"(+15px), "AmendmentStatus"(+28px), "CollaborativeTrajectoryOptionsProgram"(+107px), "+ additionalAirborneTime: Duration"(+34px), "+ assignedGroundDelay: Duration"(+15px)
- [medium] **node_overlap**: 18 overlapping pairs:  x AmendmentType;  x AmendmentStatus;  x CollaborativeTrajectoryOptionsProgram
- [high] **missing_waypoints**: 19/19 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 21, Edge count: 19, No content clipping, Edge labels found: 19 (19 edges have label data), 41 links/cross-references detected, All nodes have bgColor

### NasTmiCompliance (id: `19560584-a45f-4b92-862a-3a6f637b3331`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "SpuriousFlightIndicator"(+64px), "+ SPURIOUS_FLIGHT:"(+7px), "CanceledButFlewIndicator"(+49px), "TmiComplianceIndicator"(+69px), "TmiCompliance"(+4px)
- [medium] **node_overlap**: 4 overlapping pairs:  x SpuriousFlightIndicator;  x CanceledButFlewIndicator;  x TmiComplianceIndicator
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### NasTfdm (id: `469c5993-fa76-40b9-a1e3-a236f718fe5b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ InboundMovementAreaHoldTimeDuration: D"(+30px), "+ inboundMovementAreaTaxiTimeDuration: D"(+30px), "+ outboundMovementAreaHoldTimeDuration: "(+11px), "+ outboundMovementAreaQueuingTimeDuratio"(+30px), "+ outboundMovementAreaTaxiTimeDuration: "(+11px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ArrivalTaxiOperationsMetrics;  x DepartureTaxiOperationsMetrics;  x TfdmArrival
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 2, No content clipping, Edge labels found: 2 (2 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### NasStatus (id: `ea2f5a8b-acbf-415a-8709-71cfd67f4910`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ CLEARED_FOR_TAKEOFF:"(+16px), "AircraftMovementStateValue"(+68px), "StarsFlightStatus"(+21px), "AirborneHoldIndicator"(+29px), "+ AIRBORNE_HOLD: string"(+12px)
- [medium] **node_overlap**: 11 overlapping pairs:  x TfdmAtcFlightState;  x TfdmFlightState;  x AtcStateValue
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### NasPosition (id: `0a00227e-bbfc-43bf-989d-91a9b8fe4370`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "NasAcceleration"(+11px), "+ positionAltitude: FlightLevelOrAltitud"(+55px), "+ reportedLevel: ReportedAltitude"(+16px), "+ targetAltitude: TargetAltitude"(+10px), "+ targetPosition: GeographicalPosition"(+48px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NasAcceleration;  x PlannedReportingPosition;  x NasAircraftPosition
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### NasMessage (id: `4e2801fb-a44b-4444-a695-1318703e57dd`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ additionalFlightInformation: NameValue"(+48px), "+ finalControllingUnit: AtcUnitReference"(+23px), "+ navigationIntegrityCategory: Count"(+26px), "+ positionNavigationAccuracyCategory: Co"(+70px), "+ triggerType: CharacterString"(+35px)
- [medium] **node_overlap**: 7 overlapping pairs:  x NasFlight;  x AsdexConfidence;  x MessageProvenance
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### NasMeasures (id: `01d5fc23-a431-43b2-92d8-830f96f8e016`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "NasIndicatedAirspeed"(+52px), "+ uom: UomAirspeed"(+7px), "VeriticalRateSource"(+37px), "NasVerticalRate"(+10px), "UomAcceleration"(+17px)
- [medium] **node_overlap**: 5 overlapping pairs:  x NasIndicatedAirspeed;  x VeriticalRateSource;  x NasVerticalRate
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### NasFlightPlan (id: `d58b288d-0994-4f3b-9f83-1f03db284441`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "StarsFlightPlanSuspendedIndicator"(+107px), "StarsFlightPlanDeletedIndicator"(+108px), "StarsFlightPlanStatus"(+52px), "+ flightPlanRemarks: CharacterString"(+41px)
- [medium] **node_overlap**: 5 overlapping pairs:  x StarsFlightPlanSuspendedIndicator;  x StarsFlightPlanDeletedIndicator;  x StarsFlightPlanStatus
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 3, No content clipping, Edge labels found: 3 (3 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### NasFlightIntent (id: `a3676c43-00ed-41ae-9c7d-8006e8206674`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "MovementAreaHoldInformation"(+67px), "+ estimatedEntryTime: Time"(+3px)
- [medium] **node_overlap**: 3 overlapping pairs:  x COPYRIGHT;  x HoldIntent;  x MovementAreaHoldInformation
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected, All nodes have bgColor

### NasEnRouteData (id: `24f000fe-8ac6-4283-ba44-e7966b30becc`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "NasBoundaryCrossing"(+53px), "+ reportedLevel: ReportedAltitude"(+13px), "+ targetAltitude: TargetAltitude"(+7px), "+ targetPosition: GeographicalPosition"(+45px), "+ arrivalAerodrome: AerodromeReference"(+31px)
- [medium] **node_overlap**: 15 overlapping pairs:  x NasBoundaryCrossing;  x NasAircraftPosition;  x ControlElement
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 14, Edge count: 12, No content clipping, Edge labels found: 12 (12 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### NasDeparture (id: `f288b820-2566-4742-a310-795e8cabd51e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 24 text elements overflow: "DepartureDelayReason"(+61px), "+ facilityToCharge: CharacterString"(+42px), "+ tmiIdentifier: CharacterString"(+23px), "TmatMarkedForSubsitutionIndicator"(+61px), "TmatRelinquishIndicator"(+71px)
- [medium] **node_overlap**: 17 overlapping pairs:  x DepartureDelayReason;  x DepartureDelay;  x TmatMarkedForSubsitutionIndicator
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 19, Edge count: 18, No content clipping, Edge labels found: 18 (18 edges have label data), 38 links/cross-references detected, All nodes have bgColor

### NasCoordination (id: `086004bf-d998-4203-97b1-507828d9ecdc`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "NasBoundaryCrossing"(+53px), "+ acceptingUnit: AtcUnitReference"(+24px), "+ receivingUnit: AtcUnitReference"(+24px), "+ transferringUnit: AtcUnitReference"(+43px), "NasHandoffEvent"(+19px)
- [medium] **node_overlap**: 4 overlapping pairs:  x NasBoundaryCrossing;  x COPYRIGHT;  x NasHandoff
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 2, No content clipping, Edge labels found: 2 (2 edges have label data), 23 links/cross-references detected, All nodes have bgColor

### NasCommon (id: `41f6678b-17e4-4733-aa1f-0757a7e90042`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "NasStandInformation"(+26px), "+ standName: TextName"(+3px), "RunwayClassificationType"(+80px), "+ reportedTimestamp: Time"(+13px), "RunwayUnassignedIndicator"(+91px)
- [medium] **node_overlap**: 13 overlapping pairs:  x NasStandInformation;  x RunwayClassificationType;  x NasRunwayInformation
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 6, No content clipping, Edge labels found: 3 (3 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### NasArrival (id: `121d25e7-e221-4aed-b739-a5fd61c4e2df`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "MovementAreaHoldInformation"(+81px), "+ estimatedEntryTime: Time"(+17px), "+ estimatedExitTime: Time"(+10px), "RunwayUnassignedIndicator"(+91px), "+ RUNWAY_UNASSIGNED:"(+11px)
- [medium] **node_overlap**: 16 overlapping pairs:  x HoldIntent;  x MovementAreaHoldInformation;  x RunwayUnassignedIndicator
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 16, Edge count: 14, No content clipping, Edge labels found: 14 (14 edges have label data), 35 links/cross-references detected, All nodes have bgColor

### NasAirspace (id: `cd9c78e9-61d0-4a8e-b46c-0c8782046ab9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 3 text elements overflow: "TfmsRouteType"(+5px), "+ CODED_ROUTE: string"(+25px), "TfmsInstrumentRouteDesignator"(+97px)
- [medium] **node_overlap**: 3 overlapping pairs:  x COPYRIGHT;  x TfmsRouteType;  x TfmsInstrumentRouteDesignator
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected, All nodes have bgColor

### Capability (id: `f4529e32-07de-478d-af72-97cf48000986`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ colour: ColourChoice"(+12px), "+ totalCapacity: Count"(+12px), "DinghyCoverIndicator"(+51px), "SurvivalEquipmentType"(+54px), "+ otherSurveillanceCapabilities: Charact"(+66px)
- [medium] **node_overlap**: 15 overlapping pairs:  x Dinghies;  x DinghyCoverIndicator;  x SurvivalEquipmentType
- [high] **missing_waypoints**: 16/16 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 18, Edge count: 16, No content clipping, Edge labels found: 16 (16 edges have label data), 37 links/cross-references detected, All nodes have bgColor

### DangerousGoods (id: `592672cf-b1bb-447e-a114-eaa67c2d98aa`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "AdditionalHandlingInformation"(+10px), "+ responsibleAgent: PersonOrOrganization"(+36px), "+ airWaybillNumber: CharacterString"(+36px), "+ dangerousGoodsScreeningLocation: Chara"(+49px), "+ subsidiaryHazardClassAndDivision: Char"(+55px)
- [medium] **node_overlap**: 10 overlapping pairs:  x AdditionalHandlingInformation;  x AirWaybill;  x ShippingInformation
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### Messaging (id: `ba27babd-c821-49d2-9d9c-56cc6a3ab949`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "SubmissionStatusValue"(+64px), "FlightPlanVersionTypeChoice"(+92px), "+ statusReason: CharacterString"(+19px), "+ statusReason: CharacterString"(+31px), "+ recipientDeliveryResponsibility: Perso"(+8px)
- [medium] **node_overlap**: 14 overlapping pairs:  x MessageCollection;  x FlightPlanVersionTypeChoice;  x FlightPlanNegotiationStatus
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 17, Edge count: 18, No content clipping, Edge labels found: 16 (16 edges have label data), 36 links/cross-references detected, All nodes have bgColor

### Time (id: `517adcb2-d508-4b1b-a365-371b399e4f6f`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 19 links/cross-references detected

### RouteChanges (id: `f822e6d0-cd84-4789-8758-d23c10f8d168`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 3 text elements overflow: "AbstractRouteChange"(+24px), "+ PLAN_TO_COMMENCE:"(+11px), "AtOrAboveAltitudeIndicator"(+42px)
- [medium] **node_overlap**: 7 overlapping pairs:  x COPYRIGHT;  x SpeedChange;  x CruiseClimbStart
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 3 (3 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### Constraints (id: `ac4d7577-0e22-4962-b189-34a3705fee0b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ speed: TrueAirspeedChoice"(+8px), "+ constraintReference: CharacterString"(+46px), "+ temporalSpecification: TemporalChoice"(+35px), "+ PLAN_TO_COMMENCE:"(+11px), "SpeedCondition"(+8px)
- [medium] **node_overlap**: 10 overlapping pairs:  x LevelCondition;  x LevelConstraint;  x SpeedConstraint
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 9, No content clipping, Edge labels found: 6 (6 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### Measures (id: `9d38699c-c11f-48c8-8346-4fe46e7bcd00`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ uom: UomAirspeed"(+7px), "+ uom: UomFlightLevel"(+25px), "VerticalReference"(+22px), "VerticalDistance"(+4px), "+ uom: UomWindSpeed"(+13px)
- [medium] **node_overlap**: 19 overlapping pairs:  x TrueAirspeed;  x FlightLevel;  x Volume
- [high] **missing_waypoints**: 23/23 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 26, Edge count: 23, No content clipping, Edge labels found: 2 (2 edges have label data), 45 links/cross-references detected, All nodes have bgColor

### Extension (id: `36f668e4-9860-4a97-bdf6-261cfa191a60`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 2 overlapping pairs:  x COPYRIGHT;  x Extension

**Correct:** Node count: 2, Edge count: 0, No content clipping, 21 links/cross-references detected, All nodes have bgColor

### Airspace (id: `30231117-30bc-431c-8459-256c2ccd4200`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ position: GeographicalPosition"(+37px), "AirspaceDesignator"(+36px), "RouteDesignator"(+16px), "SidStarDesignator"(+26px), "SignificantPointDesignator"(+88px)
- [medium] **node_overlap**: 14 overlapping pairs:  x PositionPoint;  x AirspaceDesignator;  x GeographicalPosition
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 3, No content clipping, 30 links/cross-references detected, All nodes have bgColor

### Packaging (id: `d6b4d0fd-c8a1-48f8-bc24-2209e628d736`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "AircraftDangerousGoodsLimitation"(+67px), "+ PASSENGER_AND_CARGO_AIRCRAFT: string"(+54px), "MarinePollutantIndicator"(+53px), "+ MARINE_POLLUTANT: string"(+35px), "DangerousGoodsDimensions"(+66px)
- [medium] **node_overlap**: 10 overlapping pairs:  x AircraftDangerousGoodsLimitation;  x MarinePollutantIndicator;  x AllPackedInOne
- [high] **missing_waypoints**: 15/15 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 15, Edge count: 15, No content clipping, Edge labels found: 15 (15 edges have label data), 35 links/cross-references detected, All nodes have bgColor

### UnitsOfMeasure (id: `0c8562e8-312a-4a20-b5c1-c4948de9834c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 16 overlapping pairs:  x UomVolume;  x UomWeight;  x UomTemperature

**Correct:** Node count: 16, Edge count: 0, No content clipping, 36 links/cross-references detected, All nodes have bgColor

### Organization (id: `dfb2fb82-43fd-4250-84be-61ebf2ab30d9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "LocationIndicator"(+20px), "AircraftOperatorDesignator"(+93px), "+ designatorIcao: AircraftOperatorDesign"(+39px), "+ operatingOrganization: PersonOrOrganiz"(+46px), "+ locationIndicator: LocationIndicator"(+21px)
- [medium] **node_overlap**: 12 overlapping pairs:  x LocationIndicator;  x AircraftOperatorDesignator;  x COPYRIGHT
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 4, No content clipping, Edge labels found: 2 (2 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### Aerodrome (id: `ee72f9ad-1afd-4f13-90d1-480f8a115ded`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ locationIndicator: LocationIndicator"(+11px), "IataAerodromeDesignator"(+81px), "RunwayDirectionDesignator"(+85px), "AerodromeName"(+15px), "+ iataDesignator: IataAerodromeDesignato"(+30px)
- [medium] **node_overlap**: 8 overlapping pairs:  x IcaoAerodromeReference;  x AerodromeReference;  x IataAerodromeDesignator
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 2, No content clipping, 26 links/cross-references detected, All nodes have bgColor

### FlightData (id: `155943d3-5bf3-4eda-a754-e4cc0230d9e4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ guidebookNumber: CharacterString"(+47px), "+ onboardLocation: CharacterString"(+47px), "+ pilotInCommand: PersonOrOrganization"(+7px), "+ flightPlanOriginator: PersonOrOrganiza"(+48px), "+ flightPlanSubmitter: PersonOrOrganizat"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DangerousGoods;  x Departure;  x COPYRIGHT
- [high] **missing_waypoints**: 19/19 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 16, Edge count: 19, No content clipping, Edge labels found: 19 (19 edges have label data), 35 links/cross-references detected, All nodes have bgColor

### RouteTrajectory (id: `406df547-3b35-4279-973b-67cf3288f9b0`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 31 text elements overflow: "+ level: FlightLevelOrAltitude"(+25px), "+ relativeTimeFromInitialPredictionPoint"(+33px), "+ AU_REQUEST_AERODROME:"(+8px), "AbstractRouteChange"(+34px), "TrajectoryPointReference"(+42px)
- [medium] **node_overlap**: 15 overlapping pairs:  x EnRouteDelayType;  x AbstractRouteChange;  x COPYRIGHT
- [high] **missing_waypoints**: 24/24 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 24, Edge count: 24, No content clipping, Edge labels found: 24 (24 edges have label data), 44 links/cross-references detected, All nodes have bgColor

### Departure (id: `db4b7273-5f01-425c-9764-1644649dbbfa`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "+ runwayDirection: RunwayDirectionDesign"(+12px), "+ takeoffAlternateAerodrome: AerodromeRe"(+31px)
- [medium] **node_overlap**: 2 overlapping pairs:  x COPYRIGHT;  x Departure

**Correct:** Node count: 2, Edge count: 0, No content clipping, 21 links/cross-references detected, All nodes have bgColor

### Emergency (id: `aad653ec-83d8-400d-8df1-105c46aada85`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 9 text elements overflow: "+ radioFailureRemarks: CharacterString"(+21px), "+ remainingComCapability: CharacterStrin"(+39px), "EmergencyPhase"(+17px), "+ DETRESFA: string"(+7px), "+ lastContactFrequency: Frequency"(+22px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RadioCommunicationFailure;  x EmergencyPhase;  x LastContact
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 4, No content clipping, Edge labels found: 4 (4 edges have label data), 25 links/cross-references detected, All nodes have bgColor

### Types (id: `51dba42f-8c3f-4769-9c5d-8704311cfe8e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "AircraftIdentification"(+45px), "CharacterString"(+9px), "AircraftTypeDesignator"(+62px), "GloballyUniqueFlightIdentifier"(+35px)
- [medium] **node_overlap**: 15 overlapping pairs:  x TextName;  x Time;  x Duration
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 7, No content clipping, Edge labels found: 1 (1 edges have label data), 32 links/cross-references detected, All nodes have bgColor

### Address (id: `c7c99709-1e08-482c-b5bb-c2ebb007d679`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "TextCountryName"(+23px), "TelephoneContact"(+9px), "TelecomNetworkType"(+47px), "TextCountryCode"(+17px)
- [medium] **node_overlap**: 11 overlapping pairs:  x TextCountryName;  x TelephoneContact;  x OnlineContact
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 12, No content clipping, Edge labels found: 12 (12 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### RankedTrajectory (id: `32cbc712-9476-4019-96ce-ecee079a7436`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "+ takeoffWeight: Weight"(+21px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RankedTrajectory;  x COPYRIGHT;  x RouteTrajectory
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected, All nodes have bgColor

### Aircraft (id: `eb801f56-d299-4e00-9b22-c80f94e7a183`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "AircraftRegistration"(+38px), "OtherAircraftTypeReference"(+22px), "+ otherAircraftType: CharacterString"(+45px), "AircraftAddress"(+7px), "AircraftTypeReference"(+35px)
- [medium] **node_overlap**: 11 overlapping pairs:  x AircraftRegistration;  x OtherAircraftTypeReference;  x AircraftAddress
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 9, No content clipping, Edge labels found: 7 (7 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### EnRoute (id: `36bd1600-4c5d-4bb1-bc8d-8bbbc5f545c6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "BoundaryCrossingCondition"(+91px), "+ AT_OR_ABOVE: string"(+21px), "+ AT_OR_BELOW: string"(+21px), "AltitudeInTransition"(+38px), "+ alternateAerodrome: AerodromeReference"(+30px)
- [medium] **node_overlap**: 5 overlapping pairs:  x BoundaryCrossingCondition;  x AltitudeInTransition;  x EnRoute
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 3, No content clipping, Edge labels found: 3 (3 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### Arrival (id: `10228178-9456-4c58-b62c-977f734d5f47`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ runwayDirection: RunwayDirectionDesign"(+45px), "+ filedRevisedDestinationAerodrome: Aero"(+49px), "+ aerodromeAlternate: AerodromeReference"(+12px), "+ runwayDirection: RunwayDirectionDesign"(+37px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Arrival;  x COPYRIGHT;  x ReclearanceInFlight
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 23 links/cross-references detected, All nodes have bgColor

### RadioactiveMaterials (id: `6468753e-1a38-4658-b623-7ab4c386b2ee`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "FissileExcepted"(+6px), "+ EXCEPTED: string"(+7px), "RadioactiveMaterialCategory"(+72px), "+ criticalitySafetyIndex: DecimalIndex"(+31px), "+ SPECIAL_FORM: string"(+32px)
- [medium] **node_overlap**: 7 overlapping pairs:  x FissileExcepted;  x RadioactiveMaterialCategory;  x RadioactiveMaterial
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### RangesAndChoices (id: `a851e972-ce89-40b6-8e0b-441ce0ab5bd5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 13 text elements overflow: "+ lowerSpeed: TrueAirspeed"(+18px), "+ upperSpeed: TrueAirspeed"(+18px), "+ otherColour: CharacterString"(+34px), "+ uom: UomAltitude"(+7px), "TemporalRange"(+6px)
- [medium] **node_overlap**: 14 overlapping pairs:  x TrueAirspeedRange;  x ColourChoice;  x Altitude
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 14, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 33 links/cross-references detected, All nodes have bgColor


---

## APM_META

### Prolaborate APM Metamodel (id: `8a27921c-0b6e-4ffd-9424-48c158a2040f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "«ArchiMate_ApplicationComponent»"(+89px), "«ArchiMate_BusinessRole»"(+38px), "«ArchiMate_BusinessActor»"(+43px), "«ArchiMate_BusinessActor»"(+43px), "IT Application Owner"(+45px)
- [medium] **node_overlap**: 30 overlapping pairs:  x Application;  x Stakeholder;  x Organization
- [medium] **missing_waypoints**: 14/23 edges (61%) have no waypoints

**Correct:** Node count: 27, Edge count: 23, No content clipping, Edge labels found: 0 (12 edges have label data), 46 links/cross-references detected, All nodes have bgColor


---

## APM_ESSENTIAL

### Project (id: `e2f9c3d2-0df5-4062-961e-11fd534d0770`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "BI Driven Marketing"(+38px), "One-Touch Digital Payment5"(+96px), "Digital Touchpoints"(+33px), "ERP Tools Fast Config"(+48px), "Next Gen Marketing"(+38px)
- [medium] **node_overlap**: 7 overlapping pairs:  x BI Driven Marketing;  x One-Touch Digital Payment5;  x Digital Touchpoints

**Correct:** Node count: 7, Edge count: 0, No content clipping, 27 links/cross-references detected, All nodes have bgColor

### Application Service (id: `ce61f487-3c7f-401b-a3c8-d92cb6bc9cf1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "«TEA_ApplicationService»"(+33px), "Seek Approvals"(+6px), "«TEA_ApplicationService»"(+33px), "Print & Distribute Invoice"(+78px), "«TEA_ApplicationService»"(+33px)
- [medium] **node_overlap**: 15 overlapping pairs:  x Seek Approvals;  x Print & Distribute Invoice;  x Invoice Creation

**Correct:** Node count: 15, Edge count: 0, No content clipping, 35 links/cross-references detected, All nodes have bgColor

### Application Inventory (id: `4b46db33-06f1-49be-8357-015b8cdb2f10`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "HR Management"(+13px), "Oracle Database Management"(+112px), "Spreadsheet Billing"(+35px), "Business Gateway"(+25px), "Amazon Connect"(+14px)
- [medium] **node_overlap**: 26 overlapping pairs:  x HR Management;  x Pension;  x SAP CRM
- [high] **missing_waypoints**: 62/62 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 26, Edge count: 62, No content clipping, Edge labels found: 0 (62 edges have label data), 46 links/cross-references detected, All nodes have bgColor

### Domain (id: `a69b4f5a-337e-4189-bdc8-99b2a0a34027`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Data;  x Security;  x Customer

**Correct:** Node count: 7, Edge count: 0, No content clipping, 27 links/cross-references detected, All nodes have bgColor

### IT Application Owner (id: `85a63b1d-8f88-45ac-9bdb-065c99f9318a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Philip;  x James;  x John

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected, All nodes have bgColor

### Stakeholder (id: `077ba17a-a4b2-4558-8b2b-e1e1a0a60268`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "Finance Operations"(+34px), "Chief Commercial Officer"(+73px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Finance Operations;  x CEO;  x CIO Office

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected, All nodes have bgColor

### Organization (id: `b5f7ae35-46da-43ab-a0ce-ca20210757d6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "Customer and Business Services"(+128px), "Strategy & Enterprise Services"(+117px), "Corporate Centre"(+19px), "Group Services"(+3px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Customer and Business Services;  x Strategy & Enterprise Services;  x Corporate Centre

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected, All nodes have bgColor

### MetaModel (id: `2b072b8a-7fad-49f1-8e2e-13635d784f16`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "«TEA_ApplicationService»"(+33px), "Application Service"(+33px), "«TEA_ApplicationDomain»"(+34px), "Application Domain"(+35px), "«TEA_ApplicationSubDomain»"(+55px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Project;  x Application Service;  x Application Domain
- [medium] **missing_waypoints**: 3/9 edges (33%) have no waypoints

**Correct:** Node count: 8, Edge count: 9, No content clipping, Edge labels found: 0 (9 edges have label data), 26 links/cross-references detected, All nodes have bgColor

### Application Landscape (id: `c340c26e-687b-471e-bac2-03ab00f60f7b`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 18 links/cross-references detected

### Application Portfolio Management (id: `0de1dbcc-06a9-448c-a898-ef918b5b0ebc`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 18 links/cross-references detected

