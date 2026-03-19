# EA Visual Audit — Iteration 0

**Date:** 2026-03-07
**Iteration:** 0 of 3
**Diagrams audited:** 163
**Diagrams with issues:** 160
**Total issues:** 651
**By severity:** critical=0, high=250, medium=401, low=0

## Summary by Issue Type

| Issue Type | Count | Severity |
|-----------|-------|----------|
| node_overlap | 160 | medium |
| text_overflow | 157 | medium |
| missing_waypoints | 146 | high |
| missing_bg_color | 144 | high |
| missing_edge_visual | 40 | medium |
| edge_stereotype_hidden | 3 | medium |
| missing_packages | 1 | medium |

---

## AIXM

### GM_Point_Profile (id: `899a01e9-290c-4d90-80ea-2c1b6d368435`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 1 overlapping pairs:  x GM_Point
- [high] **missing_bg_color**: All 1 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 1, Edge count: 0, No content clipping, 20 links/cross-references detected

### GM_Curve Profile (id: `4e7e4f73-d646-46c9-ac91-a8c59c1cf6ac`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "GM_GeodesicString"(+33px), "GM_CurveSegment"(+17px)
- [medium] **node_overlap**: 8 overlapping pairs:  x GM_Geodesic;  x GM_Circle;  x GM_Arc
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 4 (1 edges have label data), 27 links/cross-references detected

### Aggregation (id: `8163ef34-3308-403d-b7a3-57298405820d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "GM_MultiSurface"(+15px)
- [medium] **node_overlap**: 3 overlapping pairs:  x GM_MultiSurface;  x GM_MultiCurve;  x GM_MultiPoint
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 3, Edge count: 0, No content clipping, 22 links/cross-references detected

### Basic Message (id: `344da12c-cdc9-46c4-9b95-e8474f60a3cb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ identifier: CodeUUIDType"(+46px), "«collectionMemberChoice»"(+32px), "BasicMessageMemberAIXM"(+84px), "AIXMBasicMessage"(+32px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AIXMFeature;  x BasicMessageMemberAIXM;  x AIXMBasicMessage
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 4 (2 edges have label data), 24 links/cross-references detected

### 2 - Surveillance Equipment (id: `b607015b-26e6-41cc-9adf-fb6d2d5d048a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "+ type: CodeRadioFrequencyAreaType"(+43px), "+ angleScallop: ValAngleType"(+5px), "+ signalType: CodeRadioSignalType"(+36px), "EquipmentChoice"(+7px), "SecondarySurveillanceRadar"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x SecondarySurveillanceRadar;  x PrimarySurveillanceRadar;  x SurveillanceGroundStation
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 14/15 edges (93%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 15, No content clipping, Edge labels found: 30 (9 edges have label data), 33 links/cross-references detected

### 1 - Surveillance System (id: `5e3bc371-93d6-46e7-84f4-eabc67a9248c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: TextDesignatorType"(+27px)
- [medium] **node_overlap**: 4 overlapping pairs:  x RadarComponent;  x RadarEquipment;  x OrganisationAuthority
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 10, No content clipping, Edge labels found: 27 (10 edges have label data), 28 links/cross-references detected

### 2 - Obstacle Assessment Associations (id: `6a9eefe2-5dff-4652-94cd-448503bb9b8d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ finalApproachPath: CodeMinimaFinalAppr"(+59px), "+ requiredNavigationPerformance: CodeRNP"(+9px), "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SegmentLeg;  x HoldingAssessment;  x ObstacleAssessmentArea
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 18 (6 edges have label data), 28 links/cross-references detected

### 1 - Obstacle Assessment Feature (id: `391f4aa7-e2da-43dd-bbda-7591dc7cf02b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 20 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px)
- [medium] **node_overlap**: 6 overlapping pairs:  x Surface;  x ObstacleAssessmentArea;  x AltitudeAdjustment
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 30 links/cross-references detected

### 1 - Standard Levels (id: `d785910c-7d5a-41b6-bb68-ff9e71253e3a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px)
- [medium] **node_overlap**: 6 overlapping pairs:  x AirspaceLayer;  x Airspace;  x StandardLevelSector
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected

### 1 - Properties with Schedule (id: `ecf32784-9411-4b5f-882e-d41d2f1b836b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ type: CodeSpecialDateType"(+34px), "+ dateDay: DateMonthDayType"(+34px), "+ dateYear: DateYearType"(+15px), "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px)
- [medium] **node_overlap**: 4 overlapping pairs:  x SpecialDate;  x OrganisationAuthority;  x Timesheet
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 9 (4 edges have label data), 26 links/cross-references detected

### 1 - Radio Frequency Limitation (id: `8337dad8-b53f-4a60-9b87-ae51cd719306`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ precisionApproachRadarType: CodePARTyp"(+45px), "SecondarySurveillanceRadar"(+42px), "+ transponder: CodeTransponderType"(+48px), "+ autonomous: CodeYesNoType"(+4px), "+ type: CodeSpecialNavigationStationType"(+58px)
- [medium] **node_overlap**: 8 overlapping pairs:  x SecondarySurveillanceRadar;  x SpecialNavigationStation;  x NavaidEquipment
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 8, No content clipping, Edge labels found: 24 (3 edges have label data), 31 links/cross-references detected

### 1 - Light Element (id: `44f973be-3ac8-481b-a11d-194ee5af01b2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "PropertiesWithSchedule"(+47px), "+ status: CodeStatusOperationsType"(+56px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 4 overlapping pairs:  x PropertiesWithSchedule;  x LightElementStatus;  x ElevatedPoint
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 26 links/cross-references detected

### 2 - Flight Characteristics (id: `4ef1c4a2-ace3-48e0-98fd-22d1e0c0b721`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ rule: CodeFlightRuleType"(+13px), "+ status: CodeFlightStatusType"(+38px), "+ military: CodeMilitaryStatusType"(+63px), "+ origin: CodeFlightOriginType"(+38px), "+ purpose: CodeFlightPurposeType"(+50px)
- [medium] **node_overlap**: 1 overlapping pairs:  x FlightCharacteristic
- [high] **missing_bg_color**: All 1 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 1, Edge count: 0, No content clipping, 23 links/cross-references detected

### 1 - Aircraft Characteristics (id: `a5f968a1-81f0-4ce2-ad2a-b4afa866917d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px)
- [medium] **node_overlap**: 1 overlapping pairs:  x AircraftCharacteristic
- [high] **missing_bg_color**: All 1 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 1, Edge count: 0, No content clipping, 23 links/cross-references detected

### 1 - Address (id: `34a8d61a-8a8b-4dc0-8991-6c2d80863abd`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "TelephoneContact"(+9px), "+ voice: TextPhoneType"(+18px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ContactInformation;  x TelephoneContact;  x OnlineContact
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 6, No content clipping, Edge labels found: 9 (3 edges have label data), 27 links/cross-references detected

### 7 - Search and Rescue Services (id: `3be220c4-8d90-470f-a48f-217bf87ccdf2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px), "+ upperLowerSeparation: ValFLType"(+13px), "SearchRescueService"(+27px), "+ type: CodeServiceSARType"(+36px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RoutePortion;  x Airspace;  x SearchRescueService
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 24 links/cross-references detected

### 6 - Air Traffic Management (id: `bf71ad22-8b22-479d-b513-2c2b3dac8b6f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "+ designatorPrefix: CodeAerialRefuelling"(+82px), "+ designatorSuffix: TextDesignatorType"(+7px), "+ designatorDirection: CodeCardinalDirec"(+69px), "+ receiverChannel: CodeTACANChannelType"(+13px), "+ reverseDirectionTurn: CodeDirectionTur"(+51px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AerialRefuelling;  x Airspace;  x AirTrafficManagementService
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 4/5 edges (80%) have no waypoints

**Correct:** Node count: 4, Edge count: 5, No content clipping, Edge labels found: 12 (5 edges have label data), 25 links/cross-references detected

### 5 - Air Traffic Control Services (id: `6660968e-b956-47de-bfd6-2b0f6d1f35c2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ turnDirection: CodeDirectionTurnType"(+6px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 6 overlapping pairs:  x AerialRefuelling;  x Airspace;  x AirTrafficControlService
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/12 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 12, No content clipping, Edge labels found: 27 (10 edges have label data), 30 links/cross-references detected

### 4 - Information Service (id: `0e2b7b9e-9fe2-4890-a862-2abfb871920c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ turnDirection: CodeDirectionTurnType"(+6px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 5 overlapping pairs:  x AirportHeliport;  x Airspace;  x AerialRefuelling
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 10, No content clipping, Edge labels found: 27 (10 edges have label data), 29 links/cross-references detected

### 3 - Airport Ground Services (id: `8208145b-a72f-4bff-abba-e794146941f2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ type: CodeOxygenType"(+31px), "+ type: CodeNitrogenType"(+39px), "+ category: CodeOilType"(+38px), "+ category: CodeFuelType"(+38px), "+ jetwayAvailability: CodeYesNoType"(+23px)
- [medium] **node_overlap**: 12 overlapping pairs:  x Oxygen;  x Nitrogen;  x Oil
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 11, No content clipping, Edge labels found: 18 (6 edges have label data), 33 links/cross-references detected

### 2 - Communication Channel (id: `2f7e37e4-ed36-4904-a2cf-88f97a6e38e2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 20 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeRadioFrequencyAreaType"(+43px), "+ angleScallop: ValAngleType"(+5px), "+ signalType: CodeRadioSignalType"(+36px), "EquipmentChoice"(+7px)
- [medium] **node_overlap**: 7 overlapping pairs:  x RadioCommunicationOperationalStatus;  x PropertiesWithSchedule;  x ElevatedPoint
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 27 (8 edges have label data), 31 links/cross-references detected

### 1 - Service Overview (id: `715fa8ef-e397-4bde-8580-70c256c5a7ec`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "AirportClearanceService"(+36px), "+ snowPlan: TextInstructionType"(+54px), "AirportSuppliesService"(+60px), "+ category: CodeFireFightingType"(+23px), "+ standard: CodeAviationStandardsType"(+54px)
- [medium] **node_overlap**: 11 overlapping pairs:  x PassengerService;  x AirTrafficManagementService;  x GroundTrafficControlService
- [high] **missing_bg_color**: All 19 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 20/22 edges (91%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 19, Edge count: 22, No content clipping, Edge labels found: 24 (10 edges have label data), 40 links/cross-references detected

### 1 - RulesProcedures (id: `df3bf2ae-a6e6-4017-9e86-f6f609a87bbb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ designator: CodeAirspaceDesignatorType"(+57px), "+ controlType: CodeMilitaryOperationsTyp"(+63px), "+ upperLowerSeparation: ValFLType"(+13px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px)
- [medium] **node_overlap**: 3 overlapping pairs:  x Airspace;  x AirportHeliport;  x RulesProcedures
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 24 links/cross-references detected

### 3 - Flight restriction - routings (id: `6498a3fc-ddd6-40d7-9eb6-8fafcea6d530`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px), "+ contingencyRoute: CodeYesNoType"(+15px), "StandardInstrumentArrival"(+4px), "+ designator: TextSIDSTARDesignatorType"(+53px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DirectFlightSegment;  x SignificantPoint;  x RoutePortion
- [high] **missing_bg_color**: All 11 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 12/18 edges (67%) have no waypoints

**Correct:** Node count: 11, Edge count: 18, No content clipping, Edge labels found: 51 (12 edges have label data), 33 links/cross-references detected

### 2 - Flight restrictions - conditions (id: `d74e8b6b-df3e-4bbb-8b31-1492355f5dc2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 36 text elements overflow: "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px), "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px), "+ contingencyRoute: CodeYesNoType"(+15px)
- [medium] **node_overlap**: 10 overlapping pairs:  x DirectFlightClass;  x DirectFlight;  x SignificantPoint
- [high] **missing_bg_color**: All 20 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 24/33 edges (73%) have no waypoints

**Correct:** Node count: 20, Edge count: 33, No content clipping, Edge labels found: 87 (23 edges have label data), 42 links/cross-references detected

### 1 - Flight Restrictions (id: `7be5b122-04de-4624-9a3f-71e01418bf04`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "+ speedReference: CodeSpeedReferenceType"(+44px), "+ speedCriteria: CodeComparisonType"(+13px)
- [medium] **node_overlap**: 9 overlapping pairs:  x FlightRoutingElement;  x FlightRestrictionRoute;  x FlightRestrictionLevel
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 30 (10 edges have label data), 32 links/cross-references detected

### 6 - Route Portion DME (id: `67bc6a8b-0f63-49f8-a876-574ba24c3ecb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ channel: CodeDMEChannelType"(+16px), "+ ghostFrequency: ValFrequencyType"(+48px), "+ displace: ValDistanceType"(+4px), "+ criticalDME: CodeYesNoType"(+40px), "+ satisfactory: CodeYesNoType"(+46px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RoutePortion;  x DME;  x RouteDME
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected

### 5 - Route Portion Change Over Points (id: `52e0c45d-2fcc-4ba7-b34a-0f3d749b9279`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "ChangeOverPoint"(+5px), "+ distance: ValDistanceType"(+48px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SignificantPoint;  x RoutePortion;  x ChangeOverPoint
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 2/5 edges (40%) have no waypoints

**Correct:** Node count: 3, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 25 links/cross-references detected

### 4 - Route Availability (id: `39d073f1-8365-4689-9719-2d775a5f1ab4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ unitOfMeasurement: CodeDistanceVertica"(+83px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ designatorPrefix: CodeAerialRefuelling"(+82px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AirspaceLayer;  x RouteSegment;  x PropertiesWithSchedule
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/6 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 12 (5 edges have label data), 28 links/cross-references detected

### 3 - Route Portion (id: `d19f7d44-5e57-41bf-9ab3-376a50b3806c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px), "+ designatorSuffix: CodeRouteDesignatorS"(+9px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RouteSegment;  x DesignatedPoint;  x Navaid
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 4/7 edges (57%) have no waypoints

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 21 (5 edges have label data), 28 links/cross-references detected

### 2 - Route Segment (id: `326177f7-16dd-4dab-9464-4e8b004071c2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ reportingATC: CodeATCReportingType"(+44px), "+ radarGuidance: CodeYesNoType"(+7px), "+ roleMilitaryTraining: CodeMilitaryRout"(+81px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px)
- [medium] **node_overlap**: 5 overlapping pairs:  x EnRouteSegmentPoint;  x Curve;  x ObstacleAssessmentArea
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/7 edges (86%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 18 (6 edges have label data), 28 links/cross-references detected

### 1 - Routes (id: `f8682a91-258e-47d1-b8e3-c162b2f5e3e1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "+ minimumObstacleClearanceAltitude: ValD"(+71px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px), "+ designatorSuffix: CodeRouteDesignatorS"(+9px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RouteSegment;  x OrganisationAuthority;  x Route
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 9 (4 edges have label data), 26 links/cross-references detected

### XMLSchemaDatatypes (id: `a07e8bbf-eddc-414a-865a-6c746cc100a7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "normalizedString"(+3px), "anySimpleType"(+3px), "anyAtomicType"(+4px), "+ fractionDigits: null"(+32px), "nonNegativeInteger"(+39px)
- [medium] **node_overlap**: 18 overlapping pairs:  x string;  x token;  x ENTITIES
- [high] **missing_bg_color**: All 47 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 47, Edge count: 46, No content clipping, 66 links/cross-references detected

### Temp (id: `6b4ed1d1-abd7-4756-873d-52e79050d364`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "CodeBuoyDesignatorBaseType"(+97px), "CodeBuoyDesignatorType"(+27px), "+ nilReason: NilReasonEnumeration"(+48px), "AlphanumericType"(+17px), "CodeICAOCountryBaseType"(+88px)
- [medium] **node_overlap**: 10 overlapping pairs:  x CodeBuoyDesignatorBaseType;  x CodeBuoyDesignatorType;  x string
- [high] **missing_bg_color**: All 13 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 12, No content clipping, 34 links/cross-references detected

### GM_Surface Profile (id: `0d7be0a1-c890-4fc9-ac73-ff6223bb7b2d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "GM_SurfacePatch"(+5px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ;  x ;  x GM_Polygon
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 5, No content clipping, Edge labels found: 4 (1 edges have label data), 24 links/cross-references detected

### 3 - Segment Leg (id: `1170afe3-c792-473c-9301-9870734f6dac`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 33 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ indicationDirection: CodeDirectionRefe"(+59px), "+ cardinalDirection: CodeCardinalDirecti"(+40px), "+ minimumReceptionAltitude: ValDistanceV"(+71px), "+ minimumReceptionAltitude: ValDistanceV"(+71px)
- [medium] **node_overlap**: 7 overlapping pairs:  x DepartureLeg;  x ApproachLeg;  x AircraftCharacteristic
- [high] **missing_bg_color**: All 13 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 13/15 edges (87%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 15, No content clipping, Edge labels found: 33 (11 edges have label data), 35 links/cross-references detected

### 2 - Restricted Navigation (id: `1940ec2b-b342-4bb7-909d-27f667cb018d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px)
- [medium] **node_overlap**: 5 overlapping pairs:  x Procedure;  x CircleSector;  x Surface
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 27 links/cross-references detected

### 1 - Overview (id: `c4593ec5-bad1-4588-a487-bca7d2e69905`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 26 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ requiredNavigationPerformance: CodeRNP"(+53px), "+ minimumObstacleClearanceAltitude: ValD"(+80px), "+ courseReversalInstruction: TextInstruc"(+3px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DepartureLeg;  x StandardInstrumentDeparture;  x ProcedureTransitionLeg
- [high] **missing_bg_color**: All 14 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 16/17 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 14, Edge count: 17, No content clipping, Edge labels found: 33 (11 edges have label data), 36 links/cross-references detected

### 1- Minimum and Emergency Safe Altitude (id: `8f8c8c94-05f1-4447-919c-dff6f6d3ecf0`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ altitudeAdjustmentType: CodeAltitudeAd"(+71px), "+ altitudeAdjustment: ValDistanceVertica"(+28px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AltitudeAdjustment;  x Surface;  x SafeAltitudeAreaSector
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 11, No content clipping, Edge labels found: 30 (9 edges have label data), 31 links/cross-references detected

### 5 - Navigation System Checkpoint (id: `399ea198-2b9a-45a1-8885-41cc6cb7fde8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: CodeNavaidDesignatorType"(+22px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NavaidEquipment;  x VOR;  x CheckpointVOR
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 15 (5 edges have label data), 29 links/cross-references detected

### 4 - Special Navigation System (id: `54d6c1f8-43d1-43fd-a712-f7548ddf4a1c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "PropertiesWithSchedule"(+47px), "SpecialNavigationStationStatus"(+34px), "+ operationalStatus: CodeStatusNavaidTyp"(+60px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px)
- [medium] **node_overlap**: 7 overlapping pairs:  x SpecialNavigationStationStatus;  x ElevatedPoint;  x AuthorityForSpecialNavigationSystem
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 18 (7 edges have label data), 30 links/cross-references detected

### 3 - Navaid Limitation (id: `79deae43-e681-470b-855e-e812711da0d5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ type: CodeSpecialNavigationStationType"(+58px), "+ emission: CodeRadioEmissionType"(+14px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x SpecialNavigationStation;  x NavaidEquipment
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 18 (3 edges have label data), 29 links/cross-references detected

### 2 - Navaid Equipment (id: `ec452e8e-99a6-450d-95c0-1fee3de01928`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 38 text elements overflow: "+ trueBearingAccuracy: ValAngleType"(+39px), "+ magneticBearing: ValBearingType"(+26px), "+ angleProportionalLeft: ValAngleType"(+51px), "+ angleProportionalRight: ValAngleType"(+58px), "+ angleCoverLeft: ValAngleType"(+8px)
- [medium] **node_overlap**: 8 overlapping pairs:  x NDB;  x MarkerBeacon;  x TACAN
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 11, No content clipping, 34 links/cross-references detected

### 1 - ProcedureUsage (id: `667669eb-10b8-4262-a317-f0bb3f356d4d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "PropertiesWithSchedule"(+47px), "+ communicationFailureInstruction: TextI"(+87px), "+ codingStandard: CodeProcedureCodingSta"(+56px), "+ status: CodeProcedureAvailabilityType"(+66px)
- [medium] **node_overlap**: 3 overlapping pairs:  x PropertiesWithSchedule;  x Procedure;  x ProcedureAvailability
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 3 (1 edges have label data), 25 links/cross-references detected

### 6 - Segment Leg DME (id: `540c37c3-b606-430a-80c8-3ab93d4ed503`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ endConditionDesignator: CodeSegmentTer"(+59px), "+ courseDirection: CodeDirectionReferenc"(+16px), "+ upperLimitAltitude: ValDistanceVertica"(+16px), "+ upperLimitReference: CodeVerticalRefer"(+34px), "+ lowerLimitAltitude: ValDistanceVertica"(+16px)
- [medium] **node_overlap**: 3 overlapping pairs:  x SegmentLeg;  x DME;  x ProcedureDME
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected

### 5 - LandingTakeOffArea (id: `e5caa0fb-9071-444f-95f8-163ff888fbeb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ approachMarkingCondition: CodeMarkingC"(+50px), "+ precisionApproachGuidance: CodeApproac"(+57px), "StandardInstrumentDeparture"(+29px), "+ designator: TextSIDSTARDesignatorType"(+53px)
- [medium] **node_overlap**: 6 overlapping pairs:  x TouchDownLiftOff;  x RunwayDirection;  x StandardInstrumentDeparture
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected

### 4 - SegmentLegSpecialization (id: `5bef44f2-768e-4cbf-bc37-66f050199b2f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 34 text elements overflow: "TerminalSegmentPoint"(+16px), "+ role: CodeProcedureFixRoleType"(+52px), "+ leadRadial: ValBearingType"(+27px), "+ leadDME: ValDistanceType"(+15px), "+ indicatorFACF: CodeYesNoType"(+40px)
- [medium] **node_overlap**: 10 overlapping pairs:  x IntermediateLeg;  x InitialLeg;  x ArrivalFeederLeg
- [high] **missing_bg_color**: All 15 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 17/18 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 15, Edge count: 18, No content clipping, Edge labels found: 30 (10 edges have label data), 37 links/cross-references detected

### 2 - NavigationArea (id: `39214e58-a967-4891-9a00-e84ec0dd893a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ angleDirectionReference: CodeDirection"(+74px), "+ upperLimitReference: CodeVerticalRefer"(+42px), "+ lowerLimitReference: CodeVerticalRefer"(+42px), "+ turnDirection: CodeDirectionTurnType"(+29px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x SectorDesign;  x Obstruction
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 21 (7 edges have label data), 30 links/cross-references detected

### 1 - SID (id: `43fda1f9-0d40-4d66-99f8-337fd29fe978`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ minimumEnrouteAltitude: ValDistanceVer"(+9px), "+ minimumCrossingAtEndReference: CodeVer"(+65px), "+ maximumCrossingAtEndReference: CodeVer"(+65px)
- [medium] **node_overlap**: 7 overlapping pairs:  x StandardInstrumentDeparture;  x DepartureLeg;  x ProcedureTransitionLeg
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 14, No content clipping, Edge labels found: 33 (11 edges have label data), 34 links/cross-references detected

### 1 - STAR (id: `6f933ecb-e661-4e5c-af68-3c4c20164880`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ safeAreaType: CodeSafeAltitudeType"(+50px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "LandingTakeoffAreaCollection"(+95px)
- [medium] **node_overlap**: 7 overlapping pairs:  x LandingTakeoffAreaCollection;  x ArrivalLeg;  x ProcedureTransitionLeg
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 10, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected

### 1 - Minima (id: `ac6592c3-47bf-44e3-8bb9-9e39f4159211`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "EquipmentUnavailableAdjustmentColumn"(+83px), "+ guidanceEquipment: CodeApproachType"(+14px), "+ landingSystemLights: CodeYesNoType"(+8px), "+ visibilityAdjustment: ValDistanceVerti"(+77px), "+ approachLightingInoperative: CodeYesNo"(+58px)
- [medium] **node_overlap**: 5 overlapping pairs:  x EquipmentUnavailableAdjustmentColumn;  x EquipmentUnavailableAdjustment;  x LandingTakeoffAreaCollection
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 28 links/cross-references detected

### 1 - Circling (id: `4890c709-9741-46e6-b5be-827e8bdbb361`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 24 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ courseReversalInstruction: TextInstruc"(+3px), "+ additionalEquipment: CodeApproachEquip"(+66px), "LandingTakeoffAreaCollection"(+95px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Minima;  x CircleSector;  x PropertiesWithSchedule
- [high] **missing_bg_color**: All 11 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 13/16 edges (81%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 16, No content clipping, Edge labels found: 45 (15 edges have label data), 34 links/cross-references detected

### 1 - Final Segment Leg Conditions (id: `6298c449-a342-4a35-af10-ed8f25479ce2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ isRemote: CodeYesNoType"(+23px), "+ isPrimary: CodeYesNoType"(+30px), "LandingTakeoffAreaCollection"(+95px), "+ altitudeCode: CodeMinimumAltitudeType"(+25px), "+ altitudeReference: CodeVerticalReferen"(+69px)
- [medium] **node_overlap**: 5 overlapping pairs:  x AircraftCharacteristic;  x ObstacleAssessmentArea;  x FASDataBlock
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected

### 1 - Terminal Arrival Area (id: `7e152e69-79b1-4f9c-9229-5920cda683e1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 17 text elements overflow: "+ altitudeAdjustmentType: CodeAltitudeAd"(+71px), "+ altitudeAdjustment: ValDistanceVertica"(+28px), "+ requiredClearance: ValDistanceType"(+25px), "+ minimumAltitude: ValDistanceVerticalTy"(+63px), "+ surfacePenetration: CodeYesNoType"(+19px)
- [medium] **node_overlap**: 7 overlapping pairs:  x CircleSector;  x InstrumentApproachProcedure;  x Surface
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 9/11 edges (82%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 11, No content clipping, Edge labels found: 30 (9 edges have label data), 32 links/cross-references detected

### 2 - Approach Procedure Tables (id: `056031cb-55a4-4999-8ffb-3e295722dcf4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "+ measurementPoint: CodeProcedureDistanc"(+54px), "+ altitudeReference: CodeVerticalReferen"(+60px), "+ startingMeasurementPoint: CodeProcedur"(+71px), "+ endingMeasurementPoint: CodeProcedureD"(+58px), "+ startingMeasurementPoint: CodeProcedur"(+71px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ApproachAltitudeTable;  x ApproachDistanceTable;  x ApproachTimingTable
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 28 links/cross-references detected

### 1 - Approach Procedure Overview (id: `f12d27ea-c871-48b5-8179-a965611f5c9d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ seqNumberARINC: NoSequenceType"(+29px), "+ endConditionDesignator: CodeSegmentTer"(+59px), "+ courseDirection: CodeDirectionReferenc"(+16px), "+ upperLimitAltitude: ValDistanceVertica"(+16px), "+ upperLimitReference: CodeVerticalRefer"(+34px)
- [medium] **node_overlap**: 7 overlapping pairs:  x MissedApproachGroup;  x CirclingArea;  x LandingTakeoffAreaCollection
- [high] **missing_bg_color**: All 13 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 15/15 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 13, Edge count: 15, No content clipping, Edge labels found: 42 (14 edges have label data), 36 links/cross-references detected

### 2 - Unit (id: `9feeb334-0428-4a21-a358-5625743be1e9`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ type: CodeUnitDependencyType"(+39px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "PropertiesWithSchedule"(+47px)
- [medium] **node_overlap**: 6 overlapping pairs:  x PropertiesWithSchedule;  x UnitAvailability;  x ElevatedPoint
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 10/12 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 12, No content clipping, Edge labels found: 27 (11 edges have label data), 29 links/cross-references detected

### 1 - Organisation/Authority (id: `5fbbf48e-f504-4ef0-96bd-f462840bf381`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "ContactInformation"(+35px), "+ name: TextNameType"(+19px), "+ title: TextNameType"(+25px), "OrganisationAuthorityAssociation"(+69px), "+ type: CodeOrganisationHierarchyType"(+56px)
- [medium] **node_overlap**: 3 overlapping pairs:  x ContactInformation;  x OrganisationAuthorityAssociation;  x OrganisationAuthority
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 1/2 edges (50%) have no waypoints

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 3 (2 edges have label data), 24 links/cross-references detected

### 3 - Obstacle Areas (id: `5270698f-67a6-492a-b660-58eb609abfc0`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ type: CodeVerticalStructureType"(+21px), "+ markingICAOStandard: CodeYesNoType"(+40px), "+ lightingICAOStandard: CodeYesNoType"(+46px), "+ synchronisedLighting: CodeYesNoType"(+46px), "+ horizontalAccuracy: ValDistanceType"(+60px)
- [medium] **node_overlap**: 5 overlapping pairs:  x Surface;  x RunwayDirection;  x AirportHeliport
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/9 edges (89%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 9, No content clipping, Edge labels found: 24 (9 edges have label data), 28 links/cross-references detected

### 2 - Vertical Structure Associations (id: `774c0647-1419-46f3-8e02-ae00d88dc2c6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "+ type: CodePassengerServiceType"(+46px), "+ emergencyLighting: CodeYesNoType"(+34px), "+ intensityLevel: CodeLightIntensityType"(+71px), "+ designator: CodeNavaidDesignatorType"(+22px), "+ emissionClass: CodeRadioEmissionType"(+22px)
- [medium] **node_overlap**: 7 overlapping pairs:  x GroundLightSystem;  x NavaidEquipment;  x SpecialNavigationStation
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/13 edges (85%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 13, No content clipping, Edge labels found: 33 (13 edges have label data), 29 links/cross-references detected

### 1 - Vertical Structures (id: `f6741af3-249f-4ed3-9bb0-a55d98f3a06e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ intensityLevel: CodeLightIntensityType"(+71px), "+ intensity: ValLightIntensityType"(+34px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 8 overlapping pairs:  x ElevatedPoint;  x ElevatedCurve;  x ElevatedSurface
- [high] **missing_bg_color**: All 11 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 12/13 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 11, Edge count: 13, No content clipping, Edge labels found: 30 (10 edges have label data), 32 links/cross-references detected

### 1 - Notes (id: `9db807f4-8e69-497d-ab68-8c8af12f8bae`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ identifier: CodeUUIDType"(+46px), "+ note: TextNoteType"(+19px), "+ propertyName: TextPropertyNameType"(+45px), "+ purpose: CodeNotePurposeType"(+8px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AIXMObject;  x AIXMFeature;  x LinguisticNote
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 25 links/cross-references detected

### 1 - GroundLight (id: `0d51e9a4-0435-4f89-a9a6-b8531d8b85ff`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ type: CodeVerticalStructureType"(+21px)
- [medium] **node_overlap**: 4 overlapping pairs:  x ElevatedPoint;  x VerticalStructure;  x AirportHeliport
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 12 (4 edges have label data), 26 links/cross-references detected

### 2 - Designated Point (id: `92b36554-071c-4177-b6c8-812f9089adaa`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ indicationDirection: CodeDirectionRefe"(+59px), "+ cardinalDirection: CodeCardinalDirecti"(+40px), "+ minimumReceptionAltitude: ValDistanceV"(+71px), "+ priorFixTolerance: ValDistanceSignedTy"(+66px)
- [medium] **node_overlap**: 6 overlapping pairs:  x PointReference;  x DistanceIndication;  x TouchDownLiftOff
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 9/10 edges (90%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 10, No content clipping, Edge labels found: 30 (10 edges have label data), 30 links/cross-references detected

### 1 - Significant Points (id: `ab5f4bac-afab-4212-bdb2-b5b961454b9f`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ designator: CodeDesignatedPointDesigna"(+66px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px)
- [medium] **node_overlap**: 5 overlapping pairs:  x TouchDownLiftOff;  x AirportHeliport;  x RunwayCentrelinePoint
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 13, No content clipping, Edge labels found: 39 (7 edges have label data), 29 links/cross-references detected

### 2 - Point Reference (id: `610dee62-2d64-4dfd-b002-9b979c59a94e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ signalPerformance: CodeSignalPerforman"(+61px), "+ courseQuality: CodeCourseQualityILSTyp"(+10px), "+ integrityLevel: CodeIntegrityLevelILST"(+23px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ horizontalAccuracy: ValDistanceType"(+60px)
- [medium] **node_overlap**: 7 overlapping pairs:  x Navaid;  x SignificantPoint;  x DistanceIndication
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 12/15 edges (80%) have no waypoints

**Correct:** Node count: 10, Edge count: 15, No content clipping, Edge labels found: 42 (11 edges have label data), 32 links/cross-references detected

### 1 - Segment Points (id: `3c080098-c9e0-452c-8fba-24e1623abcac`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "TerminalSegmentPoint"(+16px), "+ role: CodeProcedureFixRoleType"(+52px), "+ leadRadial: ValBearingType"(+27px), "+ leadDME: ValDistanceType"(+15px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SignificantPoint;  x Surface;  x TerminalSegmentPoint
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 9 (3 edges have label data), 28 links/cross-references detected

### 1 - Navaids (id: `2eb39860-eaa4-4351-9a65-a1870095363e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "+ designator: CodeAirportHeliportDesigna"(+4px), "+ fieldElevationAccuracy: ValDistanceVer"(+17px), "+ magneticVariationChange: ValMagneticVa"(+67px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "+ approachMarkingCondition: CodeMarkingC"(+50px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NavaidEquipmentMonitoring;  x PropertiesWithSchedule;  x NavaidOperationalStatus
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 17/18 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 18, No content clipping, Edge labels found: 45 (16 edges have label data), 34 links/cross-references detected

### 1 - Guidance Service (id: `4551f822-a3de-44bc-9b8c-ee38d1a62897`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ signalPerformance: CodeSignalPerforman"(+61px), "+ courseQuality: CodeCourseQualityILSTyp"(+10px), "+ integrityLevel: CodeIntegrityLevelILST"(+23px), "+ generalTerrainMonitor: CodeYesNoType"(+54px), "+ broadcastIdentifier: TextDesignatorTyp"(+72px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Navaid;  x RadarSystem;  x SpecialNavigationSystem
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 26 links/cross-references detected

### 2 - Unplanned Holding (id: `4cb0df51-5e6d-44f1-937e-c33400f79486`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ type: CodeObstacleAssessmentSurfaceTyp"(+26px), "+ assessedAltitude: ValDistanceVerticalT"(+39px), "+ slopeLowerAltitude: ValDistanceVertica"(+52px), "+ surfaceZone: CodeObstructionIdSurfaceZ"(+64px), "+ turnDirection: CodeDirectionTurnType"(+6px)
- [medium] **node_overlap**: 6 overlapping pairs:  x ObstacleAssessmentArea;  x HoldingPattern;  x PointReference
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 28 links/cross-references detected

### 1 - Holding Pattern (id: `2aa135e2-d9f9-45e5-8c85-69eaeab1d32d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "HoldingPatternDuration"(+52px), "+ duration: ValDurationType"(+48px), "HoldingPatternDistance"(+60px), "+ length: ValDistanceType"(+44px), "HoldingPatternLength"(+33px)
- [medium] **node_overlap**: 5 overlapping pairs:  x HoldingPatternDistance;  x HoldingPatternLength;  x SegmentPoint
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 6, No content clipping, Edge labels found: 18 (6 edges have label data), 27 links/cross-references detected

### 1 - Geometry (id: `c3a65d8d-d8d6-4a55-bb3b-c3f5ffaab0b8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ elevation: ValDistanceVerticalType"(+30px)
- [medium] **node_overlap**: 9 overlapping pairs:  x GM_Point;  x GM_Surface;  x GM_Curve
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 6, No content clipping, 30 links/cross-references detected

### 4 - Airspace Activation (id: `834ef6b8-ea68-4dc9-acf0-0c50bf99026e`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ navigationSpecification: CodeNavigatio"(+18px), "+ antiCollisionAndSeparationEquipment: C"(+87px), "+ unitOfMeasurement: CodeDistanceVertica"(+83px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AircraftCharacteristic;  x StandardLevelColumn;  x AirspaceLayer
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 18 (7 edges have label data), 28 links/cross-references detected

### 3 - Airspace Classification (id: `b6c6716e-116d-4fad-a291-aeb838ccc8ca`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "PropertiesWithSchedule"(+47px), "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ classification: CodeAirspaceClassifica"(+87px)
- [medium] **node_overlap**: 4 overlapping pairs:  x PropertiesWithSchedule;  x AirspaceLayer;  x AirspaceLayerClass
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected

### 2 - Airspace Associations (id: `718fd196-2b0a-4b93-8586-42abe151c863`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 13 text elements overflow: "+ category: CodeRuleProcedureType"(+45px), "+ title: CodeRuleProcedureTitleType"(+58px), "+ designator: CodeOrganisationDesignator"(+65px), "+ military: CodeMilitaryOperationsType"(+28px), "AuthorityForAirspace"(+41px)
- [medium] **node_overlap**: 6 overlapping pairs:  x OrganisationAuthority;  x AuthorityForAirspace;  x SignificantPoint
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 21 (8 edges have label data), 28 links/cross-references detected

### 1 - Airspace Feature (id: `ee05da6f-eb39-4269-96c0-a2b72d282bb1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "+ horizontalAccuracy: ValDistanceType"(+60px), "+ name: TextNameType"(+3px), "+ type: CodeGeoBorderType"(+34px), "+ horizontalAccuracy: ValDistanceType"(+60px), "+ dependency: CodeAirspaceDependencyType"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Curve;  x GeoBorder;  x SignificantPoint
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 7, No content clipping, Edge labels found: 15 (5 edges have label data), 29 links/cross-references detected

### 3 - Taxi Holding Position (id: `52b0a0c0-8bfd-482b-874c-5e22597c9f57`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "TaxiHoldingPositionLightSystem"(+63px), "+ type: CodeLightHoldingPositionType"(+55px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ElevatedPoint;  x Runway;  x GuidanceLine
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 15 (5 edges have label data), 28 links/cross-references detected

### 2 - Guidance Line (id: `eda09b3b-aa61-409f-9e84-4bf6a9f5f7dd`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "GuidanceLineLightSystem"(+82px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RunwayCentrelinePoint;  x Taxiway;  x TouchDownLiftOff
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 31 links/cross-references detected

### 1 - Taxiway (id: `54d0256a-529a-4e9a-b98a-34de02635a09`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ position: CodeTaxiwaySectionType"(+50px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 5 overlapping pairs:  x SurfaceCharacteristics;  x TaxiwayElement;  x TaxiwayMarking
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 12, No content clipping, Edge labels found: 36 (12 edges have label data), 30 links/cross-references detected

### 1 - Surface Contamination (id: `13b4df94-f665-46d1-8c0a-4b9ed97d0f69`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 50 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "AircraftStandContamination"(+95px), "+ abandoned: CodeYesNoType"(+28px), "ApronContamination"(+43px), "+ designator: CodeAirportHeliportDesigna"(+4px)
- [medium] **node_overlap**: 12 overlapping pairs:  x AircraftStand;  x AircraftStandContamination;  x Apron
- [high] **missing_bg_color**: All 17 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 25/25 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 17, Edge count: 25, No content clipping, Edge labels found: 54 (18 edges have label data), 39 links/cross-references detected

### 1 - Seaplanes (id: `5eb137f8-2920-4a6c-874b-7fa934008543`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ designator: CodeBuoyDesignatorType"(+51px)
- [medium] **node_overlap**: 7 overlapping pairs:  x ElevatedPoint;  x MarkingBuoy;  x FloatingDockSite
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 24 (8 edges have label data), 29 links/cross-references detected

### 6 - Runway Blast Pad (id: `4011b6a6-5f99-4d72-ad45-6f477847d2fe`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ approachMarkingCondition: CodeMarkingC"(+50px)
- [medium] **node_overlap**: 4 overlapping pairs:  x ElevatedSurface;  x RunwayDirection;  x SurfaceCharacteristics
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 26 links/cross-references detected

### 5 - Runway Visual Range (id: `990ba84c-05fd-4361-9024-cd592974c1e4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ approachMarkingCondition: CodeMarkingC"(+50px), "+ precisionApproachGuidance: CodeApproac"(+57px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RunwayDirection;  x ElevatedPoint;  x RunwayVisualRange
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 2, No content clipping, Edge labels found: 6 (2 edges have label data), 25 links/cross-references detected

### 4 - Runway Protection (id: `a002ddb3-7aaa-4a0b-bcc4-a78ea0215f64`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ markingLocation: CodeProtectAreaSectio"(+62px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px)
- [medium] **node_overlap**: 5 overlapping pairs:  x RunwayDirection;  x TouchDownLiftOffSafeArea;  x RunwayProtectArea
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 12 (4 edges have label data), 29 links/cross-references detected

### 3 - Runway Operational Point (id: `87e921a4-6a62-488e-a864-c0ad92ebc725`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 32 text elements overflow: "NavaidEquipmentDistance"(+27px), "+ distance: ValDistanceType"(+6px), "+ distanceAccuracy: ValDistanceType"(+56px), "+ designator: CodeNavaidDesignatorType"(+22px), "+ emissionClass: CodeRadioEmissionType"(+22px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Apron;  x Taxiway;  x GuidanceLine
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 12, No content clipping, Edge labels found: 33 (11 edges have label data), 34 links/cross-references detected

### 2 - Runway Direction (id: `52d5f2c7-c5a6-41b7-b2dd-61c0a8a6b769`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 43 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ elevation: ValDistanceVerticalType"(+30px)
- [medium] **node_overlap**: 9 overlapping pairs:  x ElevatedCurve;  x ArrestingGearExtent;  x ArrestingGear
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 14, No content clipping, Edge labels found: 36 (12 edges have label data), 34 links/cross-references detected

### 1 - Runway (id: `0f7201ce-33fc-47c0-a223-1f786c733d87`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ markingLocation: CodeRunwaySectionType"(+48px)
- [medium] **node_overlap**: 5 overlapping pairs:  x SurfaceCharacteristics;  x RunwayElement;  x RunwayDirection
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 13, No content clipping, Edge labels found: 39 (13 edges have label data), 30 links/cross-references detected

### 1 - Surface Marking (id: `6ea171ab-5df5-4a71-a059-562dadbc7e45`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 51 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "+ helicopterClass: CodeHelicopterPerform"(+70px), "AirportHeliportProtectionArea"(+48px), "+ width: ValDistanceType"(+9px), "+ length: ValDistanceType"(+15px)
- [medium] **node_overlap**: 13 overlapping pairs:  x AirportHeliportProtectionArea;  x TaxiHoldingPosition;  x GuidanceLine
- [high] **missing_bg_color**: All 24 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 40/41 edges (98%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 24, Edge count: 41, No content clipping, Edge labels found: 96 (32 edges have label data), 46 links/cross-references detected

### 3 - Pilot Controlled Lighting (id: `86de5ef3-a078-41eb-84a4-80408fff78cb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ intensityLevel: CodeLightIntensityType"(+72px), "+ activation: CodeSystemActivationType"(+60px), "+ classICAO: CodeApproachLightingICAOTyp"(+49px), "+ sequencedFlashing: CodeYesNoType"(+6px), "+ alignmentIndicator: CodeYesNoType"(+12px)
- [medium] **node_overlap**: 4 overlapping pairs:  x LightActivation;  x ApproachLightingSystem;  x GroundLightSystem
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 4, Edge count: 3, No content clipping, Edge labels found: 6 (2 edges have label data), 26 links/cross-references detected

### 2 - Surface Lighting Elements (id: `85016b50-746a-4d58-ad72-2de7e2a67a37`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 29 text elements overflow: "+ type: CodeGuidanceLineType"(+12px), "+ usageDirection: CodeDirectionType"(+56px), "GuidanceLineLightSystem"(+82px), "+ type: CodeRunwayProtectionAreaType"(+47px), "+ status: CodeStatusOperationsType"(+35px)
- [medium] **node_overlap**: 10 overlapping pairs:  x RunwayDirection;  x TouchDownLiftOff;  x Taxiway
- [high] **missing_bg_color**: All 16 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 20/21 edges (95%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 16, Edge count: 21, No content clipping, Edge labels found: 39 (13 edges have label data), 38 links/cross-references detected

### 1 - Surface Lighting (id: `b2b18378-9b4b-4b9b-8e4e-8a3e1b3e59f6`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "PropertiesWithSchedule"(+47px), "+ operationalStatus: CodeStatusOperation"(+68px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x PropertiesWithSchedule;  x GroundLightingAvailability;  x ElevatedPoint
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 4, No content clipping, Edge labels found: 9 (3 edges have label data), 27 links/cross-references detected

### 2 - TLOF Protection Area (id: `16605aa7-2951-4647-aa79-a9862608cb61`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ composition: CodeSurfaceCompositionTyp"(+23px), "+ preparation: CodeSurfacePreparationTyp"(+23px), "+ surfaceCondition: CodeSurfaceCondition"(+42px), "+ pavementTypePCN: CodePCNPavementType"(+5px), "+ pavementSubgradePCN: CodePCNSubgradeTy"(+30px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SurfaceCharacteristics;  x TouchDownLiftOff;  x RunwayProtectArea
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/8 edges (88%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 8, No content clipping, Edge labels found: 18 (6 edges have label data), 29 links/cross-references detected

### 1 - TLOF (id: `10f68f2c-ed06-42e3-8d79-158450ecc350`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 36 text elements overflow: "TouchDownLiftOffLightSystem"(+67px), "+ position: CodeTLOFSectionType"(+43px), "+ markingLocation: CodeTLOFSectionType"(+46px), "ManoeuvringAreaAvailability"(+15px), "+ operationalStatus: CodeStatusAirportTy"(+69px)
- [medium] **node_overlap**: 6 overlapping pairs:  x SurfaceCharacteristics;  x ElevatedSurface;  x ElevatedPoint
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 13/13 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 13, No content clipping, Edge labels found: 39 (13 edges have label data), 32 links/cross-references detected

### 4 - Passenger Loading Bridge (id: `a9f2236f-b0fe-4cb2-8ea3-aca48b24e4de`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ visualDockingSystem: CodeVisualDocking"(+64px)
- [medium] **node_overlap**: 3 overlapping pairs:  x ElevatedSurface;  x AircraftStand;  x PassengerLoadingBridge
- [high] **missing_bg_color**: All 3 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 3, No content clipping, Edge labels found: 9 (3 edges have label data), 25 links/cross-references detected

### 3 - Roads (id: `2266ce66-a005-4383-ac49-d30377d1246d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px), "+ verticalAccuracy: ValDistanceType"(+24px), "+ composition: CodeSurfaceCompositionTyp"(+23px)
- [medium] **node_overlap**: 3 overlapping pairs:  x AircraftStand;  x AirportHeliport;  x Road
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 5, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 27 links/cross-references detected

### 2 - Aircraft Stands (id: `3438ccf1-6a3a-428e-ae65-7f75b6ddfffb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 16 text elements overflow: "+ composition: CodeSurfaceCompositionTyp"(+23px), "+ preparation: CodeSurfacePreparationTyp"(+23px), "+ surfaceCondition: CodeSurfaceCondition"(+42px), "+ pavementTypePCN: CodePCNPavementType"(+5px), "+ pavementSubgradePCN: CodePCNSubgradeTy"(+30px)
- [medium] **node_overlap**: 5 overlapping pairs:  x StandMarking;  x SurfaceCharacteristics;  x ApronElement
- [high] **missing_bg_color**: All 6 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 4/7 edges (57%) have no waypoints

**Correct:** Node count: 6, Edge count: 7, No content clipping, Edge labels found: 21 (7 edges have label data), 28 links/cross-references detected

### 1 - Apron (id: `27f5059e-e89b-47bc-bfef-38b4eba884a0`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ markingLocation: CodeApronSectionType"(+51px), "+ position: CodeApronSectionType"(+48px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ElevatedSurface;  x AirportSuppliesService;  x ApronElement
- [high] **missing_bg_color**: All 9 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 10/12 edges (83%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 9, Edge count: 12, No content clipping, Edge labels found: 36 (12 edges have label data), 31 links/cross-references detected

### 5 - Apron Area Availability (id: `9ab03308-4d96-4231-86a7-a2382f2231ee`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "+ visualDockingSystem: CodeVisualDocking"(+64px), "PropertiesWithSchedule"(+47px), "+ type: CodeUsageLimitationType"(+40px), "+ priorPermission: ValDurationType"(+59px), "ApronAreaUsage"(+15px)
- [medium] **node_overlap**: 7 overlapping pairs:  x AircraftStand;  x UsageCondition;  x ApronAreaUsage
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 11, No content clipping, Edge labels found: 27 (9 edges have label data), 30 links/cross-references detected

### 4 - Manoeuvering Area Availability (id: `a95c17bd-9c67-44fd-9077-21e2c55ddbac`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "+ helicopterClass: CodeHelicopterPerform"(+70px), "PropertiesWithSchedule"(+47px), "+ type: CodeUsageLimitationType"(+40px), "+ priorPermission: ValDurationType"(+59px), "+ operation: CodeOperationManoeuvringAre"(+55px)
- [medium] **node_overlap**: 7 overlapping pairs:  x TouchDownLiftOff;  x TaxiwayElement;  x SeaplaneLandingArea
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/11 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 11, No content clipping, Edge labels found: 27 (9 edges have label data), 32 links/cross-references detected

### 3 - AirportHeliport Availability (id: `525e28ac-fa8b-4d6b-87ef-eb7d51b6ce11`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "+ status: CodeFlightStatusType"(+25px), "+ military: CodeMilitaryStatusType"(+50px), "+ origin: CodeFlightOriginType"(+25px), "+ purpose: CodeFlightPurposeType"(+37px), "+ navigationSpecification: CodeNavigatio"(+18px)
- [medium] **node_overlap**: 6 overlapping pairs:  x Meteorology;  x ContactInformation;  x AirportHeliportUsage
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 11/12 edges (92%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 12, No content clipping, Edge labels found: 24 (9 edges have label data), 32 links/cross-references detected

### 2 - AirportHeliport Association (id: `0f1201ec-6d62-4c05-876f-3a9ed0cd747a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 39 text elements overflow: "+ abandoned: CodeYesNoType"(+28px), "+ designator: TextDesignatorType"(+27px), "+ nominalLength: ValDistanceType"(+27px), "+ lengthAccuracy: ValDistanceType"(+33px), "+ nominalWidth: ValDistanceType"(+21px)
- [medium] **node_overlap**: 11 overlapping pairs:  x Taxiway;  x RulesProcedures;  x WorkArea
- [high] **missing_bg_color**: All 15 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 18/21 edges (86%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 15, Edge count: 21, No content clipping, Edge labels found: 60 (20 edges have label data), 37 links/cross-references detected

### 1 - AirportHeliport (id: `220f2309-0bf5-43bd-857f-a836707a8eb7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 27 text elements overflow: "+ designator: TextDesignatorType"(+54px), "+ instruction: TextInstructionType"(+67px), "+ elevation: ValDistanceVerticalType"(+30px), "+ geoidUndulation: ValDistanceSignedType"(+55px), "+ verticalDatum: CodeVerticalDatumType"(+43px)
- [medium] **node_overlap**: 9 overlapping pairs:  x OrganisationAuthority;  x AirportHeliportResponsibilityOrganisation;  x PropertiesWithSchedule
- [high] **missing_bg_color**: All 12 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 15/16 edges (94%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 12, Edge count: 16, No content clipping, Edge labels found: 39 (14 edges have label data), 34 links/cross-references detected

### 2 - Aerial Refuelling Availability (id: `98ddd016-f905-41ac-8558-58510a6b3583`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "PropertiesWithSchedule"(+47px), "+ cardinalDirection: CodeCardinalDirecti"(+75px)
- [medium] **node_overlap**: 4 overlapping pairs:  x AirspaceLayer;  x PropertiesWithSchedule;  x RouteAvailability
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 3/4 edges (75%) have no waypoints

**Correct:** Node count: 4, Edge count: 4, No content clipping, Edge labels found: 6 (3 edges have label data), 25 links/cross-references detected

### 1 - Aerial Refuelling (id: `e47079b6-c69a-40b8-be50-11e8f8be89d7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 23 text elements overflow: "+ upperLimitReference: CodeVerticalRefer"(+68px), "+ lowerLimitReference: CodeVerticalRefer"(+68px), "+ altitudeInterpretation: CodeAltitudeUs"(+50px), "+ reportingATC: CodeATCReportingType"(+44px), "+ radarGuidance: CodeYesNoType"(+7px)
- [medium] **node_overlap**: 9 overlapping pairs:  x AirspaceLayer;  x AerialRefuellingPoint;  x Surface
- [high] **missing_bg_color**: All 11 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 10/13 edges (77%) have no waypoints

**Correct:** Node count: 11, Edge count: 13, No content clipping, Edge labels found: 30 (12 edges have label data), 32 links/cross-references detected

### Basic Types (id: `4417a972-c0e7-4113-8c53-85b1d8506b9a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ nilReason: NilReasonEnumeration"(+48px), "Character2Type"(+7px), "AlphanumericType"(+17px), "anySimpleType"(+3px)
- [medium] **node_overlap**: 11 overlapping pairs:  x XHTMLType;  x unsignedInt;  x decimal
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 5, No content clipping, 31 links/cross-references detected

### Main (id: `b5615c00-9308-4aa1-89dc-123fe58b8529`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ sequenceNumber: NoSequenceType"(+31px), "AIXMFeaturePropertyGroup"(+33px), "+ featureLifetime: TimePrimitive"(+59px), "+ interpretation: TimeSliceInterpretatio"(+81px), "+ identifier: CodeUUIDType"(+46px)
- [medium] **node_overlap**: 8 overlapping pairs:  x ;  x AIXMMessage;  x MD_Metadata
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 8/8 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 8, Edge count: 8, No content clipping, 28 links/cross-references detected

### AIXM_v.5.1.1 (id: `b64fe16f-4bf3-424e-a853-75f77db76fa3`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "XMLSchemaDatatypes"(+55px), "AIXM Data Types"(+15px), "ISO 19107  Geometry"(+43px), "ISO 19115 Metadata"(+41px), "AIXM Abstract Feature"(+57px)
- [medium] **node_overlap**: 11 overlapping pairs:  x ;  x ;  x XMLSchemaDatatypes
- [medium] **missing_packages**: API has 7 package nodes, DOM has 0
- [high] **missing_bg_color**: All 10 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 10, Edge count: 6, No content clipping, 28 links/cross-references detected


---

## FIXM

### NasRoute (id: `735576af-6fec-4a30-b516-2e5cc5520716`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 34 text elements overflow: "UnknownRouteElement"(+62px), "StarsFlightRules"(+13px), "+ estimatedElapsedTime: Duration"(+12px), "+ predictedWaypoint: SignificantPoint"(+43px), "+ estimatedElapsedEntryTime: Duration"(+32px)
- [medium] **node_overlap**: 15 overlapping pairs:  x UnknownRouteElement;  x StarsFlightRules;  x InhibitAdaptedDepRoutesIndicator
- [medium] **missing_bg_color**: 18/19 nodes lack bgColor in API data
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 18/18 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 19, Edge count: 18, No content clipping, Edge labels found: 17 (17 edges have label data), 38 links/cross-references detected

### NasFlightData (id: `4485de51-ef3e-46c9-b7b6-6febd93a0b4a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "DiversionRecoveryIndicator"(+88px), "+ DIVERSION_RECOVERY:"(+19px), "NasFlightStatus"(+10px), "+ stddsSpotOut: Time"(+3px), "+ stddsWheelsOff: Time"(+16px)
- [medium] **node_overlap**: 18 overlapping pairs:  x DiversionRecoveryIndicator;  x RnavIndicator;  x NasFlightStatus
- [medium] **missing_bg_color**: 24/25 nodes lack bgColor in API data
- [high] **missing_waypoints**: 26/26 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 22/26 edges (85%) lack visual styling (lineColor)

**Correct:** Node count: 25, Edge count: 26, No content clipping, Edge labels found: 26 (26 edges have label data), 44 links/cross-references detected

### NasAltitude (id: `44872a17-948b-4310-8948-9978ab731f40`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "InvalidIndicator"(+8px), "ReportedAltitude"(+19px), "+ above: FlightLevelOrAltitude"(+32px), "+ below: FlightLevelOrAltitude"(+32px), "+ point: SignificantPoint"(+10px)
- [medium] **node_overlap**: 15 overlapping pairs:  x InvalidIndicator;  x TargetAltitude;  x AltitudeSuffix
- [medium] **missing_bg_color**: 13/14 nodes lack bgColor in API data
- [high] **missing_waypoints**: 10/10 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 10/10 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 14, Edge count: 10, No content clipping, Edge labels found: 10 (10 edges have label data), 33 links/cross-references detected

### NasAircraft (id: `abb8bbd9-ef3d-4381-8f3b-8b13b0d3417c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "TfmsAircraftCategory"(+38px), "+ SINGLE_PISTON_PROP:"(+13px), "+ MULTI_PISTON_PROP:"(+7px), "+ SINGLE_TURBO_PROP:"(+7px), "+ MILITARY_FIGHTER_JET:"(+26px)
- [medium] **node_overlap**: 13 overlapping pairs:  x RnavIndicator;  x EngineType;  x TfmsAircraftCategory
- [high] **missing_waypoints**: 10/10 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 10/10 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 13, Edge count: 10, No content clipping, Edge labels found: 10 (10 edges have label data), 32 links/cross-references detected

### NasTrajectoryOptions (id: `459eb132-8d37-4046-8cf1-b25268dcd4a4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 39 text elements overflow: "AssignedIndicator"(+25px), "+ ASSIGNED: string"(+7px), "+ amendmentRejectReason: CharacterString"(+29px), "RouteAmendmentStatus"(+71px), "CollaborativeTrajectoryOptionsProgram"(+107px)
- [medium] **node_overlap**: 23 overlapping pairs:  x AssignedIndicator;  x CtopRouteAmendment;  x CollaborativeTrajectoryOptionsProgram
- [medium] **missing_bg_color**: 23/24 nodes lack bgColor in API data
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 18/18 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 24, Edge count: 18, No content clipping, Edge labels found: 18 (18 edges have label data), 44 links/cross-references detected

### NasTmiData (id: `f90b29e7-b976-4413-9102-7ea17dae1426`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 19 text elements overflow: "AmendmentType"(+15px), "AmendmentStatus"(+28px), "CollaborativeTrajectoryOptionsProgram"(+107px), "+ additionalAirborneTime: Duration"(+34px), "+ assignedGroundDelay: Duration"(+15px)
- [medium] **node_overlap**: 18 overlapping pairs:  x AmendmentType;  x AmendmentStatus;  x CollaborativeTrajectoryOptionsProgram
- [medium] **missing_bg_color**: 19/21 nodes lack bgColor in API data
- [high] **missing_waypoints**: 19/19 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 19/19 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 21, Edge count: 19, No content clipping, Edge labels found: 19 (19 edges have label data), 41 links/cross-references detected

### NasTmiCompliance (id: `3bd4f7d1-6112-4af3-b1cf-5d1d6d8cf0fc`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "SpuriousFlightIndicator"(+64px), "+ SPURIOUS_FLIGHT:"(+7px), "CanceledButFlewIndicator"(+49px), "TmiComplianceIndicator"(+69px), "TmiCompliance"(+4px)
- [medium] **node_overlap**: 4 overlapping pairs:  x SpuriousFlightIndicator;  x CanceledButFlewIndicator;  x TmiComplianceIndicator
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 5/5 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 4, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 24 links/cross-references detected

### NasTfdm (id: `1de68f6c-bfa8-4fda-b1f1-0e2f584198b4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ InboundMovementAreaHoldTimeDuration: D"(+30px), "+ inboundMovementAreaTaxiTimeDuration: D"(+30px), "+ outboundMovementAreaHoldTimeDuration: "(+11px), "+ outboundMovementAreaQueuingTimeDuratio"(+30px), "+ outboundMovementAreaTaxiTimeDuration: "(+11px)
- [medium] **node_overlap**: 5 overlapping pairs:  x ArrivalTaxiOperationsMetrics;  x DepartureTaxiOperationsMetrics;  x TfdmArrival
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 2/2 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 5, Edge count: 2, No content clipping, Edge labels found: 2 (2 edges have label data), 24 links/cross-references detected

### NasStatus (id: `c807f5aa-3688-4476-af11-937899ecb4cb`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ CLEARED_FOR_TAKEOFF:"(+16px), "AircraftMovementStateValue"(+68px), "StarsFlightStatus"(+21px), "AirborneHoldIndicator"(+29px), "+ AIRBORNE_HOLD: string"(+12px)
- [medium] **node_overlap**: 11 overlapping pairs:  x TfdmAtcFlightState;  x TfdmFlightState;  x AtcStateValue
- [medium] **missing_bg_color**: 10/11 nodes lack bgColor in API data
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 11, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 30 links/cross-references detected

### NasPosition (id: `b4f9fd18-ce87-4e00-ab15-f588c71f2d8d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "NasAcceleration"(+11px), "+ positionAltitude: FlightLevelOrAltitud"(+55px), "+ reportedLevel: ReportedAltitude"(+16px), "+ targetAltitude: TargetAltitude"(+10px), "+ targetPosition: GeographicalPosition"(+48px)
- [medium] **node_overlap**: 6 overlapping pairs:  x NasAcceleration;  x PlannedReportingPosition;  x NasAircraftPosition
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 5/5 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 6, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 25 links/cross-references detected

### NasMessage (id: `d8d27a62-52b7-4cb9-a9b4-268b5d0db219`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ additionalFlightInformation: NameValue"(+48px), "+ finalControllingUnit: AtcUnitReference"(+23px), "+ navigationIntegrityCategory: Count"(+26px), "+ positionNavigationAccuracyCategory: Co"(+70px), "+ triggerType: CharacterString"(+35px)
- [medium] **node_overlap**: 7 overlapping pairs:  x NasFlight;  x AsdexConfidence;  x MessageProvenance
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 7, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 26 links/cross-references detected

### NasMeasures (id: `a47b46d9-e13a-42f3-9d53-43ff9488694c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "NasIndicatedAirspeed"(+52px), "+ uom: UomAirspeed"(+7px), "VeriticalRateSource"(+37px), "NasVerticalRate"(+10px), "UomAcceleration"(+17px)
- [medium] **node_overlap**: 5 overlapping pairs:  x NasIndicatedAirspeed;  x VeriticalRateSource;  x NasVerticalRate
- [high] **missing_bg_color**: All 5 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 1/1 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 5, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 24 links/cross-references detected

### NasFlightPlan (id: `6d95c1f7-eb66-4628-9f79-cfb81f7ed70c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "StarsFlightPlanSuspendedIndicator"(+107px), "StarsFlightPlanDeletedIndicator"(+108px), "StarsFlightPlanStatus"(+52px), "+ flightPlanRemarks: CharacterString"(+41px)
- [medium] **node_overlap**: 5 overlapping pairs:  x StarsFlightPlanSuspendedIndicator;  x StarsFlightPlanDeletedIndicator;  x StarsFlightPlanStatus
- [medium] **missing_bg_color**: 4/5 nodes lack bgColor in API data
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 3/3 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 5, Edge count: 3, No content clipping, Edge labels found: 3 (3 edges have label data), 24 links/cross-references detected

### NasFlightIntent (id: `4e549833-c69b-4d88-b251-3bfe3749f1c8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "MovementAreaHoldInformation"(+67px), "+ estimatedEntryTime: Time"(+3px)
- [medium] **node_overlap**: 3 overlapping pairs:  x COPYRIGHT;  x HoldIntent;  x MovementAreaHoldInformation
- [medium] **missing_bg_color**: 2/3 nodes lack bgColor in API data
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected

### NasEnRouteData (id: `49efe5e8-fec1-48bf-b4c2-4c887d601613`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "NasBoundaryCrossing"(+53px), "+ reportedLevel: ReportedAltitude"(+13px), "+ targetAltitude: TargetAltitude"(+7px), "+ targetPosition: GeographicalPosition"(+45px), "+ arrivalAerodrome: AerodromeReference"(+31px)
- [medium] **node_overlap**: 15 overlapping pairs:  x NasBoundaryCrossing;  x NasAircraftPosition;  x ControlElement
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 11/12 edges (92%) lack visual styling (lineColor)

**Correct:** Node count: 14, Edge count: 12, No content clipping, Edge labels found: 12 (12 edges have label data), 33 links/cross-references detected, All nodes have bgColor

### NasDeparture (id: `a555bd8a-3c57-4c7a-a107-5838ca4157d3`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 24 text elements overflow: "DepartureDelayReason"(+61px), "+ facilityToCharge: CharacterString"(+42px), "+ tmiIdentifier: CharacterString"(+23px), "TmatMarkedForSubsitutionIndicator"(+61px), "TmatRelinquishIndicator"(+71px)
- [medium] **node_overlap**: 17 overlapping pairs:  x DepartureDelayReason;  x DepartureDelay;  x TmatMarkedForSubsitutionIndicator
- [medium] **missing_bg_color**: 18/19 nodes lack bgColor in API data
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 15/18 edges (83%) lack visual styling (lineColor)

**Correct:** Node count: 19, Edge count: 18, No content clipping, Edge labels found: 18 (18 edges have label data), 38 links/cross-references detected

### NasCoordination (id: `98e1df77-885b-454d-9c74-9594b7dcb306`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "NasBoundaryCrossing"(+53px), "+ acceptingUnit: AtcUnitReference"(+24px), "+ receivingUnit: AtcUnitReference"(+24px), "+ transferringUnit: AtcUnitReference"(+43px), "NasHandoffEvent"(+19px)
- [medium] **node_overlap**: 4 overlapping pairs:  x NasBoundaryCrossing;  x COPYRIGHT;  x NasHandoff
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 2/2 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 4, Edge count: 2, No content clipping, Edge labels found: 2 (2 edges have label data), 23 links/cross-references detected

### NasCommon (id: `2ccd8677-dc8c-4586-9655-54b3665469ab`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 10 text elements overflow: "NasStandInformation"(+26px), "+ standName: TextName"(+3px), "RunwayClassificationType"(+80px), "+ reportedTimestamp: Time"(+13px), "RunwayUnassignedIndicator"(+91px)
- [medium] **node_overlap**: 13 overlapping pairs:  x NasStandInformation;  x RunwayClassificationType;  x NasRunwayInformation
- [medium] **missing_bg_color**: 7/13 nodes lack bgColor in API data
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 6/6 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 13, Edge count: 6, No content clipping, Edge labels found: 3 (3 edges have label data), 32 links/cross-references detected

### NasArrival (id: `c092bed3-0bbb-47d5-909a-f5e57173be6b`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 21 text elements overflow: "MovementAreaHoldInformation"(+81px), "+ estimatedEntryTime: Time"(+17px), "+ estimatedExitTime: Time"(+10px), "RunwayUnassignedIndicator"(+91px), "+ RUNWAY_UNASSIGNED:"(+11px)
- [medium] **node_overlap**: 16 overlapping pairs:  x HoldIntent;  x MovementAreaHoldInformation;  x RunwayUnassignedIndicator
- [medium] **missing_bg_color**: 13/16 nodes lack bgColor in API data
- [high] **missing_waypoints**: 14/14 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 13/14 edges (93%) lack visual styling (lineColor)

**Correct:** Node count: 16, Edge count: 14, No content clipping, Edge labels found: 14 (14 edges have label data), 35 links/cross-references detected

### NasAirspace (id: `daf9abed-f2d3-4cee-bb57-64a6ecfa0950`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 3 text elements overflow: "TfmsRouteType"(+5px), "+ CODED_ROUTE: string"(+25px), "TfmsInstrumentRouteDesignator"(+97px)
- [medium] **node_overlap**: 3 overlapping pairs:  x COPYRIGHT;  x TfmsRouteType;  x TfmsInstrumentRouteDesignator
- [medium] **missing_bg_color**: 2/3 nodes lack bgColor in API data
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 1/1 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected

### Capability (id: `a131e792-3ae0-433d-bfb2-30b1c957793d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 22 text elements overflow: "+ colour: ColourChoice"(+12px), "+ totalCapacity: Count"(+12px), "DinghyCoverIndicator"(+51px), "SurvivalEquipmentType"(+54px), "+ otherSurveillanceCapabilities: Charact"(+66px)
- [medium] **node_overlap**: 15 overlapping pairs:  x Dinghies;  x DinghyCoverIndicator;  x SurvivalEquipmentType
- [medium] **missing_bg_color**: 17/18 nodes lack bgColor in API data
- [high] **missing_waypoints**: 16/16 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 18, Edge count: 16, No content clipping, Edge labels found: 16 (16 edges have label data), 37 links/cross-references detected

### DangerousGoods (id: `8a25e813-f6bd-4f86-b65a-7fa170885f97`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "AdditionalHandlingInformation"(+10px), "+ responsibleAgent: PersonOrOrganization"(+36px), "+ airWaybillNumber: CharacterString"(+36px), "+ dangerousGoodsScreeningLocation: Chara"(+49px), "+ subsidiaryHazardClassAndDivision: Char"(+55px)
- [medium] **node_overlap**: 10 overlapping pairs:  x AdditionalHandlingInformation;  x AirWaybill;  x ShippingInformation
- [medium] **missing_bg_color**: 8/10 nodes lack bgColor in API data
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 10, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 30 links/cross-references detected

### Messaging (id: `f04fdfe0-ee20-4227-a41c-98b4ecf983e5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "SubmissionStatusValue"(+64px), "FlightPlanVersionTypeChoice"(+92px), "+ statusReason: CharacterString"(+19px), "+ statusReason: CharacterString"(+31px), "+ recipientDeliveryResponsibility: Perso"(+8px)
- [medium] **node_overlap**: 14 overlapping pairs:  x MessageCollection;  x FlightPlanVersionTypeChoice;  x FlightPlanNegotiationStatus
- [medium] **missing_bg_color**: 15/17 nodes lack bgColor in API data
- [high] **missing_waypoints**: 18/18 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 18/18 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 17, Edge count: 18, No content clipping, Edge labels found: 16 (16 edges have label data), 36 links/cross-references detected

### Time (id: `42bb538f-be08-41fc-9b3f-d48f92588d0e`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 19 links/cross-references detected

### RouteChanges (id: `b6814e8c-d947-4781-8c5a-c225c3d65914`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 3 text elements overflow: "AbstractRouteChange"(+24px), "+ PLAN_TO_COMMENCE:"(+11px), "AtOrAboveAltitudeIndicator"(+42px)
- [medium] **node_overlap**: 7 overlapping pairs:  x COPYRIGHT;  x SpeedChange;  x CruiseClimbStart
- [high] **missing_waypoints**: 6/6 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 6/6 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 7, Edge count: 6, No content clipping, Edge labels found: 3 (3 edges have label data), 27 links/cross-references detected, All nodes have bgColor

### Constraints (id: `c536cf3e-910e-4774-ae6e-2259b6ef6c7d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "+ speed: TrueAirspeedChoice"(+8px), "+ constraintReference: CharacterString"(+46px), "+ temporalSpecification: TemporalChoice"(+35px), "+ PLAN_TO_COMMENCE:"(+11px), "SpeedCondition"(+8px)
- [medium] **node_overlap**: 10 overlapping pairs:  x LevelCondition;  x LevelConstraint;  x SpeedConstraint
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 10, Edge count: 9, No content clipping, Edge labels found: 6 (6 edges have label data), 30 links/cross-references detected, All nodes have bgColor

### Measures (id: `9ee2f723-6913-456d-9ff2-59ca037bbf59`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 14 text elements overflow: "+ uom: UomAirspeed"(+7px), "+ uom: UomFlightLevel"(+25px), "VerticalReference"(+22px), "VerticalDistance"(+4px), "+ uom: UomWindSpeed"(+13px)
- [medium] **node_overlap**: 19 overlapping pairs:  x TrueAirspeed;  x FlightLevel;  x Volume
- [medium] **missing_bg_color**: 19/26 nodes lack bgColor in API data
- [high] **missing_waypoints**: 23/23 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 23/23 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 26, Edge count: 23, No content clipping, Edge labels found: 2 (2 edges have label data), 45 links/cross-references detected

### Extension (id: `e9c37bb8-61d5-4a5a-9c32-9cd23b5814d2`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 2 overlapping pairs:  x COPYRIGHT;  x Extension

**Correct:** Node count: 2, Edge count: 0, No content clipping, 21 links/cross-references detected

### Airspace (id: `fdcdb899-d06d-4105-8e64-5e88a1953986`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "+ position: GeographicalPosition"(+37px), "AirspaceDesignator"(+36px), "RouteDesignator"(+16px), "SidStarDesignator"(+26px), "SignificantPointDesignator"(+88px)
- [medium] **node_overlap**: 14 overlapping pairs:  x PositionPoint;  x AirspaceDesignator;  x GeographicalPosition
- [medium] **missing_bg_color**: 10/11 nodes lack bgColor in API data
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 3/3 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 11, Edge count: 3, No content clipping, 30 links/cross-references detected

### Packaging (id: `84d348dc-83ec-4006-bd47-bde5edd27bb1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 15 text elements overflow: "AircraftDangerousGoodsLimitation"(+67px), "+ PASSENGER_AND_CARGO_AIRCRAFT: string"(+54px), "MarinePollutantIndicator"(+53px), "+ MARINE_POLLUTANT: string"(+35px), "DangerousGoodsDimensions"(+66px)
- [medium] **node_overlap**: 10 overlapping pairs:  x AircraftDangerousGoodsLimitation;  x MarinePollutantIndicator;  x AllPackedInOne
- [medium] **missing_bg_color**: 14/15 nodes lack bgColor in API data
- [high] **missing_waypoints**: 15/15 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 14/15 edges (93%) lack visual styling (lineColor)

**Correct:** Node count: 15, Edge count: 15, No content clipping, Edge labels found: 15 (15 edges have label data), 35 links/cross-references detected

### UnitsOfMeasure (id: `d741f324-2292-4953-b16d-a30214ee11bd`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **node_overlap**: 16 overlapping pairs:  x UomVolume;  x UomWeight;  x UomTemperature
- [medium] **missing_bg_color**: 14/16 nodes lack bgColor in API data

**Correct:** Node count: 16, Edge count: 0, No content clipping, 36 links/cross-references detected

### Organization (id: `a5f01db2-43f7-4ba1-b0da-37ba70b66cd8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "LocationIndicator"(+20px), "AircraftOperatorDesignator"(+93px), "+ designatorIcao: AircraftOperatorDesign"(+39px), "+ operatingOrganization: PersonOrOrganiz"(+46px), "+ locationIndicator: LocationIndicator"(+21px)
- [medium] **node_overlap**: 12 overlapping pairs:  x LocationIndicator;  x AircraftOperatorDesignator;  x COPYRIGHT
- [medium] **missing_bg_color**: 9/11 nodes lack bgColor in API data
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 4/4 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 11, Edge count: 4, No content clipping, Edge labels found: 2 (2 edges have label data), 30 links/cross-references detected

### Aerodrome (id: `fbc762fd-0e05-4b3c-be87-f54861746ac1`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 5 text elements overflow: "+ locationIndicator: LocationIndicator"(+11px), "IataAerodromeDesignator"(+81px), "RunwayDirectionDesignator"(+85px), "AerodromeName"(+15px), "+ iataDesignator: IataAerodromeDesignato"(+30px)
- [medium] **node_overlap**: 8 overlapping pairs:  x IcaoAerodromeReference;  x AerodromeReference;  x IataAerodromeDesignator
- [medium] **missing_bg_color**: 6/7 nodes lack bgColor in API data
- [high] **missing_waypoints**: 2/2 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 2/2 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 7, Edge count: 2, No content clipping, 26 links/cross-references detected

### FlightData (id: `d8b57ce5-5b45-4103-b6b8-d3cd2f6d8daf`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 28 text elements overflow: "+ guidebookNumber: CharacterString"(+47px), "+ onboardLocation: CharacterString"(+47px), "+ pilotInCommand: PersonOrOrganization"(+7px), "+ flightPlanOriginator: PersonOrOrganiza"(+48px), "+ flightPlanSubmitter: PersonOrOrganizat"(+42px)
- [medium] **node_overlap**: 8 overlapping pairs:  x DangerousGoods;  x Departure;  x COPYRIGHT
- [high] **missing_waypoints**: 19/19 edges (100%) have no waypoints — straight-line routing instead of orthogonal

**Correct:** Node count: 16, Edge count: 19, No content clipping, Edge labels found: 19 (19 edges have label data), 35 links/cross-references detected, All nodes have bgColor

### RouteTrajectory (id: `57c4ea6b-c624-4946-9980-583917b6ed5a`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 31 text elements overflow: "+ level: FlightLevelOrAltitude"(+25px), "+ relativeTimeFromInitialPredictionPoint"(+33px), "+ AU_REQUEST_AERODROME:"(+8px), "AbstractRouteChange"(+34px), "TrajectoryPointReference"(+42px)
- [medium] **node_overlap**: 15 overlapping pairs:  x EnRouteDelayType;  x AbstractRouteChange;  x COPYRIGHT
- [high] **missing_waypoints**: 24/24 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 24/24 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 24, Edge count: 24, No content clipping, Edge labels found: 24 (24 edges have label data), 44 links/cross-references detected, All nodes have bgColor

### Departure (id: `36a53adf-1d44-4972-a7d8-b1fa5344e40d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "+ runwayDirection: RunwayDirectionDesign"(+12px), "+ takeoffAlternateAerodrome: AerodromeRe"(+31px)
- [medium] **node_overlap**: 2 overlapping pairs:  x COPYRIGHT;  x Departure

**Correct:** Node count: 2, Edge count: 0, No content clipping, 21 links/cross-references detected, All nodes have bgColor

### Emergency (id: `e907acc0-bf9b-41c6-ae57-52d6ae487ef4`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 9 text elements overflow: "+ radioFailureRemarks: CharacterString"(+21px), "+ remainingComCapability: CharacterStrin"(+39px), "EmergencyPhase"(+17px), "+ DETRESFA: string"(+7px), "+ lastContactFrequency: Frequency"(+22px)
- [medium] **node_overlap**: 6 overlapping pairs:  x RadioCommunicationFailure;  x EmergencyPhase;  x LastContact
- [high] **missing_waypoints**: 4/4 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 4/4 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 6, Edge count: 4, No content clipping, Edge labels found: 4 (4 edges have label data), 25 links/cross-references detected

### Types (id: `e5c3940d-6f3f-4777-9b28-a36fe21618d5`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "AircraftIdentification"(+45px), "CharacterString"(+9px), "AircraftTypeDesignator"(+62px), "GloballyUniqueFlightIdentifier"(+35px)
- [medium] **node_overlap**: 15 overlapping pairs:  x TextName;  x Time;  x Duration
- [medium] **missing_bg_color**: 11/13 nodes lack bgColor in API data
- [high] **missing_waypoints**: 7/7 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 7/7 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 13, Edge count: 7, No content clipping, Edge labels found: 1 (1 edges have label data), 32 links/cross-references detected

### Address (id: `82c35788-dd99-4b73-ad73-f38cd2b2c4ed`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "TextCountryName"(+23px), "TelephoneContact"(+9px), "TelecomNetworkType"(+47px), "TextCountryCode"(+17px)
- [medium] **node_overlap**: 11 overlapping pairs:  x TextCountryName;  x TelephoneContact;  x OnlineContact
- [medium] **missing_bg_color**: 10/11 nodes lack bgColor in API data
- [high] **missing_waypoints**: 12/12 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 12/12 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 11, Edge count: 12, No content clipping, Edge labels found: 12 (12 edges have label data), 30 links/cross-references detected

### RankedTrajectory (id: `bf0e1a13-0b4d-4af5-88e0-109057ce4f36`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 1 text elements overflow: "+ takeoffWeight: Weight"(+21px)
- [medium] **node_overlap**: 3 overlapping pairs:  x RankedTrajectory;  x COPYRIGHT;  x RouteTrajectory
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 1/1 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 3, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 22 links/cross-references detected, All nodes have bgColor

### Aircraft (id: `a8b73fcc-b42f-40ff-aa5c-c3cc5b5a6fc3`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 11 text elements overflow: "AircraftRegistration"(+38px), "OtherAircraftTypeReference"(+22px), "+ otherAircraftType: CharacterString"(+45px), "AircraftAddress"(+7px), "AircraftTypeReference"(+35px)
- [medium] **node_overlap**: 11 overlapping pairs:  x AircraftRegistration;  x OtherAircraftTypeReference;  x AircraftAddress
- [medium] **missing_bg_color**: 9/11 nodes lack bgColor in API data
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 11, Edge count: 9, No content clipping, Edge labels found: 7 (7 edges have label data), 30 links/cross-references detected

### EnRoute (id: `56315442-adce-4771-8f6c-94271c7d819c`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 6 text elements overflow: "BoundaryCrossingCondition"(+91px), "+ AT_OR_ABOVE: string"(+21px), "+ AT_OR_BELOW: string"(+21px), "AltitudeInTransition"(+38px), "+ alternateAerodrome: AerodromeReference"(+30px)
- [medium] **node_overlap**: 5 overlapping pairs:  x BoundaryCrossingCondition;  x AltitudeInTransition;  x EnRoute
- [high] **missing_waypoints**: 3/3 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 3/3 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 5, Edge count: 3, No content clipping, Edge labels found: 3 (3 edges have label data), 24 links/cross-references detected, All nodes have bgColor

### Arrival (id: `fed1511a-cd37-403d-a11c-5c9f79e33275`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "+ runwayDirection: RunwayDirectionDesign"(+45px), "+ filedRevisedDestinationAerodrome: Aero"(+49px), "+ aerodromeAlternate: AerodromeReference"(+12px), "+ runwayDirection: RunwayDirectionDesign"(+37px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Arrival;  x COPYRIGHT;  x ReclearanceInFlight
- [high] **missing_waypoints**: 1/1 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 1/1 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 4, Edge count: 1, No content clipping, Edge labels found: 1 (1 edges have label data), 23 links/cross-references detected, All nodes have bgColor

### RadioactiveMaterials (id: `78754a29-8fb2-4347-aa3d-301ac4ebfb46`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "FissileExcepted"(+6px), "+ EXCEPTED: string"(+7px), "RadioactiveMaterialCategory"(+72px), "+ criticalitySafetyIndex: DecimalIndex"(+31px), "+ SPECIAL_FORM: string"(+32px)
- [medium] **node_overlap**: 7 overlapping pairs:  x FissileExcepted;  x RadioactiveMaterialCategory;  x RadioactiveMaterial
- [medium] **missing_bg_color**: 6/7 nodes lack bgColor in API data
- [high] **missing_waypoints**: 5/5 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 5/5 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 7, Edge count: 5, No content clipping, Edge labels found: 5 (5 edges have label data), 27 links/cross-references detected

### RangesAndChoices (id: `1439f02a-0349-4af7-9495-5af9ca9a47ce`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 13 text elements overflow: "+ lowerSpeed: TrueAirspeed"(+18px), "+ upperSpeed: TrueAirspeed"(+18px), "+ otherColour: CharacterString"(+34px), "+ uom: UomAltitude"(+7px), "TemporalRange"(+6px)
- [medium] **node_overlap**: 14 overlapping pairs:  x TrueAirspeedRange;  x ColourChoice;  x Altitude
- [high] **missing_waypoints**: 9/9 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)

**Correct:** Node count: 14, Edge count: 9, No content clipping, Edge labels found: 9 (9 edges have label data), 33 links/cross-references detected


---

## APM_META

### Prolaborate APM Metamodel (id: `7950df93-f464-4a84-95b3-4075ea6d74c8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 18 text elements overflow: "«ArchiMate_ApplicationComponent»"(+89px), "«ArchiMate_BusinessRole»"(+38px), "«ArchiMate_BusinessActor»"(+43px), "«ArchiMate_BusinessActor»"(+43px), "IT Application Owner"(+45px)
- [medium] **node_overlap**: 30 overlapping pairs:  x Application;  x Stakeholder;  x Organization
- [medium] **missing_bg_color**: 22/27 nodes lack bgColor in API data
- [medium] **missing_waypoints**: 14/23 edges (61%) have no waypoints
- [medium] **missing_edge_visual**: 21/23 edges (91%) lack visual styling (lineColor)
- [medium] **edge_stereotype_hidden**: 3 edges have stereotype but no label — stereotype text not visible (e.g., "ArchiMate_Aggregation")

**Correct:** Node count: 27, Edge count: 23, No content clipping, Edge labels found: 0 (9 edges have label data), 46 links/cross-references detected


---

## APM_ESSENTIAL

### Project (id: `0876b24b-6e29-4244-9f27-2095fb29c3b7`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "BI Driven Marketing"(+38px), "One-Touch Digital Payment5"(+96px), "Digital Touchpoints"(+33px), "ERP Tools Fast Config"(+48px), "Next Gen Marketing"(+38px)
- [medium] **node_overlap**: 7 overlapping pairs:  x BI Driven Marketing;  x One-Touch Digital Payment5;  x Digital Touchpoints
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 7, Edge count: 0, No content clipping, 27 links/cross-references detected

### Application Service (id: `e6a679d1-d993-4daf-9dc7-f3795937f426`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 30 text elements overflow: "«TEA_ApplicationService»"(+33px), "Seek Approvals"(+6px), "«TEA_ApplicationService»"(+33px), "Print & Distribute Invoice"(+78px), "«TEA_ApplicationService»"(+33px)
- [medium] **node_overlap**: 15 overlapping pairs:  x Seek Approvals;  x Print & Distribute Invoice;  x Invoice Creation
- [high] **missing_bg_color**: All 15 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 15, Edge count: 0, No content clipping, 35 links/cross-references detected

### Application Inventory (id: `9c774564-ca6e-41fd-9f54-f776709e5808`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 12 text elements overflow: "HR Management"(+13px), "Oracle Database Management"(+112px), "Spreadsheet Billing"(+35px), "Business Gateway"(+25px), "Amazon Connect"(+14px)
- [medium] **node_overlap**: 26 overlapping pairs:  x HR Management;  x Pension;  x SAP CRM
- [high] **missing_bg_color**: All 26 content nodes lack bgColor in API data (EA defaults not mapped)
- [high] **missing_waypoints**: 62/62 edges (100%) have no waypoints — straight-line routing instead of orthogonal
- [medium] **missing_edge_visual**: 62/62 edges (100%) lack visual styling (lineColor)
- [medium] **edge_stereotype_hidden**: 62 edges have stereotype but no label — stereotype text not visible (e.g., "Integrates")

**Correct:** Node count: 26, Edge count: 62, No content clipping, 46 links/cross-references detected

### Domain (id: `f8d2f23b-2ce9-45a9-a2ea-0f0ab0512b25`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 7 text elements overflow: "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px), "«TEA_ApplicationDomain»"(+34px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Data;  x Security;  x Customer
- [high] **missing_bg_color**: All 7 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 7, Edge count: 0, No content clipping, 27 links/cross-references detected

### IT Application Owner (id: `333d8d3d-f64f-412d-91b4-abe796047cfc`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px), "«TEA_ITApplicationOwner»"(+37px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Philip;  x James;  x John
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected

### Stakeholder (id: `de94f3c7-1cce-436e-ad9f-6cb4c188de3d`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 2 text elements overflow: "Finance Operations"(+34px), "Chief Commercial Officer"(+73px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Finance Operations;  x CEO;  x CIO Office
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected

### Organization (id: `cde2cb34-a660-44a4-aa2b-e9af0a9df718`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 4 text elements overflow: "Customer and Business Services"(+128px), "Strategy & Enterprise Services"(+117px), "Corporate Centre"(+19px), "Group Services"(+3px)
- [medium] **node_overlap**: 4 overlapping pairs:  x Customer and Business Services;  x Strategy & Enterprise Services;  x Corporate Centre
- [high] **missing_bg_color**: All 4 content nodes lack bgColor in API data (EA defaults not mapped)

**Correct:** Node count: 4, Edge count: 0, No content clipping, 24 links/cross-references detected

### MetaModel (id: `116ecbf5-72da-4d22-b3ef-7b76d4bba7a8`)
**Status:** ISSUES_FOUND

**Issues:**
- [medium] **text_overflow**: 8 text elements overflow: "«TEA_ApplicationService»"(+33px), "Application Service"(+33px), "«TEA_ApplicationDomain»"(+34px), "Application Domain"(+35px), "«TEA_ApplicationSubDomain»"(+55px)
- [medium] **node_overlap**: 8 overlapping pairs:  x Project;  x Application Service;  x Application Domain
- [high] **missing_bg_color**: All 8 content nodes lack bgColor in API data (EA defaults not mapped)
- [medium] **missing_waypoints**: 3/9 edges (33%) have no waypoints
- [medium] **missing_edge_visual**: 9/9 edges (100%) lack visual styling (lineColor)
- [medium] **edge_stereotype_hidden**: 9 edges have stereotype but no label — stereotype text not visible (e.g., "Impact")

**Correct:** Node count: 8, Edge count: 9, No content clipping, 26 links/cross-references detected

### Application Landscape (id: `a51c4f4f-6c07-43b8-b3f5-0975841b6b2c`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 18 links/cross-references detected

### Application Portfolio Management (id: `05a0979d-f80b-45c2-8c49-1312a8cb66d7`)
**Status:** PASS

**Correct:** Node count: 0, Edge count: 0, No content clipping, 18 links/cross-references detected

