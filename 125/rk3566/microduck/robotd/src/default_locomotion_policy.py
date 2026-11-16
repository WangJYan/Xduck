"""Rider Mini requires a trained Walk/Stand model and matching API-v2 policy.py.

The original Xduck consumer encodes fifteen joints with fourteen motor targets. Reusing it
with Rider Mini's twelve motors would produce incorrect targets, so an upload must
include a model-specific consumer until a Rider Mini default has been validated.
"""


class Policy:
    def describe(self):
        raise RuntimeError(
            "Rider Mini Walk/Stand requires an uploaded policy.py matched to the model; "
            "the Xduck 14-motor-target default is incompatible"
        )
