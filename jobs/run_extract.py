import shutil
import time

import pandas as pd
from pyspark.ml.feature import StandardScaler
from pyspark.ml.functions import array_to_vector, vector_to_array
from pyspark.sql import SparkSession
from pyspark.sql.types import ArrayType, DoubleType, LongType, StructField, StructType

from musicrec.config import PROCESSED_DIR

RAW_SCHEMA = StructType(
    [
        StructField("track_id", LongType(), False),
        StructField("raw", ArrayType(DoubleType()), True),
    ]
)

def extract_batches(iterator):
    from musicrec.features import extract_track, raw_vector

    for frame in iterator:
        rows = []
        for rec in frame.itertuples(index=False):
            try:
                vec = raw_vector(extract_track(rec.audio_path))
            except Exception as exc:
                print(f"extract failed track_id={rec.track_id} err={exc!r}", flush=True)
                vec = None
            rows.append({"track_id": int(rec.track_id), "raw": vec})
            if len(rows) % 200 == 0:
                print(f"extracted_in_batch={len(rows)}", flush=True)
        print(f"extracted_batch={len(rows)}", flush=True)
        yield pd.DataFrame(rows)


def main():
    from musicrec.features import feature_names

    t0 = time.perf_counter()
    spark = SparkSession.builder.master("local[*]").appName("extract").getOrCreate()
    parallelism = spark.sparkContext.defaultParallelism
    tracks = spark.read.parquet(str(PROCESSED_DIR / "tracks.parquet")).repartition(parallelism)
    input_count = tracks.count()
    print(f"partitions={parallelism} input_rows={input_count}", flush=True)

    extracted = (
        tracks.select("track_id", "audio_path")
        .mapInPandas(extract_batches, RAW_SCHEMA)
        .persist()
    )
    print(f"extracted_rows={extracted.count()}", flush=True)
    t_extract = time.perf_counter() - t0

    bad_rows = extracted.filter(extracted.raw.isNull()).select("track_id").toPandas()
    good = extracted.filter(extracted.raw.isNotNull())
    output_count = good.count()
    good.write.mode("overwrite").parquet(str(PROCESSED_DIR / "features_raw.parquet"))

    if len(bad_rows):
        bad_path = PROCESSED_DIR / "bad_tracks.csv"
        tagged = bad_rows.assign(reason="unreadable")
        if bad_path.exists():
            tagged = pd.concat([pd.read_csv(bad_path), tagged], ignore_index=True)
        tagged.to_csv(bad_path, index=False)

    with_vectors = good.withColumn("raw_features", array_to_vector("raw"))
    scaler = StandardScaler(
        inputCol="raw_features", outputCol="features", withMean=True, withStd=True
    )
    model = scaler.fit(with_vectors)
    scaled = model.transform(with_vectors)
    scaled = scaled.withColumn("vector", vector_to_array("features"))

    dim = len(scaled.select("vector").first()["vector"])
    assert dim == len(feature_names()), f"dim={dim}, expected {len(feature_names())}"

    scaled.write.mode("overwrite").parquet(str(PROCESSED_DIR / "features.parquet"))
    scaler_path = PROCESSED_DIR / "scaler"
    if scaler_path.exists():
        shutil.rmtree(scaler_path)
    model.save(str(scaler_path))

    total = time.perf_counter() - t0
    print(f"input_rows={input_count} output_rows={output_count} null_drops={len(bad_rows)}")
    print(
        f"dim={dim} extract_s={t_extract:.1f} total_s={total:.1f} "
        f"s_per_track={t_extract / max(input_count, 1):.2f} cores={parallelism}"
    )
    spark.stop()


if __name__ == "__main__":
    main()
