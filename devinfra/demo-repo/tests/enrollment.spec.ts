// Stand-in for the E2E suite.
// Doc-map area: ci-and-tests, class no-doc-impact. Most merges in a real
// repository look like this one, which is why the tier-1 path filter is the
// part of the gate that pays for itself (foundation doc §6.3).

export const spec = {
  name: 'enrollment wizard completes',
  steps: ['open wizard', 'upload token', 'assign policy'],
};
