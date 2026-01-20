# Documentation Policy

## Purpose
This document establishes the organizational structure for all markdown documentation within the ContentStash project.

## Documentation Structure

All markdown documentation files must be placed in the appropriate `documents/` subfolder based on their scope:

### Root Documentation (`/documents/`)
Place documentation here that covers:
- Project-wide specifications and requirements (e.g., PRD.md)
- Cross-cutting implementation plans (e.g., Backend-dev-plan.md)
- Feature implementation summaries that span multiple components
- Testing strategies and branch documentation
- Any documentation that doesn't fit specifically into frontend or backend scope

### Frontend Documentation (`/frontend/documents/`)
Place documentation here that covers:
- Frontend-specific README files
- Frontend deployment guides
- Frontend architecture and design decisions
- Frontend-specific feature documentation
- UI/UX implementation details

### Backend Documentation (`/backend/documents/`)
Place documentation here that covers:
- Backend-specific implementation guides
- API documentation
- Database and vector search setup
- Content extraction and processing documentation
- Backend service integration guides
- Backend-specific feature implementations

## Guidelines

1. **New Documentation**: All new markdown documentation must be created in the appropriate `documents/` subfolder from the start.

2. **Naming Conventions**: Use clear, descriptive names in UPPERCASE with underscores (e.g., `FEATURE_NAME_IMPLEMENTATION.md`) or standard README naming conventions.

3. **Cross-Reference**: When documentation in one folder references documentation in another, use relative paths (e.g., `../../backend/documents/VECTOR_SEARCH_SETUP.md`).

4. **Scope Determination**: If unsure which folder to use:
   - Does it only affect frontend? → `frontend/documents/`
   - Does it only affect backend? → `backend/documents/`
   - Does it affect both or is project-wide? → `documents/`

## Maintenance

This policy should be reviewed and updated as the project structure evolves. All team members are responsible for adhering to this documentation structure.