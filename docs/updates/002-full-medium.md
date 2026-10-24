# 002 Keep the full FMA medium set

Date: 2026-09-25

Overrides: Task 2 rule "Keep at most 12000 rows", and the ~10-12k subset described in the plan.

Use every track in `fma_medium`. Do not cap the manifest. Rows with an empty title are still dropped. `fma_metadata.zip` is downloaded with the audio because track titles live there, not in the mp3 zip.

JDK 17 is required for Spark 3.5. The machine had Java 26 only, which fails at `Subject.getSubject`. Install Homebrew `openjdk@17` and point `JAVA_HOME` at it when running Spark jobs.
