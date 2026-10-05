# Router sealed project

No project is sealed in this revision. A labeled export is not in the repository.

`scripts/router/seal.py` overwrites this file when an export is present. The written file has the project id hash, the export hash, the artifact hash, the item count, the count of each label, and the sha256 of each sealed item. It does not include document text, filenames, or the project name.

Selection rule: `largest_then_lowest_project_sha256` (the largest project; ties break to the lowest project-id hash). That rule is data in `configs/router/dataset.json`. The project name is not in product code.

The dry run does not write train or held-out pairs, and it does not write them before this seal exists.
