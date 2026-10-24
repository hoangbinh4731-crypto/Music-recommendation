# 001 Vector length is 36

Date: 2026-09-25

Overrides: Global Constraints `VECTOR_DIM = 35`, and the Task 1 import check that asserts 35.

The feature list in that same section is MFCC mean (20), chroma mean (12), tempo, spectral centroid, RMS energy, and zero-crossing rate. That is 36 values. `config.VECTOR_DIM` is 36. The old figure was a miscount.
