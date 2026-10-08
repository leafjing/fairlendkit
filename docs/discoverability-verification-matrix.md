# Discoverability verification matrix

This matrix is the review contract for repository discoverability. Each row
connects a public metadata field or prohibited publication artifact to its
fail-closed verification logic and a named negative regression test.

| ID | Field or prohibited artifact | Verification logic | Negative regression test |
| --- | --- | --- | --- |
| `DV-01` | Software name and package identity | `verify_metadata` compares README, `pyproject.toml`, CFF, CodeMeta, and JSON-LD names; `verify_installed_package` compares the normalized wheel `Name`. | `test_metadata_cross_validation_fails_closed[name]`; `test_installed_wheel_metadata_fails_closed[Name]` |
| `DV-02` | CodeMeta `@context` and `@type` | `verify_metadata` requires the frozen CodeMeta context and `SoftwareSourceCode` type. | `test_metadata_cross_validation_fails_closed[@context]`; `test_metadata_cross_validation_fails_closed[@type]` |
| `DV-03` | Author and maintainer identity | `verify_metadata` compares pyproject, CFF, CodeMeta, and JSON-LD author identities and requires the frozen CodeMeta maintainer object; `verify_installed_package` checks wheel `Author`. | `test_metadata_cross_validation_fails_closed[author]`; `test_metadata_cross_validation_fails_closed[maintainer]`; `test_installed_wheel_metadata_fails_closed[Author]` |
| `DV-04` | Core description and README positioning | `verify_metadata` compares pyproject, CodeMeta, JSON-LD, README positioning, and the CFF abstract; `verify_installed_package` checks wheel `Summary`. | `test_metadata_cross_validation_fails_closed[description]`; `test_readme_and_cff_positioning_fail_closed`; `test_installed_wheel_metadata_fails_closed[Summary]` |
| `DV-05` | Version | `verify_metadata` compares pyproject, CFF, CodeMeta, and JSON-LD versions; `verify_installed_package` checks wheel `Version`. | `test_metadata_cross_validation_fails_closed[version]`; `test_installed_wheel_metadata_fails_closed[Version]` |
| `DV-06` | Repository, issue, documentation, and citation URLs | `verify_metadata` compares repository and issue URLs and CFF identity; `verify_installed_package` requires the complete wheel project-URL set. | `test_metadata_cross_validation_fails_closed[codeRepository]`; `test_metadata_cross_validation_fails_closed[issueTracker]`; `test_installed_wheel_metadata_fails_closed[Project-URL]` |
| `DV-07` | Apache-2.0 license | `verify_metadata` requires aligned pyproject, CFF, CodeMeta, JSON-LD, README, and `LICENSE` declarations; `verify_installed_package` checks wheel license metadata. | `test_metadata_cross_validation_fails_closed[license]`; `test_installed_wheel_metadata_fails_closed[License]` |
| `DV-08` | Keywords | `verify_metadata` compares pyproject, CFF, CodeMeta, and JSON-LD keyword sets; `verify_installed_package` checks wheel keywords. | `test_metadata_cross_validation_fails_closed[keywords]`; `test_installed_wheel_metadata_fails_closed[Keywords]` |
| `DV-09` | Python runtime and `Requires-Python` | `verify_metadata` compares pyproject, CodeMeta, and JSON-LD runtime declarations and the frozen `Requires-Python`; `verify_installed_package` checks wheel `Requires-Python`. | `test_metadata_cross_validation_fails_closed[runtimePlatform]`; `test_package_metadata_source_fields_fail_closed[requires-python]`; `test_installed_wheel_metadata_fails_closed[Requires-Python]` |
| `DV-10` | Package classifiers and development status | `verify_metadata` requires the frozen classifier set and matching CodeMeta pre-alpha status; `verify_installed_package` checks wheel classifiers. | `test_package_metadata_source_fields_fail_closed[classifier]`; `test_installed_wheel_metadata_fails_closed[Classifier]` |
| `DV-11` | Internal Markdown links | `verify_links` recursively scans root Markdown, `CONTRIBUTING.md`, all `docs/**`, and `llms.txt`, rejecting missing or escaping targets. | `test_recursive_link_check_fails_closed[broken-link]` |
| `DV-12` | Heading fragment anchors | `verify_links` derives GitHub-style heading anchors, including duplicate-heading suffixes, and rejects missing fragments. | `test_recursive_link_check_fails_closed[broken-anchor]` |
| `DV-13` | Duplicate canonical links | `verify_deferred_site_boundary` counts canonical elements in every checked-in HTML file and rejects duplicates. | `test_duplicate_canonical_links_fail_closed` |
| `DV-14` | Any live canonical link before an approved docs origin | `verify_deferred_site_boundary` rejects even a single live canonical element. | `test_live_site_metadata_fails_closed[single-canonical]` |
| `DV-15` | Open Graph or Twitter metadata before an approved docs origin | `verify_deferred_site_boundary` rejects live `og:*` and `twitter:*` metadata. | `test_live_site_metadata_fails_closed[open-graph]`; `test_live_site_metadata_fails_closed[twitter]` |
| `DV-16` | `sitemap.xml` or `robots.txt` before an approved docs origin | `verify_deferred_site_boundary` rejects either file at repository root or under `docs/`. | `test_live_site_metadata_fails_closed[sitemap]`; `test_live_site_metadata_fails_closed[robots]` |
| `DV-17` | Published JSON-LD before an approved docs origin | `verify_metadata` requires the unresolved URL token in the template; `verify_deferred_site_boundary` rejects a published `software-source-code.jsonld`. | `test_live_site_metadata_fails_closed[published-jsonld]` |

`test_discoverability_verification_matrix_is_complete` requires all IDs above,
so removing a row is itself a test failure. The executable verifier remains
authoritative; this matrix makes its review coverage explicit.
