# Ownership, assistance and third-party notices

Project owner/maintainer: **Shriram Masalekar**. Repository code and generated synthetic data
are licensed under MIT, as stated in LICENSE. Git commits use the owner's configured Git
identity. They record actual incremental changes made during this build, without backdating.

This implementation was created with OpenAI Codex assistance from the project blueprint
provided by the owner. It was implemented locally for this project; no third-party project
repository or professor's private source code was copied. AI assistance is disclosed so the
owner can accurately explain both the code and the development process. Commit authorship
does not imply every line was typed manually or establish exclusive intellectual-property
rights beyond applicable law and dependency licenses.

The supplied blueprint is a specification, not part of the software license grant. It is not
redistributed in the public source package. The following dependencies remain under their own
licenses; installation does not transfer ownership of them:

| Dependency | Role | License family / upstream |
|---|---|---|
| Python | Runtime and SQLite/CSV/JSON tooling | PSF; https://www.python.org/ |
| PyYAML | Safe YAML parsing | MIT; https://pyyaml.org/ |
| Matplotlib | PNG scientific figures | Matplotlib license (PSF-based); https://matplotlib.org/ |
| NumPy | Matplotlib numerical dependency | BSD-3-Clause; https://numpy.org/ |
| pytest | Automated verification | MIT; https://docs.pytest.org/ |
| Ruff | Lint and format checks | MIT; https://docs.astral.sh/ruff/ |
| setuptools / build | Packaging | MIT; https://setuptools.pypa.io/ and https://build.pypa.io/ |

The exact installed dependency set is recorded in `requirements.lock`. Refer to each installed
distribution's metadata/license files for transitive dependencies and complete license text.
The submission does not vendor third-party library source or binaries. Standard geometry,
log-distance modeling, hysteresis and bootstrap techniques are implemented as described in
the architecture documentation; they are not claimed as new telecommunications standards.
