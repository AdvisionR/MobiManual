// Stand-in for the real MobiVisor console component.
// Exists so a merge request can touch a path the doc map classifies as
// `ai-drafted` (area: enrollment-ios) and the gate has something to hit.
//
// The manual page this renders is docs/pages/enrollment/ios-abm.md — in the
// same repository, which is the point of the monorepo layout: the code change
// and the documentation change can land in one merge request.

export function EnrollmentWizard() {
  const steps = ['Select platform', 'Configure ABM token', 'Assign policy'];
  return steps;
}
