# Contributing to Jumbox

Thank you for your interest in contributing to Jumbox! We welcome community contributions to make local-first file transfer faster, simpler, and more reliable.

## Development Setup

1. **Clone the repository:**
   `ash
   git clone https://github.com/hd-rx8/jumbox.git
   cd jumbox
   `

2. **Set up Python virtual environment:**
   `ash
   python -m venv .venv
   .\.venv\Scripts\activate   # Windows
   # or: source .venv/bin/activate  # macOS / Linux
   pip install -r requirements.txt pytest httpx
   `

3. **Run tests:**
   `ash
   pytest -v
   `

4. **Start the local development server (Standalone Mode):**
   `ash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   `

## Development Guidelines

- **Architecture:** Maintain clean separation between the domain layer (pp/domain), application layer (pp/application), infrastructure (pp/infrastructure), and API routes (pp/api).
- **TDD / Testing:** Write automated unit and integration tests under 	ests/ for any new features, bug fixes, or endpoints.
- **Integrity & Security:** Ensure all uploaded files are properly sanitized against path-traversal attacks and verified with SHA-256 rolling checksums.
- **Resumability:** Any enhancements to chunk uploads must preserve byte-offset synchronization (Upload-Offset headers) and avoid re-transmitting accepted data.

## Submitting a Pull Request

1. Create a feature branch (git checkout -b feature/my-new-feature).
2. Ensure all tests pass (pytest -v).
3. Commit your changes with clear, descriptive commit messages.
4. Push to your branch and open a Pull Request describing your changes and testing steps.
