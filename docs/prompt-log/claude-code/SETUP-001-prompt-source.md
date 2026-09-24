# SETUP-001 — Initialize Knowledge Assistant Project

You are performing the INITIAL PROJECT SETUP for the Knowledge Assistant project.

This is an architecture and repository setup task.

DO NOT implement the actual RAG pipeline yet.
DO NOT implement question generation yet.
DO NOT implement evaluation logic yet.
DO NOT implement experiments yet.
DO NOT build the complete GUI yet.

Your responsibility is to establish a clean, traceable, maintainable project foundation that follows the architecture and technology decisions defined below.

## 1. PROJECT PURPOSE

The project is a grounded Knowledge Assistant based on a defined collection of documents.

The final system must implement a RAG pipeline:

    Documents
        ↓
    Parsing
        ↓
    Chunking
        ↓
    Embedding
        ↓
    Vector Storage / Retrieval
        ↓
    Gemini LLM
        ↓
    Answer + Citation

The system must eventually support:

- document ingestion
- document parsing
- chunking
- embedding
- retrieval
- answer generation
- source citation
- insufficient-information detection
- evaluation using at least 30 questions
- experiment comparing at least 2 approaches
- evaluation reporting
- failure analysis

The current corpus contains 29 original documents.

25 documents have been selected as accepted sources.

4 documents have been deliberately excluded.

The project must preserve this distinction and maintain complete traceability.

## 2. CORE ARCHITECTURE DECISION

The project uses this architectural structure:

    Core
       ↓
    Application
       ↓
    Infrastructure

    Presentation
       ↓
    Application

More precisely:

    presentation
        ↓
    application
        ↓
    core
        ↑
    infrastructure

Responsibilities:

CORE
- domain models
- domain concepts
- interfaces/contracts
- domain exceptions
- technology-independent business concepts

APPLICATION
- use cases
- orchestration
- RAG workflow coordination
- ingestion workflow
- retrieval workflow
- generation workflow
- citation workflow
- evaluation workflow

INFRASTRUCTURE
- document parsers
- chunking implementations
- embedding implementations
- ChromaDB integration
- Gemini API integration
- filesystem persistence
- external technology integrations

PRESENTATION
- PySide6 desktop GUI
- windows
- views
- view models
- widgets
- dialogs
- presentation state

IMPORTANT:

Core MUST NOT depend on PySide6, ChromaDB, Gemini API, or a specific document format.

Application SHOULD depend on interfaces/contracts rather than concrete infrastructure implementations.

Infrastructure implements the contracts required by Core/Application.

Presentation MUST NOT contain core business logic.

## 3. TECHNOLOGY STACK — LOCKED DECISIONS

The following technology decisions are authoritative for this project.

PRIMARY LANGUAGE
- Python

GUI
- PySide6

VECTOR DATABASE
- ChromaDB

LLM PROVIDER
- Google Gemini API

LLM AUTHENTICATION
- Gemini API key supplied through environment configuration.

The Gemini API key MUST NOT be hard-coded into source code.

The Gemini API key MUST NOT be committed to Git.

The project MUST support configuration through environment variables or an equivalent secure local configuration mechanism.

SOURCE CORPUS
- A curated collection of documents.
- The CURRENT corpus happens to consist of Markdown files.
- The architecture MUST NOT assume that Markdown is the only supported document format.

EXPECTED FUTURE INPUT FORMATS
- Markdown
- PDF
- HTML
- potentially other formats through parser adapters

TESTING
- pytest

STRUCTURED DATA
- JSON / JSONL where appropriate

RELATIONAL DATABASE
- NOT required for the initial architecture.
- SQLite MAY be introduced later if a concrete requirement emerges.
- Do NOT add SQLite merely because it is commonly used.

EMBEDDINGS
- Must be abstracted behind an embedding interface.
- The concrete embedding model/provider will be selected during the RAG implementation phase.
- Do NOT assume that Gemini generation automatically determines the embedding implementation.
- Embedding configuration must remain replaceable.

LLM
- Gemini API is the selected LLM provider.
- The Gemini integration MUST be isolated behind an LLM interface.
- The concrete Gemini model/version is TBD until the RAG implementation phase.
- Do NOT hard-code a model name during project setup unless explicitly specified elsewhere.

RERANKING
- Optional.
- It is NOT part of the mandatory baseline implementation.
- It may be introduced later as an experiment or bonus feature.

ML / LOCAL AI
- Optional.
- Do not add ML/ONNX/other model dependencies unless required by a later implementation decision.

PACKAGING
- PyInstaller may be used later for desktop distribution.
- Do not implement packaging during this setup task.

VERSION CONTROL
- Git

## 4. TECHNOLOGY DRIFT RULE

The following technologies MUST NOT be introduced as part of the default architecture:

- C#
- .NET
- Java
- Node.js
- React
- Angular
- Vue
- Flutter
- Electron
- ASP.NET Core as the application framework

ASP.NET Core may exist inside the SOURCE CORPUS because it is a subject being studied.

That does NOT mean the Knowledge Assistant itself should be implemented using ASP.NET Core.

IMPORTANT DISTINCTION:

    "Technology discussed by the corpus"

is NOT the same as:

    "Technology used to implement the Knowledge Assistant."

PySide6 is the desktop presentation technology.

Python is the primary implementation language.

ChromaDB is the vector storage/retrieval technology.

Google Gemini API is the LLM provider.

## 5. SECRET / API KEY MANAGEMENT

Gemini authentication MUST be handled securely.

Use environment-based configuration.

The expected development workflow should support something equivalent to:

    GEMINI_API_KEY=<secret>

Do NOT:

- hard-code the API key
- place the real key in Python source
- place the real key in CLAUDE.md
- place the real key in README.md
- place the real key in documentation
- commit a .env file containing the real secret
- print the API key in logs
- include the API key in reports or snapshots

If a .env-based workflow is introduced later, the actual .env file MUST be ignored by Git.

A safe example configuration may be documented using:

    GEMINI_API_KEY=your_api_key_here

but NEVER use the user's real key in repository files.

Create an appropriate example configuration file if useful, such as:

    .env.example

It must contain placeholders only.

## 6. DOCUMENT FORMAT ABSTRACTION

The application MUST treat documents as format-independent domain objects.

Do NOT design the system around:

    MarkdownDocument

as the primary domain abstraction.

Instead use concepts such as:

    Document
    ParsedDocument
    DocumentChunk
    Citation

Format-specific parsing belongs under:

    src/knowledge_assistant/infrastructure/parsing/

Expected parser structure:

    parsing/
        base.py
        markdown_parser.py
        pdf_parser.py
        html_parser.py
        registry.py

At setup time, these may be skeletons/placeholders.

Do not implement unnecessary parsers yet.

The architecture must allow:

    Markdown
        ↓
    MarkdownParser
        ↓

or:

    PDF
        ↓
    PDFParser
        ↓

or:

    HTML
        ↓
    HTMLParser
        ↓

to produce a normalized internal representation.

Core/Application MUST NOT depend on a specific input format.

## 7. CITATION / PROVENANCE ARCHITECTURE

Citation is a first-class requirement.

The system must eventually be able to trace an answer back to relevant source material.

Citation metadata MUST NOT assume that every source has page numbers.

The citation model should be capable of representing locations such as:

- page
- section
- heading
- paragraph
- line
- URL
- document-relative location
- other format-specific locations

A conceptual citation may contain:

    source_id
    document_name
    location_type
    location
    excerpt

Do not over-engineer the final implementation during setup.

Create the architectural extension point and document the design intent.

## 8. RAG ARCHITECTURE

The baseline RAG architecture is:

    Source Documents
          ↓
       Parsing
          ↓
       Chunking
          ↓
      Embedding
          ↓
       ChromaDB
          ↓
      Retrieval
          ↓
       Context
          ↓
     Gemini LLM
          ↓
    Answer + Citation

The system must eventually support an explicit insufficient-information behavior.

Gemini must not simply answer from unrestricted general knowledge.

The final answer-generation workflow must be grounded in retrieved corpus context.

Do NOT implement this pipeline during SETUP-001.

Only establish the architectural boundaries and skeleton.

## 9. PROJECT STRUCTURE

Create exactly this high-level structure:

knowledge-assistant/
│
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── src/
│   └── knowledge_assistant/
│       ├── __init__.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models/
│       │   ├── interfaces/
│       │   └── exceptions/
│       │
│       ├── application/
│       │   ├── __init__.py
│       │   ├── ingestion/
│       │   ├── retrieval/
│       │   ├── generation/
│       │   ├── citation/
│       │   └── evaluation/
│       │
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── parsing/
│       │   ├── chunking/
│       │   ├── embeddings/
│       │   ├── vector_store/
│       │   │   └── chromadb/
│       │   ├── llm/
│       │   │   └── gemini/
│       │   └── persistence/
│       │
│       └── presentation/
│           └── desktop/
│               ├── __init__.py
│               ├── app.py
│               ├── windows/
│               ├── views/
│               ├── viewmodels/
│               ├── widgets/
│               ├── dialogs/
│               └── resources/
│
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   ├── application/
│   │   └── infrastructure/
│   ├── integration/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   └── evaluation/
│   └── presentation/
│       └── desktop/
│
├── scripts/
│   ├── ingestion/
│   ├── evaluation/
│   ├── experiments/
│   └── utilities/
│
├── corpus/
│   ├── README.md
│   ├── sources/
│   └── excluded/
│
├── data/
│   ├── processed/
│   │   ├── documents/
│   │   └── chunks/
│   ├── chroma/
│   ├── evaluation/
│   │   ├── questions/
│   │   └── results/
│   └── experiments/
│
├── docs/
│   ├── specs/
│   ├── architecture/
│   │   └── decisions/
│   ├── plans/
│   │   ├── epics/
│   │   └── tasks/
│   ├── reports/
│   │   ├── milestones/
│   │   ├── epics/
│   │   └── execution/
│   ├── reviews/
│   │   ├── milestones/
│   │   ├── epics/
│   │   ├── code/
│   │   ├── corpus/
│   │   ├── retrieval/
│   │   └── evaluation/
│   ├── knowledge/
│   │   ├── domain/
│   │   ├── rag/
│   │   ├── engineering/
│   │   ├── evaluation/
│   │   ├── agent-workflow/
│   │   └── lessons-learned/
│   ├── snapshots/
│   │   ├── corpus/
│   │   ├── architecture/
│   │   ├── rag/
│   │   ├── evaluation/
│   │   └── experiments/
│   └── prompt-log/
│       ├── research/
│       ├── gemini-notebook/
│       ├── planning/
│       ├── claude-code/
│       ├── verification/
│       └── qc/
│
├── agents/
│   ├── README.md
│   ├── roles/
│   │   ├── corpus-analyst.md
│   │   ├── ingestion-analyst.md
│   │   ├── rag-analyst.md
│   │   ├── knowledge-map-analyst.md
│   │   ├── evaluation-designer.md
│   │   ├── experiment-designer.md
│   │   ├── verifier.md
│   │   └── quality-controller.md
│   └── prompts/
│
├── validation/
│   ├── ingestion/
│   ├── retrieval/
│   ├── generation/
│   ├── citations/
│   └── evaluation/
│
└── output/
    ├── reports/
    └── exports/

## 10. INITIAL CORE MODELS

Create only minimal domain model/interface skeletons.

Potential domain concepts include:

- Document
- DocumentChunk
- Citation
- Question
- EvaluationCase
- EvaluationResult
- Experiment

Do NOT prematurely implement detailed fields or business rules unless clearly required by the architecture.

If a field or behavior is not yet decided, mark it as TBD in documentation rather than inventing a design.

## 11. APPLICATION LAYER

Create skeleton modules for:

    application/ingestion/
    application/retrieval/
    application/generation/
    application/citation/
    application/evaluation/

These represent application use cases.

Do not implement real RAG behavior yet.

The purpose of this layer is to establish boundaries so that later implementation does not place business logic inside GUI code or infrastructure adapters.

## 12. INFRASTRUCTURE LAYER

Create skeletons for:

    infrastructure/parsing/
    infrastructure/chunking/
    infrastructure/embeddings/
    infrastructure/vector_store/
    infrastructure/vector_store/chromadb/
    infrastructure/llm/
    infrastructure/llm/gemini/
    infrastructure/persistence/

The ChromaDB integration is the selected vector-store technology.

The Gemini API is the selected LLM provider.

Create the integration boundaries, but do not build the complete retrieval or generation implementation yet.

Embedding and LLM providers must remain replaceable through interfaces.

Gemini-specific code MUST remain inside the Infrastructure layer.

## 13. GEMINI API INTEGRATION BOUNDARY

The project uses the Google Gemini API for LLM generation.

Create an infrastructure boundary conceptually equivalent to:

    core/interfaces/llm.py

and a Gemini-specific implementation under:

    infrastructure/llm/gemini/

The exact Gemini SDK and concrete model are implementation-phase decisions unless already explicitly specified elsewhere.

During setup:

- establish the package/module boundary
- establish configuration loading
- establish environment-variable naming
- do not make actual LLM calls
- do not generate real answers
- do not require a valid API key for repository setup validation

Use:

    GEMINI_API_KEY

as the canonical environment variable name.

The application layer MUST NOT import the Gemini SDK directly.

## 14. DESKTOP GUI

The product is a desktop Knowledge Assistant.

Use PySide6.

The presentation layer should be organized as:

    presentation/
        desktop/
            app.py
            windows/
            views/
            viewmodels/
            widgets/
            dialogs/
            resources/

The GUI must not directly:

- parse documents
- access ChromaDB
- call the Gemini API
- perform retrieval logic
- implement evaluation algorithms

The GUI should eventually call Application-layer use cases.

During setup, create only minimal application startup scaffolding.

Do not build the complete UI.

## 15. CORPUS MIGRATION

An existing directory named:

    markdown sources/

contains the 29 original source documents.

After establishing the repository structure, move the documents into the new corpus structure.

Accepted documents:

    corpus/sources/

Excluded documents:

    corpus/excluded/

The following 4 documents are deliberately excluded:

    #14 Hello World - Introductory tutorial
    #19 Order unit tests
    #24 Sharing services added with dependencies via the basic view
    #27 Understanding the Routing Mechanism in ASP.NET Core - Multicode

All other original documents are accepted.

Therefore:

    Original documents = 29
    Accepted = 25
    Excluded = 4

IMPORTANT:

- Preserve original numbering.
- Preserve original filenames whenever possible.
- Do not renumber accepted documents.
- Do not delete excluded documents.
- Do not modify the contents of the source documents.
- Do not silently convert the documents to another format.
- Do not create duplicate copies unless required by the migration process.

The resulting corpus should intentionally have missing source numbers:

    14
    19
    24
    27

inside corpus/sources/.

This is intentional and MUST NOT be "fixed" by renumbering.

## 16. CORPUS README

Create:

    corpus/README.md

Document:

- purpose of the corpus
- original document count
- accepted document count
- excluded document count
- accepted source location
- excluded source location
- preservation of source numbering
- high-level exclusion rationale
- source-of-truth rules
- current format of the corpus
- future format extensibility

Clearly state:

The current dataset consists of 25 accepted Markdown documents, but the ingestion architecture is designed to support additional document formats.

## 17. DATA DIRECTORY

Create:

    data/processed/documents/
    data/processed/chunks/
    data/chroma/
    data/evaluation/questions/
    data/evaluation/results/
    data/experiments/

Do not generate actual embeddings or ChromaDB collections during this setup task unless necessary for validating the infrastructure skeleton.

Do not populate fake evaluation results.

Do not fabricate experiment results.

## 18. EVALUATION ARCHITECTURE

The final system must evaluate at least 30 questions.

Each evaluation case must eventually support:

    Question
    Expected answer / ground truth
    Expected source
    Generated answer
    Result

The architecture must additionally support evaluation of:

- answer quality
- retrieval quality
- citation quality
- latency

Create appropriate documentation/specification placeholders.

Do not create fake scores or results.

## 19. EXPERIMENT ARCHITECTURE

The final project must compare at least two approaches.

Possible experiments include:

- chunk size A vs chunk size B
- vector search vs hybrid search
- baseline RAG vs reranking
- other justified retrieval/generation changes

Do not select an experiment merely for convenience during setup.

The actual experiment should be selected after corpus/RAG analysis.

Create the infrastructure/documentation locations required for experiments:

    data/experiments/
    scripts/experiments/
    docs/reports/
    docs/reviews/

Do not fabricate experiment results.

## 20. DOCUMENTATION SYSTEM

Create README files for the major documentation directories.

Use these distinctions:

docs/specs/
    WHAT and WHY
    formal requirements and contracts

docs/architecture/
    HOW the system is designed

docs/plans/
    WHAT WILL BE DONE and execution sequencing

docs/reports/
    WHAT ACTUALLY HAPPENED

docs/reviews/
    QUALITY / ACCEPTANCE / INDEPENDENT REVIEW

docs/knowledge/
    DISTILLED reusable knowledge

docs/snapshots/
    POINT-IN-TIME project state

docs/prompt-log/
    HISTORICAL prompt record

agents/
    CURRENT operational agent definitions

Do not collapse these responsibilities into a single documentation folder.

## 21. INITIAL SPEC DOCUMENTS

Create skeleton documents:

docs/specs/project-spec.md
docs/specs/corpus-spec.md
docs/specs/ingestion-spec.md
docs/specs/retrieval-spec.md
docs/specs/generation-spec.md
docs/specs/citation-spec.md
docs/specs/evaluation-spec.md
docs/specs/quality-spec.md

Do not invent requirements that have not yet been decided.

Use:

    TBD
    DECISION REQUIRED

where appropriate.

## 22. INITIAL ARCHITECTURE DOCUMENTS

Create:

docs/architecture/system-architecture.md
docs/architecture/data-model.md
docs/architecture/rag-pipeline.md
docs/architecture/ingestion-architecture.md
docs/architecture/retrieval-architecture.md
docs/architecture/evaluation-architecture.md
docs/architecture/gui-architecture.md
docs/architecture/agent-architecture.md
docs/architecture/tech-stack.md

Also create the decisions directory.

The following decisions ARE already made:

- Python
- PySide6
- ChromaDB
- Google Gemini API
- pytest
- Gemini API key via environment variable
- format-independent document architecture
- 25 accepted / 4 excluded corpus structure
- RAG architecture
- evaluation as a first-class project concern
- experiment as a first-class project concern

Record these decisions accurately.

## 23. TECH-STACK DOCUMENT

Create:

    docs/architecture/tech-stack.md

This must explicitly state:

PRIMARY LANGUAGE:
    Python

DESKTOP UI:
    PySide6

VECTOR DATABASE:
    ChromaDB

LLM PROVIDER:
    Google Gemini API

LLM AUTHENTICATION:
    GEMINI_API_KEY environment variable

TESTING:
    pytest

SOURCE FORMAT:
    Current corpus = Markdown
    Architecture = format-independent

STRUCTURED DATA:
    JSON / JSONL

OPTIONAL FUTURE STORAGE:
    SQLite only if a concrete requirement appears

EMBEDDING:
    abstracted behind an interface

LLM:
    Gemini API through an abstraction/interface

RERANKING:
    optional / experiment / bonus

PACKAGING:
    PyInstaller later if required

Also document technologies explicitly NOT part of the default stack.

## 24. CLAUDE.md

Edit the root:

    CLAUDE.md

This is the project constitution.

It must contain project-wide rules, not merely documentation instructions.

At minimum include:

1. Project purpose
2. Scope
3. Technology stack
4. Architecture
5. Repository structure
6. Corpus rules
7. Document-format abstraction
8. RAG grounding rules
9. Retrieval rules
10. Citation/provenance rules
11. Insufficient-information rules
12. Gemini API rules
13. Secret-management rules
14. Evaluation rules
15. Experiment rules
16. GUI architecture rules
17. Testing rules
18. Data management rules
19. Documentation rules
20. Prompt-log rules
21. Agent/subagent rules
22. Validation rules
23. Git/file safety rules
24. Definition of Done

Use:

    MUST
    MUST NOT
    SHOULD
    SHOULD NOT
    MAY

Do not invent unresolved project policies.

Mark unresolved decisions as TBD.

**HOWEVER**, if any rules above can be saved into your long-term project memory, do it instead, keep the CLAUDE.md as short as possible

## 25. AGENT DOCUMENTATION

Create:

agents/README.md

Create role skeletons:

agents/roles/corpus-analyst.md
agents/roles/ingestion-analyst.md
agents/roles/rag-analyst.md
agents/roles/knowledge-map-analyst.md
agents/roles/evaluation-designer.md
agents/roles/experiment-designer.md
agents/roles/verifier.md
agents/roles/quality-controller.md

At setup stage these are role definitions only.

Do not invent detailed operational prompts yet.

## 26. PROMPT LOG

Create:

docs/prompt-log/README.md

Create:

docs/prompt-log/claude-code/SETUP-001-project-structure.md

Record:

- Prompt ID
- Phase
- Purpose
- Input/context
- Prompt
- Expected output
- Actual output
- Problems found
- Revision
- Status

Do not fabricate the Actual Output section before execution.

The prompt log is historical.

The agents directory is operational.

Do not confuse the two.

## 27. INITIAL PLAN

Create:

docs/plans/master-plan.md

Create epic placeholders:

EPIC-01-corpus-analysis
EPIC-02-ingestion-pipeline
EPIC-03-rag-baseline
EPIC-04-knowledge-assistant
EPIC-05-evaluation
EPIC-06-experiment
EPIC-07-final-qc

Do not claim any epic is completed.

## 28. TESTING SETUP

Configure pytest through pyproject.toml.

Create the test directory structure.

At minimum, verify that:

- pytest discovers tests
- package imports work
- the project structure is valid

Do not create meaningless tests merely to increase test count.

Do not require a valid Gemini API key for unit-test discovery or basic repository validation.

Integration tests requiring Gemini MUST be explicitly separated from offline/unit tests.

## 29. PYPROJECT.TOML

Create a clean pyproject.toml.

Keep dependencies minimal.

Required initial runtime dependencies should reflect the locked architecture:

- PySide6
- ChromaDB
- the official Google Gemini Python SDK/client selected for the project

Testing/development dependency:

- pytest

Add only dependencies genuinely required by the initial skeleton.

Do NOT add large AI/ML dependencies simply because they may be useful later.

The concrete embedding dependency may be added when the embedding implementation is selected.

The exact Gemini model is NOT a setup-time decision.

## 30. GIT SAFETY

Create an appropriate .gitignore.

Ignore normal generated files such as:

- __pycache__/
- .pytest_cache/
- .venv/
- build/
- dist/
- IDE-specific files
- .env
- generated runtime artifacts where appropriate

Do NOT accidentally ignore:

- corpus/
- docs/
- agents/
- src/
- tests/
- scripts/
- evaluation definitions
- architecture documents

Be careful with data/chroma/.

The policy for committing generated vector-store data should be documented rather than silently ignored.

## 31. VALIDATION

After setup, verify all of the following:

STRUCTURE
- required directories exist
- required files exist

PYTHON
- package imports successfully
- pyproject.toml is valid
- pytest runs

CORPUS
- all 29 original documents are accounted for
- exactly 25 are accepted
- exactly 4 are excluded
- excluded IDs are 14, 19, 24, 27
- original numbering is preserved
- source contents were not unintentionally modified

ARCHITECTURE
- Core does not depend on PySide6
- Core does not depend on ChromaDB
- Core does not depend directly on Gemini
- Application does not directly contain GUI code
- Application does not directly depend on a concrete Gemini SDK
- presentation is separated from business/application logic
- infrastructure is separated from domain concepts

TECH STACK
- Python is used
- PySide6 is the GUI framework
- ChromaDB is the vector-store technology
- Google Gemini API is the LLM provider
- Gemini authentication uses environment configuration
- pytest is configured
- no unauthorized web stack has been introduced

SECURITY
- no real API key is present in repository files
- .env is ignored
- .env.example contains placeholders only
- API keys are not printed during setup

DOCUMENTATION
- CLAUDE.md exists
- tech-stack.md exists
- architecture documents exist
- prompt log entry exists
- corpus README exists

Do not claim a check passed unless it was actually performed.

## 32. SOURCE INTEGRITY

Before moving the 29 Markdown files, if practical, calculate checksums or another reliable content fingerprint.

After migration, verify that the file contents are unchanged.

The migration must be a file organization operation, not a content-editing operation.

## 33. SETUP REPORT

After completing setup, create:

docs/reports/execution/SETUP-001-project-structure.md

Include:

- setup date
- setup scope
- architecture established
- technology stack established
- files/directories created
- corpus migration summary
- accepted count
- excluded count
- validation performed
- test/import result
- source-integrity result
- issues encountered
- deviations
- unresolved decisions

Do not claim success for unverified operations.

## 34. INITIAL SNAPSHOTS

Create initial snapshots under:

docs/snapshots/corpus/
docs/snapshots/architecture/

Record:

Corpus:

    Original: 29
    Accepted: 25
    Excluded: 4

Excluded:

    14
    19
    24
    27

Architecture:

    Python
    PySide6
    ChromaDB
    Google Gemini API
    pytest
    Gemini API key via environment variable
    Format-independent ingestion
    RAG architecture
    Evaluation-first architecture
    Experiment support

## 35. STRICT SCOPE LIMIT

This task is SETUP ONLY.

DO NOT:

- implement complete RAG
- implement real embedding pipeline
- implement complete ChromaDB retrieval
- make real Gemini generation calls
- implement evaluation metrics
- implement experiment logic
- build the complete GUI
- create fake evaluation data
- create fake benchmark results
- invent ground-truth answers
- invent retrieval scores
- invent latency measurements
- add unnecessary technologies

The repository must be ready for the next development phase, but the next development phase must remain separate from this setup task.

## 36. FINAL RESPONSE

When finished, report:

1. Setup status
2. Architecture established
3. Technology stack established
4. Corpus migration result
5. 25 accepted / 4 excluded confirmation
6. Excluded IDs
7. Validation results
8. pytest result
9. Source-integrity result
10. Gemini configuration status
11. Issues/deviations
12. Unresolved decisions

Do not report unverified success.

The final result should be a clean, reproducible foundation for implementing the Knowledge Assistant RAG system.