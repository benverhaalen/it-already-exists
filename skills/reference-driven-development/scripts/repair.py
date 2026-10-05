"""Reviewed external repair input. This validates bindings, not semantic independence."""
import re

import comparison
import workflow


def prepare(report, review, guidance, artifact):
    if report.get('status') not in ('failed', 'not_tested'):
        raise ValueError('repair requires failed or unresolved external evidence')
    for key in ('contract_sha256', 'candidate_artifact'):
        if not isinstance(report.get(key), str) or not re.fullmatch(r'[0-9a-f]{64}', report[key]):
            raise ValueError('repair report needs contract and actual artifact bindings')
    feedback = comparison.repair_export(report, review)
    if not feedback['counterexamples'] and not feedback['unresolved']:
        raise ValueError('repair has no external counterexamples or unresolved properties')
    if not isinstance(guidance, dict) or set(guidance) != {'scope', 'behaviors', 'review'}:
        raise ValueError('repair guidance needs scoped behavioral review')
    # Reuse the actual behavioral-export checks; metadata stays broker-side.
    workflow.review_export(dict(scope=guidance['scope'], goal='Repair external discrepancies',
        audience='The original intended audience',
        journey=dict(entry='Retain the reviewed entry', default='Retain the default',
                     action='Repair the reviewed discrepancy', outcome='Re-evaluate externally',
                     reset='Retain the reset behavior'), behaviors=guidance['behaviors'],
        unknowns=[], acceptance=['Keep the external contract fixed'], review=guidance['review']))
    return dict(artifact=artifact, feedback=feedback, guidance=guidance, report=report)
