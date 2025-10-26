"""
New index to ensure reasonable timehop performance.
"""

from yoyo import step

__depends__ = {'20250131_01_nFypG-some-new-indexes-for-performance'}

steps = [
    step("create index sharedfile_created_at_idx on sharedfile (created_at)")
]
