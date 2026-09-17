# License Decision

MIT was selected by the project owner and its standard text is now in [LICENSE](LICENSE). This license decision does not grant permission to publish; repository creation and public release still require separate approval.

## MIT

Advantages:

- short and widely recognized;
- minimal adoption friction for a small instructions-and-tools project;
- compatible with many downstream open-source and commercial uses.

Tradeoff:

- no explicit patent grant beyond what may be implied by applicable law.

## Apache License 2.0

Advantages:

- explicit patent license and patent-termination language;
- clearer notice and contribution treatment for a growing adapter ecosystem.

Tradeoffs:

- longer text and more notice obligations;
- may be more process than this dependency-free candidate currently needs.

## Decision rationale

MIT fits the current small policy Skill and dependency-free helper implementation with minimal adoption friction. Apache-2.0 remains a future reconsideration point if substantial adapter code or patent-sensitive corporate contributions enter the repository. Review all third-party attributions independently; this repository does not copy optional-backend code, so their licenses do not determine this project's license.
