from pyspark.ml.feature import BucketedRandomProjectionLSH
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from musicrec.config import LSH_BUCKET_LENGTH, LSH_DISTANCE_THRESHOLD, LSH_NUM_HASH_TABLES, PROCESSED_DIR, TOP_N
from musicrec.neighbors import fill_short_lists, top_n_from_pairs


def neighbor_frame(features):
    model = BucketedRandomProjectionLSH(
        inputCol="features",
        outputCol="hashes",
        bucketLength=LSH_BUCKET_LENGTH,
        numHashTables=LSH_NUM_HASH_TABLES,
    ).fit(features)
    pairs = model.approxSimilarityJoin(features, features, LSH_DISTANCE_THRESHOLD, distCol="distance")
    flat = pairs.select(
        F.col("datasetA.track_id").alias("track_id"),
        F.col("datasetB.track_id").alias("neighbor_id"),
        F.col("distance"),
    )
    grouped = top_n_from_pairs(flat.toPandas(), TOP_N)
    vectors = features.select("track_id", "vector").toPandas()
    return fill_short_lists(grouped, vectors, TOP_N, min_count=5)


def main():
    spark = SparkSession.builder.master("local[*]").appName("neighbors").getOrCreate()
    features = spark.read.parquet(str(PROCESSED_DIR / "features.parquet"))
    result = neighbor_frame(features)
    out = PROCESSED_DIR / "neighbors.parquet"
    result.to_parquet(out, index=False)
    counts = result["neighbor_ids"].map(len)
    print(f"tracks={len(result)} min_neighbors={int(counts.min()) if len(counts) else 0}")
    spark.stop()


if __name__ == "__main__":
    main()
