---
name: do.mermaid
description: Create accurate Mermaid diagrams in Obsidian. Covers all diagram types with syntax, examples, and common pitfalls. Use when generating any Mermaid code block or when the user mentions diagrams, flowcharts, mindmaps, sequence diagrams, gantt charts, or any other visualization.
---

# Mermaid Diagram Skill

This skill enables accurate creation of Mermaid diagrams inside Obsidian Markdown files. It covers every major diagram type with correct syntax, working examples, and critical pitfalls.

## ⚠️ Global Syntax Rules (MUST FOLLOW)

1. **NO full-width punctuation** inside code blocks. All parentheses, commas, colons, and symbols MUST be half-width (English) characters.
   - ❌ `，` `。` `！` `（` `）` `：`
   - ✅ `,` `.` `!` `(` `)` `:`
2. **Quote node labels** containing special characters like `()`, `[]`, `{}` using double quotes: `A["Label (info)"]`
3. **No HTML tags** in labels (use `<br/>` only when explicitly needed for line breaks).
4. **Indentation matters** in mindmaps and timelines — use spaces only, never `- ` or `* `.
5. Read `deeporbit.json` from the workspace root to determine the interaction language. Use this language for all your responses and generated note contents (e.g. `zh-CN`). **The Obsidian folder paths themselves will ALWAYS remain in English.**

## Diagram Selection Guide

| Scenario | Diagram Type | Declaration |
|----------|-------------|-------------|
| Logic flow, steps, decisions | Flowchart | `flowchart TD` |
| Hierarchical concepts, brainstorm | Mindmap | `mindmap` |
| Object interactions over time | Sequence Diagram | `sequenceDiagram` |
| Project schedule, milestones | Gantt Chart | `gantt` |
| System states, transitions | State Diagram | `stateDiagram-v2` |
| OOP class relationships | Class Diagram | `classDiagram` |
| Database schema, entities | ER Diagram | `erDiagram` |
| User experience path | User Journey | `journey` |
| Priority matrix, 2D positioning | Quadrant Chart | `quadrantChart` |
| Historical events, milestones | Timeline | `timeline` |
| Branch/merge visualization | Git Graph | `gitGraph` |
| Proportional distribution | Pie Chart | `pie` |
| Numeric trends, bar+line | XY Chart | `xychart-beta` |
| Task board, workflow columns | Kanban | `kanban` |

---

## 1. Flowchart

The most common diagram. Supports multiple node shapes, subgraphs, and conditional edges.

### Direction

| Declaration | Direction |
|-------------|-----------|
| `flowchart TD` or `flowchart TB` | Top → Down (preferred) |
| `flowchart LR` | Left → Right |
| `flowchart BT` | Bottom → Top |
| `flowchart RL` | Right → Left |

### Node Shapes

```
A[Rectangle]        B(Rounded)         C{Diamond/Decision}
D((Circle))         E([Stadium])       F[[Subroutine]]
G[(Cylinder/DB)]    H{{Hexagon}}       I>Asymmetric]
J[/Parallelogram/]  K[\Parallelogram\] L[/Trapezoid\]
```

### Link Types

| Syntax | Description |
|--------|-------------|
| `A --> B` | Arrow |
| `A --- B` | Open link (no arrow) |
| `A -->|text| B` | Arrow with label ⚠️ **`|` required** |
| `A -.-> B` | Dotted arrow |
| `A -.->|text| B` | Dotted arrow with label |
| `A ==> B` | Thick arrow |
| `A ==>|text| B` | Thick arrow with label |
| `A ~~~ B` | Invisible link (for layout control) |

> [!CAUTION]
> **Conditional edges MUST use double pipe `|`**: `A -->|Yes| B`. Never write `A --> Yes B` or `A --Yes--> B` in flowchart syntax.

### Subgraphs

```mermaid
flowchart TD
    subgraph Backend
        A[API Server] --> B[(Database)]
    end
    subgraph Frontend
        C[React App] --> D[Components]
    end
    C --> A
```

Subgraphs can have their own direction:
```
subgraph Name
    direction LR
    ...
end
```

### Styling

```mermaid
flowchart TD
    A[Start] --> B[End]
    style A fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style B fill:#1a1a2e,stroke:#533483,color:#e0e0e0
```

Using CSS classes:
```
classDef highlight fill:#f9f,stroke:#333,stroke-width:2px
A:::highlight --> B
```

### Complete Example

```mermaid
flowchart TD
    A[User Input] --> B{Input Type?}
    B -->|URL| C[Fetch Content]
    B -->|PDF| D[Extract Text]
    B -->|Text| E[Parse Directly]
    C --> F[Summarize]
    D --> F
    E --> F
    F --> G[(Save to Vault)]
```

---

## 2. Mindmap

Best for hierarchical concept decomposition. **Obsidian fully supports this.**

### Syntax Rules

- Declare with `mindmap` (no direction keyword)
- Root node uses `root((...))` for circle or just `root(text)`
- **Indentation = hierarchy** (spaces only)
- ⚠️ **NEVER use `- ` or `* ` list markers**

### Node Shapes in Mindmap

```
root((Circle Root))
    Square node
    (Rounded)
    [Square]
    ))Bang((
    )Cloud(
```

### Complete Example

```mermaid
mindmap
  root((DeepOrbit))
    AI Agents
      Gemini CLI
      Claude Code
    PKM
      Obsidian
      Daily Notes
    Research
      ArXiv
      Deep Dive
```

---

## 3. Sequence Diagram

Describes interactions between actors/objects over time.

### Syntax

```
sequenceDiagram
    participant A as Alice
    participant B as Bob
    A->>B: Sync message (solid arrow)
    B-->>A: Async reply (dashed arrow)
    A-)B: Async message (open arrow)
```

### Arrow Types

| Syntax | Description |
|--------|-------------|
| `->>`  | Solid line with arrowhead |
| `-->>` | Dashed line with arrowhead |
| `-)`   | Solid line with open arrow |
| `--)`  | Dashed line with open arrow |
| `->`   | Solid line without arrowhead |
| `-->`  | Dashed line without arrowhead |

### Features

```mermaid
sequenceDiagram
    autonumber
    Alice->>John: Hello John
    loop Health Check
        John->>John: Self check
    end
    Note right of John: Rational thoughts<br/>prevail!
    John-->>Alice: Great!
    alt Success
        Alice->>Bob: Forward message
    else Failure
        Alice->>Alice: Retry
    end
```

**Blocks:** `loop`, `alt/else`, `opt`, `par/and`, `critical/option`, `break`, `rect` (highlight), `Note left of/right of/over`

---

## 4. Gantt Chart

Project schedules with task dependencies.

```mermaid
gantt
    title Project Plan
    dateFormat YYYY-MM-DD
    section Design
    Requirements    :done,    des1, 2026-03-01, 2026-03-05
    UI Design       :active,  des2, 2026-03-06, 3d
    section Dev
    Backend         :         dev1, after des2, 5d
    Frontend        :         dev2, after des2, 5d
```

### Task Status Keywords

| Keyword | Description |
|---------|-------------|
| `done` | Completed |
| `active` | In progress |
| `crit` | Critical path |
| (none) | Future/planned |

---

## 5. State Diagram

System states and transitions.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing: Start
    Processing --> Done: Success
    Processing --> Error: Failure
    Error --> Idle: Retry
    Done --> [*]
```

`[*]` = start/end pseudo-state. Supports `state "label" as s1`, composite states, forks, and notes.

---

## 6. Class Diagram

OOP class modeling with relationships.

```mermaid
classDiagram
    Animal <|-- Duck
    Animal <|-- Fish
    Animal : +int age
    Animal : +String gender
    Animal: +isMammal()
    class Duck{
        +String beakColor
        +swim()
        +quack()
    }
```

### Relationship Types

| Syntax | Meaning |
|--------|---------|
| `<\|--` | Inheritance |
| `*--` | Composition |
| `o--` | Aggregation |
| `-->` | Association |
| `..>` | Dependency |
| `..\|>` | Realization |

---

## 7. ER Diagram

Database entity-relationship modeling.

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses
```

### Cardinality Notation

| Symbol | Meaning |
|--------|---------|
| `\|\|` | Exactly one |
| `o\|` | Zero or one |
| `}o` | Zero or more |
| `}\|` | One or more |

---

## 8. User Journey

User experience paths with satisfaction scores (1-5).

```mermaid
journey
    title My Working Day
    section Morning
      Make tea: 5: Me
      Go upstairs: 3: Me, Cat
    section Work
      Do work: 1: Me, Boss
```

---

## 9. Quadrant Chart

2D positioning for priority/evaluation matrices.

```mermaid
quadrantChart
    title Feature Priority
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Do First
    quadrant-2 Plan
    quadrant-3 Eliminate
    quadrant-4 Delegate
    Feature A: [0.3, 0.8]
    Feature B: [0.7, 0.2]
    Feature C: [0.5, 0.6]
```

Coordinates are `[x, y]` where both axes range from `0` to `1`.

---

## 10. Timeline

Historical events and milestones.

```mermaid
timeline
    title AI Milestones
    2022 : ChatGPT Released : Generative AI Boom
    2023 : GPT-4 : Multimodal Breakthrough
    2024 : AI Agents : From Chat to Action
```

Format: `Year : Event1 : Event2`. Uses indentation for sections.

---

## 11. Git Graph

Branch and merge visualization.

```mermaid
gitGraph
    commit
    commit
    branch develop
    checkout develop
    commit
    commit
    checkout main
    merge develop
    commit
```

Commands: `commit`, `branch`, `checkout`, `merge`, `cherry-pick`. Supports `commit id: "msg"` and `commit tag: "v1.0"`.

---

## 12. Pie Chart

Proportional data distribution.

```mermaid
pie title Skill Distribution
    "Computer Vision" : 45
    "Deep Learning" : 30
    "System Engineering" : 15
    "Others" : 10
```

---

## 13. XY Chart (Beta)

Numerical trends with bar and line plots.

```mermaid
xychart-beta
    title "Sales Revenue"
    x-axis [Jan, Feb, Mar, Apr, May]
    y-axis "Revenue ($)" 0 --> 11000
    bar [5000, 6000, 7500, 8200, 9500]
    line [5000, 6000, 7500, 8200, 9500]
```

---

## 14. Kanban

Task board with workflow columns.

```mermaid
kanban
  Todo
    [Build dev environment]
    [Read source code]
  Doing
    [Prepare interview]
  Done
    [Update CV]
```

Columns are top-level labels. Tasks use `[Task name]` with indentation.

---

## Common Pitfalls

| Problem | Wrong | Correct |
|---------|-------|---------|
| Missing pipe on conditional edge | `A --> Yes B` | `A -->\|Yes\| B` |
| Full-width punctuation in code | `A[启动，运行]` | `A["Start, Run"]` |
| List markers in mindmap | `- Child node` | `  Child node` (indent with spaces) |
| Unquoted special chars in labels | `A[Label (v2)]` | `A["Label (v2)"]` |
| Wrong direction keyword | `flowchart top-down` | `flowchart TD` |

## References

- [Mermaid Official Docs](https://mermaid.js.org/)
- [Flowchart Syntax](https://mermaid.js.org/syntax/flowchart.html)
- [Sequence Diagram](https://mermaid.js.org/syntax/sequenceDiagram.html)
- [Class Diagram](https://mermaid.js.org/syntax/classDiagram.html)
- [State Diagram](https://mermaid.js.org/syntax/stateDiagram.html)
- [ER Diagram](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)
- [Gantt Chart](https://mermaid.js.org/syntax/gantt.html)
- [Mindmap](https://mermaid.js.org/syntax/mindmap.html)
- [Timeline](https://mermaid.js.org/syntax/timeline.html)
- [Quadrant Chart](https://mermaid.js.org/syntax/quadrantChart.html)
- [XY Chart](https://mermaid.js.org/syntax/xyChart.html)
- [Kanban](https://mermaid.js.org/syntax/kanban.html)
- [Git Graph](https://mermaid.js.org/syntax/gitgraph.html)
