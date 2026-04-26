"""Mock data for the medication reconciliation service.

Stands in for the external systems the service integrates with — the
client's FHIR API, the DrugBank-style drug interaction service, and the
allergy CSV exported nightly from a separate system. The adapter layer
in ``app/adapters/`` is the only consumer of this package; ``app/services/``
must never import from ``mocks/`` directly.
"""
