// Stand-in for the real MobiVisor console component.
// Exists so a merge request can touch a path the doc map classifies as
// `ai-drafted` (area: enrollment-ios) and the gate has something to hit.

export function EnrollmentWizard() {
  const steps = ['Select platform', 'Configure ABM token', 'Assign policy'];
  return steps;
}
