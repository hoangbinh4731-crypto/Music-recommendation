import sys
import time

from pyspark.ml.feature import BucketedRandomProjectionLSH
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

from musicrec.config import (
    LSH_BUCKET_LENGTH,
    LSH_DISTANCE_THRESHOLD,
    LSH_NUM_HASH_TABLES,
    PROCESSED_DIR,
    TOP_N,
    VECTOR_DIM,
)
from musicrec.neighbors import fill_short_lists, top_n_from_pairs


def neighbor_frame(features):
    model = BucketedRandomProjectionLSH(
        inputCol="features",
        outputCol="hashes",
        bucketLength=LSH_BUCKET_LENGTH,
        numHashTables=LSH_NUM_HASH_TABLES,
    ).fit(features)
    pairs = model.approxSimilarityJoin(
        features, features, LSH_DISTANCE_THRESHOLD, distCol="distance"
    )
    flat = pairs.select(
        F.col("datasetA.track_id").alias("track_id"),
        F.col("datasetB.track_id").alias("neighbor_id"),
        F.col("distance"),
    ).filter(F.col("track_id") != F.col("neighbor_id")).dropDuplicates(["track_id", "neighbor_id"])

    # Chọn top-N ngay trong Spark để không kéo toàn bộ cặp về driver
    w = Window.partitionBy("track_id").orderBy("distance", "neighbor_id")
    limited = flat.withColumn("rk", F.row_number().over(w)).filter(F.col("rk") <= TOP_N).drop("rk")

    grouped = top_n_from_pairs(limited.toPandas(), TOP_N)
    vectors = features.select("track_id", "vector").toPandas()
    lsh_counts = grouped["neighbor_ids"].map(len)
    short = int((lsh_counts < 5).sum()) + (len(vectors) - len(grouped))
    result = fill_short_lists(grouped, vectors, TOP_N, min_count=5)
    return result, short


def main():
    master = sys.argv[1] if len(sys.argv) > 1 else "local[*]"
    t0 = time.perf_counter()
    spark = SparkSession.builder.master(master).appName("neighbors").getOrCreate()
    features = spark.read.parquet(str(PROCESSED_DIR / "features.parquet"))

    dim = len(features.select("vector").first()["vector"])
    assert dim == VECTOR_DIM, f"features.parquet có {dim} chiều, config.VECTOR_DIM={VECTOR_DIM}"

    result, short = neighbor_frame(features)
    out = PROCESSED_DIR / "neighbors.parquet"
    result.to_parquet(out, index=False)

    counts = result["neighbor_ids"].map(len)
    elapsed = time.perf_counter() - t0
    print(f"tracks={len(result)} min_neighbors={int(counts.min()) if len(counts) else 0}")
    print(f"fallback_tracks={short} ({short / max(len(result), 1):.1%}) "
          f"master={master} dim={dim} elapsed_s={elapsed:.1f}")
    spark.stop()


if __name__ == "__main__":
    main()
