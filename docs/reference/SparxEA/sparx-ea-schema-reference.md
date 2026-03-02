# Sparx Enterprise Architect Database Schema Reference

## Purpose

This document provides a complete reference for the internal database schema of Sparx Systems Enterprise Architect (EA). It is intended to be used alongside a .qea (SQLite) or .eap (MS Access/JET) model file to build tools that can read, query, and render EA models programmatically without requiring the EA application itself.

## How EA Stores Models

EA models are stored as relational databases. The file format determines the database engine:

| Format | Engine | Notes |
|--------|--------|-------|
| .qea / .qeax | SQLite | Default from EA 16+. Recommended. Works cross-platform. |
| .feap | Firebird | Supported in all editions |
| .eap / .eapx | MS Access (JET) | Legacy. Not supported in 64-bit EA 16. |
| DBMS | MySQL, SQL Server, Oracle, PostgreSQL | For team/enterprise use |

The schema is identical across all backends. A .qea file can be opened directly with any SQLite client or library (Python sqlite3, Node better-sqlite3, etc.).

---

## Complete Table List

### Core Modeling Tables

| Table | Description |
|-------|-------------|
| `t_object` | All model elements (classes, components, use cases, actors, notes, boundaries, etc.) |
| `t_package` | Package hierarchy and containment |
| `t_connector` | All relationships between elements |
| `t_diagram` | Diagram metadata (name, type, owning package) |
| `t_diagramobjects` | Element placement on diagrams (x, y, width, height) |
| `t_diagramlinks` | Connector routing/visibility on specific diagrams |

### Element Feature Tables

| Table | Description |
|-------|-------------|
| `t_attribute` | Attributes defined on elements |
| `t_attributeconstraints` | Constraints on attributes |
| `t_attributetag` | Tagged values on attributes |
| `t_operation` | Operations/methods on elements |
| `t_operationparams` | Parameters for operations |
| `t_operationposts` | Postconditions for operations |
| `t_operationpres` | Preconditions for operations |
| `t_operationtag` | Tagged values on operations |

### Tagged Values and Properties

| Table | Description |
|-------|-------------|
| `t_objectproperties` | **Tagged values for elements.** This is the correct table for tagged values. |
| `t_taggedvalue` | **MISLEADING NAME.** Used for WSDL model elements only. NOT general tagged values. |
| `t_connectortag` | Tagged values on connectors |
| `t_propertytypes` | Predefined tagged value definitions |

### Connector Tables

| Table | Description |
|-------|-------------|
| `t_connectorconstraint` | Constraints on connectors |
| `t_connectortag` | Tagged values on connectors |
| `t_connectortypes` | Connector metatypes (profile dialog). `t_connector.Connector_Type` values come from here. |

### Metadata and Configuration

| Table | Description |
|-------|-------------|
| `t_xref` | Extended properties, stereotype details, and miscellaneous cross-references |
| `t_xrefsystem` | Various profiles |
| `t_stereotypes` | Stereotype definitions |
| `t_genopt` | Various options |
| `t_constants` | Key/value pairs from misc. dialogues |
| `t_lists` | Status types from `Settings/Project Types/General Types` tabs |
| `t_authors` | Project authors |
| `t_clients` | Project clients |
| `t_resources` | Project resources |
| `t_projectroles` | Project roles |
| `usys_system` | Repository-wide key-value settings |
| `usystables` | List of all tables with version introduced |

### Element Constraints and Requirements

| Table | Description |
|-------|-------------|
| `t_objectconstraint` | Constraints on elements |
| `t_objectrequires` | Internal requirements defined on elements |
| `t_objectscenarios` | Use case scenarios |
| `t_objecttests` | Tests defined on elements |
| `t_objectfiles` | Files linked in element properties |

### Project Management Tables

| Table | Description |
|-------|-------------|
| `t_objecteffort` | Project estimation (effort) |
| `t_objectmetrics` | Project estimation (metrics) |
| `t_objectresource` | Project estimation (resources) |
| `t_objectrisks` | Project estimation (risks) |
| `t_objectproblems` | Problems |
| `t_tasks` | System tasks |
| `t_issues` | System issues |
| `t_efforttypes` | Effort type definitions |
| `t_metrictypes` | Metric type definitions |
| `t_risktypes` | Risk type definitions |
| `t_problemtypes` | Problem type definitions |
| `t_testtypes` | Test type definitions |

### Document and Rendering Tables

| Table | Description |
|-------|-------------|
| `t_document` | Contents of linked documents, baselines, and more |
| `t_image` | Alternate pictures from `Settings/Images` |
| `t_html` | HTML strings for doc generation |
| `t_rtf` | Internal doc generation settings |
| `t_rtfreport` | Doc generation settings |
| `t_template` | RTF templates |
| `t_umlpattern` | UML patterns |

### Security Tables

| Table | Description |
|-------|-------------|
| `t_secgroup` | Security groups |
| `t_secgrouppermission` | Security group permissions |
| `t_seclocks` | Security locks |
| `t_secpolicies` | Security settings (check if security is enabled) |
| `t_secuser` | Security users |
| `t_secusergroup` | Security user/group assignments |
| `t_secuserpermission` | Security user permissions |

### Code Generation and Types

| Table | Description |
|-------|-------------|
| `t_datatypes` | Code datatype definitions |
| `t_primitives` | Code primitive types |
| `t_cardinality` | Cardinality value definitions |
| `t_statustypes` | Status type definitions |
| `t_constrainttypes` | Constraint type definitions |
| `t_requiretypes` | Requirement type definitions |
| `t_scenariotypes` | Scenario type definitions |
| `t_diagramtypes` | Diagram type definitions (legacy) |
| `t_objecttypes` | EA internal rendering support |

### Audit and Scripting

| Table | Description |
|-------|-------------|
| `t_snapshot` | Audit log |
| `t_script` | Local scripts |
| `t_trxtypes` | Matrix profiles, painter settings, auto-counters, and more |
| `t_rules` | Model validation rules |

---

## Key Table Schemas (Detailed)

### t_object -- All Model Elements

This is the central table. Every element visible in the Project Browser (and some that are not, like notes and boundaries) is stored here.

#### Primary Identification

| Column | Type | Description |
|--------|------|-------------|
| `Object_ID` | INTEGER | **Primary key.** Unique element identifier. |
| `ea_guid` | TEXT | Global unique identifier (GUID). Use `Repository.GetElementByGUID()` via API. |
| `Object_Type` | TEXT | Element type string. See Object_Type reference below. |
| `NType` | INTEGER | Numeric subtype. Context-sensitive -- meaning depends on Object_Type. |
| `Name` | TEXT | Element name. |
| `Stereotype` | TEXT | Stereotype string. |
| `Alias` | TEXT | Element alias. |

#### Hierarchy and Containment

| Column | Type | Description |
|--------|------|-------------|
| `Package_ID` | INTEGER | FK to `t_package.Package_ID`. The package containing this element. |
| `ParentID` | INTEGER | FK to `t_object.Object_ID`. Only for nested elements (element within element). |
| `Diagram_ID` | INTEGER | Only for Text elements. FK to `t_diagram.Diagram_ID`. |
| `Classifier` | INTEGER | FK to `t_object.Object_ID` of the classifying element. NULL or 0 if not defined. |
| `Classifier_guid` | TEXT | GUID of classifier. Used for ActivityParameter types and ProxyConnector references. |

#### Properties

| Column | Type | Description |
|--------|------|-------------|
| `Notes` | TEXT | Element notes/description. **CAUTION:** EA's SQL Search filters columns named "Note". Use `t_object.Note AS [Notes]` in queries. |
| `Author` | TEXT | Author name. |
| `Status` | TEXT | Status string. Corresponds to values in `t_statustypes`. |
| `Phase` | TEXT | Phase string. |
| `Version` | TEXT | Version string. |
| `Complexity` | TEXT | `1` = Easy, `2` = Medium, `3` = Difficult. |
| `Scope` | TEXT | Scope/visibility string. |
| `GenType` | TEXT | Language property. Must be defined as Product in Language Datatypes. |
| `PDATA5` | TEXT | Keywords property. |

#### Detail Properties

| Column | Type | Description |
|--------|------|-------------|
| `Abstract` | TEXT | Abstract flag. |
| `Cardinality` | TEXT | Cardinality string. |
| `Concurrency` | TEXT | Concurrency property (for class elements). |
| `IsActive` | BOOLEAN | Active flag. |
| `IsLeaf` | BOOLEAN | Leaf flag. |
| `IsSpecification` | BOOLEAN | Specification flag. |
| `IsRoot` | BOOLEAN | Root flag. |
| `Persistence` | TEXT | Persistence string. |

#### Timestamps

| Column | Type | Description |
|--------|------|-------------|
| `CreatedDate` | DATETIME | Creation timestamp. |
| `ModifiedDate` | DATETIME | Last modification timestamp. |

#### Appearance (Element-Level Defaults)

| Column | Type | Description |
|--------|------|-------------|
| `Backcolor` | INTEGER | Background color as decimal RGB. |
| `Bordercolor` | INTEGER | Border color as decimal RGB. |
| `BorderStyle` | INTEGER | Border style (0-3, where 3 = solid line). For frame-like elements. |
| `BorderWidth` | INTEGER | Border width. |
| `Fontcolor` | INTEGER | Font color as decimal RGB. |

#### Multi-Purpose Columns (PDATA)

These columns are overloaded and their meaning depends on `Object_Type`:

| Column | Context | Description |
|--------|---------|-------------|
| `PDATA1` | Package elements | FK to `t_package.Package_ID` |
| `PDATA1` | Plain elements | Same as Status column |
| `PDATA1` | Parts/Instances | GUID of the classifier |
| `PDATA1` | UseCase | Semicolon-separated list of extension points |
| `PDATA1` | Notes | Linked element feature name |
| `PDATA1` | Text (hyperlink) | `t_diagram.Diagram_ID` |
| `PDATA1` | Requirements | Status property |
| `PDATA1` | UMLDiagram | `Diagram_ID` of the underlying diagram |
| `PDATA2` | Plain elements | Same as Priority column |
| `PDATA2` | Notes | `Object_ID` of the linked feature element |
| `PDATA2` | Requirements | Priority property |
| `PDATA3` | State | `Diagram_ID` of the composite diagram |
| `PDATA3` | Ports in classified Parts | GUID of corresponding Port in the Classifier |
| `PDATA3` | Requirements | Difficulty property |
| `PDATA4` | Note elements linked to features | `Yes` plus `idref=<val>;` list where `<val>` is connector ID |
| `PDATA4` | Elements | If > 0, FK to `t_connector.Connector_ID` for association class |

#### Miscellaneous

| Column | Type | Description |
|--------|------|-------------|
| `Style` | TEXT | Semicolon-separated key=value pairs. Contains `Locked=true;`, `MDoc=1;` (linked doc), `ShowBeh`, etc. |
| `StyleEx` | TEXT | Semicolon-separated list. Contains actual font/style information. |
| `GenFile` | TEXT | Filename property. |
| `Multiplicity` | TEXT | Multiplicity string. |
| `RunState` | TEXT | Run state variables for object instances. |
| `Tagged` | INTEGER | Bookmark flag (red triangle in diagram). |
| `TPos` | INTEGER | Tree position order in Project Browser. |
| `EventFlags` | TEXT | Semicolon-separated links into Risk/Metrics tables. |
| `GenOptions` | TEXT | Code generation options (semicolon-separated). |
| `GenLinks` | TEXT | Specialized-from class (for reverse-engineered classes). |
| `Header1` | TEXT | Code generation header. |
| `Header2` | TEXT | Code generation header. |

---

### t_package -- Package Hierarchy

Every package in the model has a row here AND a corresponding element in `t_object`. Some data is redundant between the two.

| Column | Type | Description |
|--------|------|-------------|
| `Package_ID` | INTEGER | **Primary key.** |
| `Name` | TEXT | Package name. |
| `Parent_ID` | INTEGER | FK to `t_package.Package_ID`. The parent package. 0 for root packages. |
| `ea_guid` | TEXT | GUID for this package. |
| `CreatedDate` | DATETIME | Creation timestamp. |
| `ModifiedDate` | DATETIME | Last modification timestamp. |
| `Notes` | TEXT | Package description. |
| `IsControlled` | BOOLEAN | Version control flag. |
| `XMLPath` | TEXT | Version control XMI file path. |
| `IsProtected` | BOOLEAN | Protection flag. |
| `UseDTD` | BOOLEAN | DTD usage flag. |
| `LogXML` | BOOLEAN | XML logging flag. |
| `CodePath` | TEXT | Code generation path. |
| `Namespace` | TEXT | Code generation namespace. |
| `TPos` | INTEGER | Tree position in Browser. |
| `PackageFlags` | TEXT | Semicolon-separated flags. |
| `BatchSave` | INTEGER | Batch save flag. |
| `BatchLoad` | INTEGER | Batch load flag. |
| `Version` | TEXT | Version string. |
| `LastSaveDate` | TEXT | Last save timestamp. |
| `LastLoadDate` | TEXT | Last load timestamp. |

**Critical relationship:** `t_object` has a row with `Object_Type = 'Package'` for each package. The link is:
- `t_object.PDATA1` = `t_package.Package_ID` (for Package-type elements)
- `t_object.Package_ID` = `t_package.Package_ID` (for elements contained in a package)

---

### t_diagram -- Diagram Metadata

| Column | Type | Description |
|--------|------|-------------|
| `Diagram_ID` | INTEGER | **Primary key.** |
| `Package_ID` | INTEGER | FK to `t_package.Package_ID`. Owning package. |
| `ParentID` | INTEGER | FK to `t_object.Object_ID` if diagram is owned by an element (composite diagrams). |
| `Diagram_Type` | TEXT | Diagram type string (e.g., `Logical`, `Use Case`, `Sequence`, `Activity`, `Statechart`, `Component`, `Deployment`, `Custom`, `Object`). |
| `Name` | TEXT | Diagram name. |
| `Version` | TEXT | Version string. |
| `Author` | TEXT | Author name. |
| `ShowDetails` | INTEGER | Detail display level. |
| `Notes` | TEXT | Diagram description. |
| `Stereotype` | TEXT | Diagram stereotype. |
| `AttPub` | BOOLEAN | Show attributes flag. |
| `AttPri` | BOOLEAN | Show private attributes. |
| `AttPro` | BOOLEAN | Show protected attributes. |
| `AttPkg` | BOOLEAN | Show package attributes. |
| `cx` | INTEGER | Diagram canvas width. |
| `cy` | INTEGER | Diagram canvas height. |
| `Scale` | INTEGER | Zoom scale. |
| `CreatedDate` | DATETIME | Creation timestamp. |
| `ModifiedDate` | DATETIME | Last modification timestamp. |
| `HTMLPath` | TEXT | HTML export path. |
| `ShowForeign` | BOOLEAN | Show foreign keys. |
| `ShowBorder` | BOOLEAN | Show border. |
| `ShowPackageContents` | BOOLEAN | Show package contents. |
| `Orientation` | TEXT | Page orientation. |
| `Swimlanes` | TEXT | Swimlane configuration (complex semicolon-separated format). |
| `StyleEx` | TEXT | Extended style properties (semicolon-separated key=value). |
| `MetaType` | TEXT | Diagram metatype (e.g., for MDG technology diagrams). |

---

### t_diagramobjects -- Element Placement on Diagrams

**This is the critical table for rendering.** It maps which elements appear on which diagrams and where they are positioned.

| Column | Type | Description |
|--------|------|-------------|
| `Instance_ID` | INTEGER | **Primary key.** Unique placement identifier. |
| `Diagram_ID` | INTEGER | FK to `t_diagram.Diagram_ID`. Which diagram this placement is on. |
| `Object_ID` | INTEGER | FK to `t_object.Object_ID`. Which element is placed. |
| `RectTop` | INTEGER | Top Y coordinate (EA uses inverted Y: top of screen is positive). |
| `RectLeft` | INTEGER | Left X coordinate. |
| `RectRight` | INTEGER | Right X coordinate. |
| `RectBottom` | INTEGER | Bottom Y coordinate. |
| `Sequence` | INTEGER | Z-order / draw sequence. |
| `ObjectStyle` | TEXT | Semicolon-separated rendering overrides for this specific placement. |
| `Seqno` | INTEGER | Sequence number (for sequence diagrams). |

**Calculating element dimensions:**
- Width = `RectRight - RectLeft`
- Height = `RectTop - RectBottom` (note: Top > Bottom in EA's coordinate system)
- Position = (`RectLeft`, `RectTop`) for top-left corner

**Note on coordinate system:** EA uses a coordinate system where Y increases upward (mathematical convention), which is the inverse of most screen rendering systems where Y increases downward. When rendering to screen, you will need to invert the Y axis.

---

### t_diagramlinks -- Connector Routing on Diagrams

Controls how connectors are drawn on specific diagrams. A connector may appear on multiple diagrams with different routing.

| Column | Type | Description |
|--------|------|-------------|
| `Instance_ID` | INTEGER | **Primary key.** |
| `Diagram_ID` | INTEGER | FK to `t_diagram.Diagram_ID`. |
| `ConnectorID` | INTEGER | FK to `t_connector.Connector_ID`. |
| `Geometry` | TEXT | Encoded path/routing geometry for the connector on this diagram. |
| `Style` | TEXT | Rendering style overrides. |
| `Hidden` | BOOLEAN | Whether the connector is hidden on this diagram. |
| `Path` | TEXT | Waypoint path data. Semicolon-separated coordinate pairs. |
| `SX` | INTEGER | Start point X offset. |
| `SY` | INTEGER | Start point Y offset. |
| `EX` | INTEGER | End point X offset. |
| `EY` | INTEGER | End point Y offset. |

---

### t_connector -- Relationships Between Elements

| Column | Type | Description |
|--------|------|-------------|
| `Connector_ID` | INTEGER | **Primary key.** |
| `Name` | TEXT | Connector name (often empty). |
| `Direction` | TEXT | Direction string (`Source -> Destination`, `Destination -> Source`, `Bi-Directional`, `Unspecified`). |
| `Notes` | TEXT | Connector description. |
| `Connector_Type` | TEXT | Relationship type. See Connector_Type reference below. |
| `SubType` | TEXT | Subtype string. |
| `SourceCard` | TEXT | Source cardinality (e.g., `1`, `0..*`, `1..*`). |
| `SourceAccess` | TEXT | Source access/visibility. |
| `SourceElement` | TEXT | Source element description. |
| `DestCard` | TEXT | Destination cardinality. |
| `DestAccess` | TEXT | Destination access/visibility. |
| `DestElement` | TEXT | Destination element description. |
| `SourceRole` | TEXT | Source role name. |
| `SourceRoleType` | TEXT | Source role type. |
| `SourceRoleNote` | TEXT | Source role description. |
| `SourceContainment` | TEXT | Source containment type. |
| `SourceIsAggregate` | INTEGER | Source aggregation flag. |
| `SourceIsOrdered` | INTEGER | Source ordering flag. |
| `SourceQualifier` | TEXT | Source qualifier. |
| `DestRole` | TEXT | Destination role name. |
| `DestRoleType` | TEXT | Destination role type. |
| `DestRoleNote` | TEXT | Destination role description. |
| `DestContainment` | TEXT | Destination containment type. |
| `DestIsAggregate` | INTEGER | Destination aggregation flag. |
| `DestIsOrdered` | INTEGER | Destination ordering flag. |
| `DestQualifier` | TEXT | Destination qualifier. |
| `Start_Object_ID` | INTEGER | FK to `t_object.Object_ID`. Source element. |
| `End_Object_ID` | INTEGER | FK to `t_object.Object_ID`. Target element. |
| `Top_Start_Label` | TEXT | Label at source top. |
| `Top_Mid_Label` | TEXT | Label at middle top. |
| `Top_End_Label` | TEXT | Label at target top. |
| `Btm_Start_Label` | TEXT | Label at source bottom. |
| `Btm_Mid_Label` | TEXT | Label at middle bottom. |
| `Btm_End_Label` | TEXT | Label at target bottom. |
| `Start_Edge` | INTEGER | Edge of source element where connector starts (0=top, 1=right, 2=bottom, 3=left). |
| `End_Edge` | INTEGER | Edge of target element where connector ends. |
| `PtStartX` | INTEGER | Start point X coordinate. |
| `PtStartY` | INTEGER | Start point Y coordinate. |
| `PtEndX` | INTEGER | End point X coordinate. |
| `PtEndY` | INTEGER | End point Y coordinate. |
| `RouteStyle` | INTEGER | Routing algorithm (0=direct, 1=auto, 2=custom, 3=tree vertical, etc.). |
| `Stereotype` | TEXT | Connector stereotype. |
| `ea_guid` | TEXT | GUID. |
| `IsRoot` | BOOLEAN | Root flag. |
| `IsLeaf` | BOOLEAN | Leaf flag. |
| `IsSpec` | BOOLEAN | Specification flag. |
| `SourceChangeable` | TEXT | Source changeability. |
| `DestChangeable` | TEXT | Destination changeability. |
| `SourceTS` | TEXT | Source constraint. |
| `DestTS` | TEXT | Destination constraint. |
| `StateFlags` | TEXT | State flags. |
| `ActionFlags` | TEXT | Action flags. |
| `IsSignal` | BOOLEAN | Signal flag. |
| `IsStimulus` | BOOLEAN | Stimulus flag. |
| `DispatchAction` | TEXT | Dispatch action. |
| `Target2` | INTEGER | Secondary target. |
| `StyleEx` | TEXT | Extended style (semicolon-separated). |
| `SourceStereotype` | TEXT | Source end stereotype. |
| `DestStereotype` | TEXT | Destination end stereotype. |
| `SourceStyle` | TEXT | Source end style. |
| `DestStyle` | TEXT | Destination end style. |
| `EventFlags` | TEXT | Event flags. |
| `VirtualInheritance` | TEXT | Virtual inheritance flag. |

---

### t_attribute -- Element Attributes

| Column | Type | Description |
|--------|------|-------------|
| `ID` | INTEGER | **Primary key.** |
| `Object_ID` | INTEGER | FK to `t_object.Object_ID`. Owning element. |
| `Name` | TEXT | Attribute name. |
| `Scope` | TEXT | Visibility (public, private, protected, package). |
| `Stereotype` | TEXT | Attribute stereotype. |
| `Containment` | TEXT | Containment type. |
| `IsStatic` | BOOLEAN | Static flag. |
| `IsCollection` | BOOLEAN | Collection flag. |
| `IsOrdered` | BOOLEAN | Ordered flag. |
| `AllowDuplicates` | BOOLEAN | Allow duplicates flag. |
| `LowerBound` | TEXT | Lower bound multiplicity. |
| `UpperBound` | TEXT | Upper bound multiplicity. |
| `Container` | TEXT | Container type. |
| `Notes` | TEXT | Attribute description. |
| `Derived` | TEXT | Derived flag. |
| `Pos` | INTEGER | Position/order within the element. |
| `GenOption` | TEXT | Code generation options. |
| `Length` | INTEGER | Data length. |
| `Precision` | INTEGER | Data precision. |
| `Scale` | INTEGER | Data scale. |
| `Const` | BOOLEAN | Constant flag. |
| `Style` | TEXT | Style properties. |
| `Classifier` | TEXT | FK to classifying element. |
| `Default` | TEXT | Default value. |
| `Type` | TEXT | Attribute data type string. |
| `ea_guid` | TEXT | GUID. |
| `StyleEx` | TEXT | Extended style. |

---

### t_objectproperties -- Tagged Values (Element Level)

**This is where tagged values for elements are stored.** Not `t_taggedvalue`.

| Column | Type | Description |
|--------|------|-------------|
| `PropertyID` | INTEGER | **Primary key.** |
| `Object_ID` | INTEGER | FK to `t_object.Object_ID`. |
| `Property` | TEXT | Tag name/key. |
| `Value` | TEXT | Tag value. |
| `Notes` | TEXT | Additional notes on the tagged value. |
| `ea_guid` | TEXT | GUID. |

---

## Object_Type Reference

The `Object_Type` column in `t_object` identifies what kind of element it is. Common values:

### Standard UML Types
- `Class` - UML Class
- `Interface` - UML Interface
- `Package` - Package element (also has row in `t_package`)
- `Component` - UML Component
- `Node` - UML Node (deployment)
- `UseCase` - Use Case
- `Actor` - Actor
- `Interaction` - Interaction
- `Activity` - Activity
- `StateMachine` - State Machine
- `State` - State
- `Object` - Object instance
- `Artifact` - Artifact
- `Collaboration` - Collaboration
- `Sequence` - Sequence element

### Special/Display Types
- `Text` - Text label, hyperlink, legend, or diagram note (see NType)
- `Note` - UML Note element
- `Boundary` - Visual boundary
- `UMLDiagram` - Diagram frame or reference
- `StateNode` - State machine nodes (initial, final, junction, choice -- see NType)
- `Event` - Event element (send, receive, timer -- see NType)
- `InteractionFragment` - Combined fragment (alt, opt, loop, par, etc. -- see NType)
- `ProxyConnector` - Connector-from-connector element

### Enterprise Architecture Types (ArchiMate, etc.)
- `ApplicationComponent`
- `BusinessProcess`
- `DataObject`
- `TechnologyService`
- (Many more depending on MDG technologies loaded)

### Requirement Types
- `Requirement` - Requirement element
- `Constraint` - Constraint element
- `Issue` - Issue element
- `Change` - Change element

---

## NType Subtype Reference

The `NType` column modifies the meaning of `Object_Type`. This is context-sensitive:

### Text Elements (`Object_Type = 'Text'`)
| NType | Meaning |
|-------|---------|
| 0 | Plain text |
| 18 | Diagram Note |
| 19 | Hyperlink (`Name` contains `$help://`, `$inet://`, etc.) |
| 76 | Legend |
| 82 | Diagram Hyperlink (`PDATA1` = `t_diagram.Diagram_ID`) |

### State Nodes (`Object_Type = 'StateNode'`)
| NType | Meaning |
|-------|---------|
| 3 | Initial state |
| 4 | Final state |
| 5 | Shallow history |
| 10 | Junction |
| 11 | Choice |
| 13 | Entry point |
| 14 | Exit point |
| 15 | Deep history |
| 100 | Activity initial |
| 101 | Activity final |
| 102 | Flow final |

### Events (`Object_Type = 'Event'`)
| NType | Meaning |
|-------|---------|
| 0 | Send event |
| 1 | Receive event |
| 2 | Accept timer event |

### UML Diagram Frames (`Object_Type = 'UMLDiagram'`)
| NType | Meaning |
|-------|---------|
| 0 | Frame (`PDATA1` = `t_diagram.Diagram_ID`) |
| 1 | Diagram reference (`PDATA1` = `t_diagram.Diagram_ID`) |

### Interaction Fragments (`Object_Type = 'InteractionFragment'`)
| NType | Meaning |
|-------|---------|
| 0 | alt |
| 1 | opt |
| 2 | break |
| 3 | par |
| 4 | loop |
| 5 | critical |
| 6 | neg |
| 7 | assert |
| 8 | strict |
| 9 | seq |
| 10 | ignore |
| 11 | consider |

### Composite Diagrams
If `Object_Type` is one of `Activity`, `Artifact`, `Class`, `Interaction`, `Requirement`, `State`, `StateMachine`, `UseCase` and `NType = 8` and `PDATA1 > 0`, then `PDATA1` is the `Diagram_ID` of the composite diagram.

---

## Connector_Type Reference

Common values for `t_connector.Connector_Type`:

### UML Relationships
- `Association` - Association
- `Aggregation` - Aggregation (check `SourceIsAggregate` / `DestIsAggregate`)
- `Composition` - Composition (stronger form of aggregation)
- `Generalization` - Inheritance/generalization
- `Realisation` - Realization/implementation
- `Dependency` - Dependency
- `Usage` - Usage dependency
- `Abstraction` - Abstraction
- `Nesting` - Nesting relationship

### Other Relationship Types
- `NoteLink` - Link from a note element to another element
- `Connector` - Generic connector
- `InformationFlow` - Information flow
- `Delegate` - Delegation
- `Assembly` - Assembly connector
- `ControlFlow` - Control flow (activity diagrams)
- `ObjectFlow` - Object flow (activity diagrams)
- `Transition` - State transition
- `Sequence` - Sequence diagram message
- `UseCase` - Use case relationship (include/extend via stereotype)
- `Manifest` - Manifestation
- `Deployment` - Deployment

### ArchiMate Relationships (if MDG loaded)
- `ArchiMate_Access`
- `ArchiMate_Association`
- `ArchiMate_Composition`
- `ArchiMate_Flow`
- `ArchiMate_Realization`
- `ArchiMate_Serving`
- `ArchiMate_Triggering`
- (And others)

---

## Essential SQL Queries for Rendering

### 1. Get All Diagrams
```sql
SELECT d.Diagram_ID, d.Name, d.Diagram_Type, d.Stereotype, d.MetaType,
       d.Package_ID, d.cx, d.cy, d.Scale, d.ModifiedDate,
       p.Name AS PackageName
FROM t_diagram d
LEFT JOIN t_package p ON d.Package_ID = p.Package_ID
ORDER BY p.Name, d.Name;
```

### 2. Get All Elements on a Specific Diagram (with positions)
```sql
SELECT do.Instance_ID, do.RectTop, do.RectLeft, do.RectRight, do.RectBottom,
       do.Sequence, do.ObjectStyle,
       o.Object_ID, o.Name, o.Object_Type, o.NType, o.Stereotype,
       o.Backcolor, o.Bordercolor, o.Fontcolor, o.BorderWidth,
       o.Alias, o.Status, o.Notes
FROM t_diagramobjects do
JOIN t_object o ON do.Object_ID = o.Object_ID
WHERE do.Diagram_ID = ?
ORDER BY do.Sequence;
```

### 3. Get All Connectors on a Specific Diagram (with routing)
```sql
SELECT dl.Instance_ID, dl.ConnectorID, dl.Geometry, dl.Style, dl.Hidden,
       dl.Path, dl.SX, dl.SY, dl.EX, dl.EY,
       c.Connector_ID, c.Name, c.Connector_Type, c.Stereotype, c.Direction,
       c.Start_Object_ID, c.End_Object_ID,
       c.SourceCard, c.DestCard, c.SourceRole, c.DestRole,
       c.Start_Edge, c.End_Edge,
       c.PtStartX, c.PtStartY, c.PtEndX, c.PtEndY,
       c.RouteStyle,
       src.Name AS SourceName, dst.Name AS DestName
FROM t_diagramlinks dl
JOIN t_connector c ON dl.ConnectorID = c.Connector_ID
LEFT JOIN t_object src ON c.Start_Object_ID = src.Object_ID
LEFT JOIN t_object dst ON c.End_Object_ID = dst.Object_ID
WHERE dl.Diagram_ID = ?
  AND (dl.Hidden IS NULL OR dl.Hidden = 0);
```

### 4. Get Attributes for an Element
```sql
SELECT a.ID, a.Name, a.Type, a.Scope, a.Stereotype, a.Default,
       a.Notes, a.Pos, a.IsStatic, a.Const,
       a.LowerBound, a.UpperBound
FROM t_attribute a
WHERE a.Object_ID = ?
ORDER BY a.Pos;
```

### 5. Get Operations for an Element
```sql
SELECT op.OperationID, op.Name, op.Type, op.Scope, op.Stereotype,
       op.Notes, op.Pos, op.IsStatic, op.Abstract, op.Concurrency
FROM t_operation op
WHERE op.Object_ID = ?
ORDER BY op.Pos;
```

### 6. Get Tagged Values for an Element
```sql
SELECT tp.PropertyID, tp.Property, tp.Value, tp.Notes
FROM t_objectproperties tp
WHERE tp.Object_ID = ?
ORDER BY tp.Property;
```

### 7. Get the Full Package Hierarchy
```sql
WITH RECURSIVE pkg_tree AS (
    SELECT Package_ID, Name, Parent_ID, 0 AS depth,
           CAST(Name AS TEXT) AS path
    FROM t_package
    WHERE Parent_ID = 0
    UNION ALL
    SELECT p.Package_ID, p.Name, p.Parent_ID, pt.depth + 1,
           pt.path || '/' || p.Name
    FROM t_package p
    JOIN pkg_tree pt ON p.Parent_ID = pt.Package_ID
)
SELECT * FROM pkg_tree ORDER BY path;
```

### 8. Find Orphaned Elements (not on any diagram)
```sql
SELECT o.Object_ID, o.Name, o.Object_Type, o.Stereotype
FROM t_object o
LEFT JOIN t_diagramobjects do ON o.Object_ID = do.Object_ID
WHERE do.Object_ID IS NULL;
```

### 9. Relationship Count Per Element
```sql
SELECT o.Name, o.Object_Type,
       COUNT(c.Connector_ID) AS ConnectionCount
FROM t_object o
LEFT JOIN t_connector c
    ON o.Object_ID IN (c.Start_Object_ID, c.End_Object_ID)
GROUP BY o.Object_ID, o.Name, o.Object_Type
ORDER BY ConnectionCount DESC;
```

### 10. Get Connector Path/Routing Details for a Diagram
```sql
SELECT c.Connector_ID,
       c.Start_Object_ID, c.End_Object_ID,
       c.Start_Edge, c.End_Edge,
       c.PtStartX, c.PtStartY,
       c.PtEndX, c.PtEndY,
       c.RouteStyle,
       dl.Path,
       dl.SX, dl.SY, dl.EX, dl.EY,
       dl.Geometry
FROM t_connector c
JOIN t_diagramlinks dl ON c.Connector_ID = dl.ConnectorID
WHERE dl.Diagram_ID = ?
  AND (dl.Hidden IS NULL OR dl.Hidden = 0);
```

---

## Rendering Considerations

### Coordinate System
EA uses a mathematical coordinate system (Y increases upward). Most screen/SVG/canvas systems use Y increasing downward. You will need to invert Y coordinates when rendering:
- Screen Y = MaxY - EA_Y (or negate and offset)

### Color Encoding
Colors in `Backcolor`, `Bordercolor`, `Fontcolor` are stored as decimal integers representing BGR (not RGB):
- Blue = (color >> 16) & 0xFF
- Green = (color >> 8) & 0xFF
- Red = color & 0xFF
- To convert to hex RGB: swap red and blue channels

A value of -1 typically means "use default color."

### Element Sizing
Element dimensions come from `t_diagramobjects`:
- Width = `RectRight - RectLeft`
- Height = `RectTop - RectBottom`

The element's visual content (attributes, operations, compartments) determines minimum size but the stored coordinates represent the actual rendered size.

### Connector Routing
Connectors have multiple layers of routing information:
1. `t_connector` has global routing hints (`Start_Edge`, `End_Edge`, `PtStartX/Y`, `PtEndX/Y`, `RouteStyle`)
2. `t_diagramlinks` has per-diagram routing (`Path`, `Geometry`, `SX/SY`, `EX/EY`)
3. The `Path` column contains waypoints as semicolon-separated coordinate pairs
4. The `Geometry` column contains more detailed encoded routing data

### Semicolon-Separated Style Strings
Many columns (`Style`, `StyleEx`, `ObjectStyle`) use semicolon-separated key=value pairs:
```
key1=value1;key2=value2;key3=value3;
```
These override default rendering behavior. Parse them into dictionaries for each element/connector placement.

### Diagram Images
EA stores rendered diagram images in the database (in `t_document` or related tables). These are cached bitmaps and may not be present in all models. For a renderer, you should render from the structural data rather than relying on cached images.

---

## Key Gotchas and Warnings

1. **Tagged values are in `t_objectproperties`, NOT `t_taggedvalue`.** The `t_taggedvalue` table is for WSDL model elements only.

2. **The `Note` column is filtered by EA's SQL Search.** Always alias it: `SELECT t_object.Note AS [Notes]`.

3. **`Object_Type` display may be mangled.** EA may display `StartEvent` for rows where the actual stored value is `Event`. Always check with `GROUP BY object_type`.

4. **Package elements are dual-stored.** Every package exists in both `t_package` and `t_object` (with `Object_Type = 'Package'`). Keep this in mind to avoid double-counting.

5. **PDATA columns are overloaded.** Their meaning depends entirely on `Object_Type`. Always check the context.

6. **Colors are BGR, not RGB.** Swap the byte order when converting to standard hex colors.

7. **Y-axis is inverted** relative to screen coordinates.

8. **Read-only access recommended.** Never write directly to the database. Use the EA API for modifications.

9. **The schema is very stable.** It has remained largely unchanged across EA versions, with the audit tables being the last major addition.

---

## References

- "Inside Enterprise Architect" by Thomas Kilian (Leanpub) -- the definitive database schema reference
- "Scripting Enterprise Architect" by Thomas Kilian (Leanpub) -- API reference companion
- Sparx Systems EA User Guide: https://sparxsystems.com/enterprise_architect_user_guide/
- Sparx Systems DBMS Schema Scripts: https://sparxsystems.com/resources/repositories/
- Geert Bellekens' blog: extensive EA technical content
- Capri-Soft Knowledge Base: SQL query examples for EA data extraction
- UML Channel (umlchannel.com): EA community articles and tools
