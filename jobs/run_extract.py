import shutil
from pathlib import Path

import pandas as pd
from pyspark.ml.feature import StandardScaler
from pyspark.ml.linalg import Vectors, VectorUDT
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, DoubleType, LongType, StructField, StructType

from musicrec.config import PROCESSED_DIR
from musicrec.features import raw_vector

RAW_SCHEMA = StructType(
    [
        StructField("track_id", LongType(), False),
        StructField("mfcc", ArrayType(DoubleType()), True),
        StructField("chroma", ArrayType(DoubleType()), True),
        StructField("tempo", DoubleType(), True),
        StructField("spectral_centroid", DoubleType(), True),
        StructField("energy", DoubleType(), True),
        StructField("zcr", DoubleType(), True),
    ]
)


def extract_batches(iterator):
    from musicrec.features import extract_track

    for frame in iterator:
        rows = []
        for rec in frame.itertuples(index=False):
            try:
                feat = extract_track(rec.audio_path)
            except Exception:
                print(f"extract failed track_id={rec.track_id}")
                feat = {
                    "mfcc": None,
                    "chroma": None,
                    "tempo": None,
                    "spectral_centroid": None,
                    "energy": None,
                    "zcr": None,
                }
            feat["track_id"] = int(rec.track_id)
            rows.append(feat)
            if len(rows) % 200 == 0:
                print(f"extracted_in_batch={len(rows)}", flush=True)
        print(f"extracted_batch={len(rows)}", flush=True)
        yield pd.DataFrame(rows)


def attach_raw_features(frame):
    def to_raw(mfcc, chroma, tempo, centroid, energy, zcr):
        if mfcc is None:
            return None
        return Vectors.dense(
            raw_vector(
                {
                    "mfcc": mfcc,
                    "chroma": chroma,
                    "tempo": tempo,
                    "spectral_centroid": centroid,
                    "energy": energy,
                    "zcr": zcr,
                }
            )
        )

    convert = udf(to_raw, VectorUDT())
    return frame.withColumn(
        "raw_features",
        convert("mfcc", "chroma", "tempo", "spectral_centroid", "energy", "zcr"),
    )


def assemble_and_scale(spark, raw_df):
    del spark
    scaler = StandardScaler(
        inputCol="raw_features",
        outputCol="features",
        withMean=True,
        withStd=True,
    )
    model = scaler.fit(raw_df)
    return model.transform(raw_df), model


def main():
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
    bad = extracted.filter(extracted.mfcc.isNull()).select("track_id")
    bad_rows = bad.toPandas()
    good = extracted.filter(extracted.mfcc.isNotNull())
    output_count = good.count()
    raw_path = PROCESSED_DIR / "features_raw.parquet"
    good.write.mode("overwrite").parquet(str(raw_path))
    if len(bad_rows):
        bad_path = PROCESSED_DIR / "bad_tracks.csv"
        tagged = bad_rows.assign(reason="unreadable")
        if bad_path.exists():
            tagged = pd.concat([pd.read_csv(bad_path), tagged], ignore_index=True)
        tagged.to_csv(bad_path, index=False)
    with_vectors = attach_raw_features(good)
    scaled, model = assemble_and_scale(spark, with_vectors)
    to_list = udf(lambda vector: None if vector is None else vector.toArray().tolist(), ArrayType(DoubleType()))
    scaled = scaled.withColumn("vector", to_list("features"))
    scaled.write.mode("overwrite").parquet(str(PROCESSED_DIR / "features.parquet"))
    scaler_path = PROCESSED_DIR / "scaler"
    if scaler_path.exists():
        shutil.rmtree(scaler_path)
    model.save(str(scaler_path))
    print(f"input_rows={input_count} output_rows={output_count} null_drops={len(bad_rows)}")
    spark.stop()


if __name__ == "__main__":
    main()
